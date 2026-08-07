from __future__ import annotations

import json
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from support import (
    authority,
    compiled_specification,
    digest_text,
    load_contract,
    treatment,
    workflow,
)


class LoopstrapConformanceAcceptance(unittest.TestCase):
    def test_real_cell_path_custodies_charges_and_accepts(self) -> None:
        from loopstrap_core.atomic import canonical_json
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.authority import Authorization
        from loopstrap_core.certification import ConformanceEvaluator
        from loopstrap_core.errors import CertificationError
        from loopstrap_core.evidence import AcceptanceObligation, EvidenceRecord
        from loopstrap_core.system import LoopstrapSystem

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source"
            source.mkdir()
            (source / "base.txt").write_text("base\n", encoding="utf-8")
            harness = base / "conformance_harness.py"
            harness.write_text(
                "import hashlib,json,sys\n"
                "from pathlib import Path\n"
                "request=json.loads(sys.stdin.read())\n"
                "requested=request['requested_role_treatment']\n"
                "canon=lambda value:json.dumps(value,sort_keys=True,separators=(',',':')).encode()\n"
                "config_digest='sha256:'+hashlib.sha256(canon(requested['configuration'])).hexdigest()\n"
                "identity={**requested,'command':request['role_treatment_command']}\n"
                "attestation={'schema_version':1,'issuer':'loopstrap-harness-wrapper-v1',"
                "'invocation_id':request['invocation_id'],'role_treatment_id':requested['id'],"
                "'role':requested['role'],'harness':requested['harness'],"
                "'requested_identity_digest':'sha256:'+hashlib.sha256(canon(identity)).hexdigest(),"
                "'sent':{'model_selector':requested['model_route']['selector'],"
                "'model_provider':requested['model_route']['provider'],"
                "'reasoning_control':requested['reasoning']['control'],"
                "'reasoning_value':requested['reasoning']['requested'],"
                "'expected_wire_reasoning':requested['reasoning']['expected_wire'],"
                "'orchestration':requested['reasoning']['orchestration'],"
                "'configuration_digest':config_digest},"
                "'observed':{'models':[requested['model_route']['allowed_resolved_models'][0]],"
                "'reasoning':requested['reasoning']['expected_wire'],"
                "'orchestration':requested['reasoning']['orchestration'],"
                "'fallback_detected':False,'hidden_config_detected':False},"
                "'proof':{'model':'runtime_event','reasoning':'runtime_event',"
                "'configuration':'sanitized_argv_and_digests','mapping_evidence_ref':None},"
                "'sanitized_argv':['conformance-mock'],'configuration_digest':config_digest,"
                "'environment_names':[]}\n"
                "Path('agent-output.txt').write_text('certified mutation\\n')\n"
                "response={'invocation_id':request['invocation_id'],"
                "'cell_revision':request['cell_revision'],'status':'completed',"
                "'launch_attestation':attestation,"
                "'artifacts':[],'claims':[],"
                "'usage':{'input_tokens':10,'output_tokens':5,'cost':0.25},"
                "'cache_lineage':request.get('cache_lineage')}\n"
                "print(json.dumps(response,sort_keys=True,separators=(',',':')))\n",
                encoding="utf-8",
            )
            row = treatment(behavior="write")
            row["command"] = [sys.executable, str(harness)]
            row["wrapper"]["id"] = sys.executable
            certs = authority(
                row,
                ArtifactStore(base / "certification-artifacts"),
            )
            specification = compiled_specification()
            system = LoopstrapSystem.create(
                root_dir=base / "run",
                workflow=workflow(),
                role_treatments={
                    "version": 1,
                    "role_treatments": [row],
                },
                role_policy={
                    "version": 1,
                    "roles": {
                        "implementer": {
                            "role_treatment": row["id"],
                            "requires": [],
                        }
                    },
                },
                source_dir=source,
                specification=specification,
                certification_authority=certs,
            )
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1"],
            )
            system.accept_contract("root")
            system.freeze_tests(
                "root",
                visible_digest=digest_text("visible"),
                holdout_digest=digest_text("holdout"),
                obligation_map={"G1": ["test::root::G1"]},
                executable=True,
            )
            system.record_plan(
                "root",
                plan_digest=digest_text("plan"),
                responsibilities={"G1": "implementation"},
            )
            system.record_pre_review(
                "root",
                accepted=True,
                leaf=True,
                unresolved_seams=[],
            )
            view = system.control_view("root")
            authorization = Authorization.from_dict(
                {
                    "authorization_id": "auth-conformance",
                    "run_id": system.run_id,
                    "cell_id": "root",
                    "revision": view.revision,
                    "role": "implementer",
                    "role_treatment_id": row["id"],
                    "act": "dispatch",
                }
            )
            bindings = {
                "prompt_ref": digest_text("prompt"),
                "context_manifest_ref": digest_text("context"),
                "context_lineage": "fresh-conformance",
                "cache_lineage": None,
            }
            job = system.dispatch(authorization, **bindings)
            self.assertEqual(
                system.artifacts.get_bytes(job.response_ref),
                canonical_json(job.result.evidence()),
            )
            self.assertIsNotNone(job.result.execution_ref)
            self.assertTrue((job.workspace.path / "agent-output.txt").is_file())
            self.assertEqual(system.usage_ledger.totals().tokens, 15)
            self.assertEqual(system.usage_ledger.totals().money, 0.25)

            events = system.ledger.verify()
            completed_index = next(
                index
                for index, event in enumerate(events)
                if event["type"] == "harness.completed"
            )
            durable = events[completed_index - 1]
            self.assertEqual(durable["type"], "state.checkpoint")
            self.assertIn(job.job_id, durable["payload"]["jobs"])
            interrupted_root = base / "interrupted-run"
            shutil.copytree(base / "run", interrupted_root)
            lines = (interrupted_root / "events.jsonl").read_bytes().splitlines(
                keepends=True
            )
            (interrupted_root / "events.jsonl").write_bytes(
                b"".join(lines[:completed_index])
            )
            interrupted = LoopstrapSystem.open(
                root_dir=interrupted_root,
                workflow=workflow(),
                role_treatments={
                    "version": 1,
                    "role_treatments": [row],
                },
                role_policy={
                    "version": 1,
                    "roles": {
                        "implementer": {
                            "role_treatment": row["id"],
                            "requires": [],
                        }
                    },
                },
                specification=specification,
                certification_authority=certs,
            )
            interrupted_reuse = interrupted.dispatch(authorization, **bindings)
            self.assertEqual(interrupted_reuse.job_id, job.job_id)
            self.assertEqual(interrupted.usage_ledger.totals().tokens, 15)
            self.assertNotIn(
                "harness.completed",
                [event["type"] for event in interrupted.ledger.verify()],
            )

            cell = system.graph.cell("root")
            records = (
                EvidenceRecord.from_dict(
                    {
                        "id": "evidence.cell",
                        "specification_digest": specification.digest,
                        "cell_id": "root",
                        "cell_revision": cell.revision,
                        "scope_kind": "cell",
                        "scope_id": "root",
                        "role_treatment_id": row["id"],
                        "producer_id": "conformance-harness",
                        "producer_class": "test_harness",
                        "subject_producer_ids": ["implementer"],
                        "obligation_ids": ["accept.cell"],
                        "execution_ref": job.result.execution_ref,
                        "artifact_refs": [job.response_ref],
                        "observation": {"passed": True},
                        "finding_ids": [],
                    }
                ),
                EvidenceRecord.from_dict(
                    {
                        "id": "evidence.root",
                        "specification_digest": specification.digest,
                        "cell_id": "root",
                        "cell_revision": cell.revision,
                        "scope_kind": "root",
                        "scope_id": "root",
                        "role_treatment_id": row["id"],
                        "producer_id": "system-harness",
                        "producer_class": "system_harness",
                        "subject_producer_ids": ["implementer"],
                        "obligation_ids": ["accept.root"],
                        "execution_ref": job.result.execution_ref,
                        "artifact_refs": [job.response_ref],
                        "observation": {"passed": True},
                        "finding_ids": [],
                    }
                ),
            )
            for record in records:
                system.record_evidence(record)
            acceptance = system.evaluate_acceptance(
                acceptance_id="acceptance.conformance",
                obligations=[
                    AcceptanceObligation.from_dict(
                        {
                            "id": "accept.cell",
                            "scope_kind": "cell",
                            "scope_id": "root",
                            "eligible_producer_classes": ["test_harness"],
                            "minimum_evidence": 1,
                            "independent": True,
                        }
                    ),
                    AcceptanceObligation.from_dict(
                        {
                            "id": "accept.root",
                            "scope_kind": "root",
                            "scope_id": "root",
                            "eligible_producer_classes": ["system_harness"],
                            "minimum_evidence": 1,
                            "independent": True,
                        }
                    ),
                ],
            )

            completed_before = sum(
                event["type"] == "harness.completed"
                for event in system.ledger.verify()
            )
            recovered = LoopstrapSystem.open(
                root_dir=base / "run",
                workflow=workflow(),
                role_treatments={
                    "version": 1,
                    "role_treatments": [row],
                },
                role_policy={
                    "version": 1,
                    "roles": {
                        "implementer": {
                            "role_treatment": row["id"],
                            "requires": [],
                        }
                    },
                },
                specification=specification,
                certification_authority=certs,
            )
            reused = recovered.dispatch(authorization, **bindings)
            completed_after = sum(
                event["type"] == "harness.completed"
                for event in recovered.ledger.verify()
            )
            observation = {
                "dispatch_completed": True,
                "structured_response_valid": True,
                "workspace_mutated": (
                    job.workspace.path / "agent-output.txt"
                ).is_file(),
                "execution_ref": job.result.execution_ref,
                "usage_charged": (
                    recovered.usage_ledger.totals().tokens == 15
                    and recovered.usage_ledger.totals().money == 0.25
                ),
                "cell_accepted": (
                    acceptance.accepted
                    and "accept.cell" in acceptance.satisfied_obligation_ids
                ),
                "root_accepted": (
                    acceptance.accepted
                    and "accept.root" in acceptance.satisfied_obligation_ids
                ),
                "restart_reused": (
                    reused.job_id == job.job_id
                    and completed_before == completed_after == 1
                ),
            }
            self.assertEqual(
                ConformanceEvaluator(load_contract()).evaluate(observation),
                "PASS",
            )
            failed = dict(observation)
            failed["root_accepted"] = False
            self.assertEqual(
                ConformanceEvaluator(load_contract()).evaluate(failed),
                "FAIL",
            )
            incomplete = dict(observation)
            incomplete.pop("usage_charged")
            with self.assertRaises(CertificationError):
                ConformanceEvaluator(load_contract()).evaluate(incomplete)

    def test_partial_stream_failures_are_custodied_and_refused(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.evidence import RawExecutionCustodian
        from loopstrap_core.errors import (
            HarnessInterruptedError,
            HarnessOutputLimitError,
            HarnessProtocolError,
            HarnessTimeoutError,
        )
        from loopstrap_core.harness import (
            HarnessDispatcher,
            Invocation,
            RoleTreatment,
        )

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            script = root / "partial.py"
            script.write_text(
                "import sys,time\n"
                "mode=sys.argv[1]\n"
                "print('partial-token=secret', flush=True)\n"
                "if mode == 'interrupt': time.sleep(0.05)\n"
                "print('stderr-partial', file=sys.stderr, flush=True)\n"
                "if mode == 'overflow': print('x'*10000, flush=True)\n"
                "if mode == 'failure': raise SystemExit(7)\n"
                "time.sleep(5)\n",
                encoding="utf-8",
            )
            row = treatment(behavior="write")
            artifacts = ArtifactStore(root / "artifacts")
            dispatcher = HarnessDispatcher(
                execution_custodian=RawExecutionCustodian(artifacts)
            )

            def invocation(
                mode: str,
                *,
                timeout: float = 0.1,
                maximum: int = 4096,
            ) -> Invocation:
                return Invocation(
                    invocation_id=f"partial-{mode}",
                    run_id="run",
                    cell_id="root",
                    cell_revision=1,
                    role="implementer",
                    prompt_ref=digest_text(f"prompt-{mode}"),
                    context_manifest_ref=digest_text(f"context-{mode}"),
                    context_lineage=f"fresh-{mode}",
                    cache_lineage=None,
                    workspace=root,
                    timeout_seconds=timeout,
                    max_output_bytes=maximum,
                    environment={},
                )

            def retained(exception, *, expect_stderr: bool = True) -> dict:
                self.assertIsNotNone(exception.execution_ref)
                payload = json.loads(artifacts.get_bytes(exception.execution_ref))
                self.assertIn("partial-token=[REDACTED]", payload["stdout"])
                if expect_stderr:
                    self.assertIn("stderr-partial", payload["stderr"])
                return payload

            row["command"] = [sys.executable, str(script), "timeout"]
            row["wrapper"]["id"] = sys.executable
            with self.assertRaises(HarnessTimeoutError) as caught:
                dispatcher.dispatch(
                    RoleTreatment.from_dict(row),
                    invocation("timeout"),
                )
            retained(caught.exception, expect_stderr=False)

            row["command"] = [sys.executable, str(script), "overflow"]
            with self.assertRaises(HarnessOutputLimitError) as caught:
                dispatcher.dispatch(
                    RoleTreatment.from_dict(row),
                    invocation("overflow", maximum=64),
                )
            retained(caught.exception, expect_stderr=False)

            row["command"] = [sys.executable, str(script), "failure"]
            with self.assertRaises(HarnessProtocolError) as caught:
                dispatcher.dispatch(
                    RoleTreatment.from_dict(row),
                    invocation("failure", timeout=1),
                )
            retained(caught.exception, expect_stderr=False)

            row["command"] = [sys.executable, str(script), "interrupt"]
            original_select = selectors.DefaultSelector.select
            calls = 0

            def interrupt_after_first_read(selector, timeout=None):
                nonlocal calls
                calls += 1
                if calls > 1:
                    raise KeyboardInterrupt
                return original_select(selector, timeout)

            with mock.patch.object(
                selectors.DefaultSelector,
                "select",
                interrupt_after_first_read,
            ):
                with self.assertRaises(HarnessInterruptedError) as caught:
                    dispatcher.dispatch(
                        RoleTreatment.from_dict(row),
                        invocation("interrupt", timeout=1),
                    )
            retained(caught.exception, expect_stderr=False)

    def test_restart_reuses_completion_without_double_charge(self) -> None:
        from loopstrap_core.certification import UsageChargeLedger
        from loopstrap_core.errors import IdempotencyError

        ledger = UsageChargeLedger()
        first = ledger.charge(
            dispatch_id="job-1",
            usage={"input_tokens": 10, "output_tokens": 5, "cost": 0.25},
            latency_ms=100,
        )
        second = ledger.charge(
            dispatch_id="job-1",
            usage={"input_tokens": 10, "output_tokens": 5, "cost": 0.25},
            latency_ms=100,
        )
        self.assertEqual(first, second)
        self.assertEqual(ledger.totals().tokens, 15)
        self.assertEqual(ledger.totals().money, 0.25)
        with self.assertRaises(IdempotencyError):
            ledger.charge(
                dispatch_id="job-1",
                usage={"input_tokens": 10, "output_tokens": 6, "cost": 0.25},
                latency_ms=100,
            )

    def test_receipt_requires_all_three_layers(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.harness import RoleTreatment

        with tempfile.TemporaryDirectory() as raw:
            artifacts = ArtifactStore(Path(raw) / "artifacts")
            row = treatment()
            for missing in load_contract().required_layers:
                statuses = {
                    layer: "PASS"
                    for layer in load_contract().required_layers
                    if layer != missing
                }
                certs = authority(row, artifacts, statuses=statuses)
                self.assertFalse(
                    certs.is_certified(RoleTreatment.from_dict(row))
                )

    def test_mock_certification_does_not_arm_live_configuration(self) -> None:
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "loopstrap_core.cli",
                "validate",
                "--workflow",
                str(root / "config" / "workflow.v1.json"),
                "--role-treatments",
                str(root / "config" / "role-treatments.v1.json"),
                "--roles",
                str(root / "config" / "roles.v1.json"),
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["armed"])
        self.assertEqual(payload["assigned_roles"], 6)
