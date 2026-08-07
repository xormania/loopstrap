from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from support import certification_authority, digest, treatment, workflow_definition


HERE = Path(__file__).resolve().parent
MOCK = HERE / "mock_harness.py"


class InnerLoopAcceptance(unittest.TestCase):
    def test_real_mock_harness_leaf_path_is_tests_first_reviewed_and_promoted(self) -> None:
        from loopstrap_core.authority import Authorization
        from loopstrap_core.system import LoopstrapSystem

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            (source / "existing.txt").write_text("base\n", encoding="utf-8")
            rows = [
                treatment(
                    "mock-writer",
                    harness="mock",
                    model="deterministic",
                    reasoning="fixed",
                    command=[sys.executable, str(MOCK), "--behavior", "write"],
                    capabilities=("json", "workspace_write"),
                )
            ]
            system = LoopstrapSystem.create(
                root_dir=root / "run",
                workflow=workflow_definition(),
                role_treatments={
                    "version": 1,
                    "role_treatments": rows,
                },
                role_policy={
                    "version": 1,
                    "roles": {
                        "implementer": {
                            "role_treatment": "mock-writer"
                        }
                    },
                },
                source_dir=source,
                certification_authority=certification_authority(rows, root),
            )
            system.create_root(
                "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
            )
            system.accept_contract("root")
            system.freeze_tests(
                "root",
                visible_digest=digest("visible-tests"),
                holdout_digest=digest("holdout-tests"),
                obligation_map={"O1": ["test-o1"]},
                executable=True,
            )
            system.record_plan(
                "root",
                plan_digest=digest("plan"),
                responsibilities={"O1": "implementation"},
            )
            system.record_pre_review("root", accepted=True, leaf=True, unresolved_seams=[])
            view = system.control_view("root")
            auth = Authorization.from_dict(
                {
                    "authorization_id": "auth-implement",
                    "run_id": system.run_id,
                    "cell_id": "root",
                    "revision": view.revision,
                    "role": "implementer",
                    "role_treatment_id": "mock-writer",
                    "act": "dispatch",
                }
            )
            job = system.dispatch(
                auth,
                prompt_ref="sha256:" + digest("implement-prompt"),
                context_manifest_ref="sha256:" + digest("implementation-context"),
                context_lineage="implementation-lineage",
                cache_lineage=None,
            )
            self.assertEqual((source / "existing.txt").read_text(encoding="utf-8"), "base\n")
            self.assertFalse((source / "agent-output.txt").exists())
            system.verify_job(
                job.job_id,
                passed=True,
                evidence_refs=["sha256:" + digest("judges-green")],
            )
            system.record_post_review(
                "root",
                accepted=True,
                evidence_refs=["sha256:" + digest("adversarial-review-green")],
            )
            system.promote_job(job.job_id)
            system.close("root")
            materialized = root / "result"
            system.materialize_current(materialized)
            self.assertEqual(
                (materialized / "agent-output.txt").read_text(encoding="utf-8"),
                "written only in workspace\n",
            )
            self.assertEqual(system.status()["cells"]["root"]["phase_kind"], "closed")
            event_types = [event["type"] for event in system.ledger.verify()]
            for required in (
                "tests.frozen",
                "plan.recorded",
                "pre_review.recorded",
                "job.reserved",
                "harness.completed",
                "verification.recorded",
                "post_review.recorded",
                "candidate.promoted",
                "cell.closed",
            ):
                self.assertIn(required, event_types)

    def test_malformed_harness_result_never_changes_candidate_pointer(self) -> None:
        from loopstrap_core.authority import Authorization
        from loopstrap_core.errors import HarnessProtocolError
        from loopstrap_core.system import LoopstrapSystem

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            (source / "base.txt").write_text("base\n", encoding="utf-8")
            rows = [
                treatment(
                    "broken",
                    harness="mock",
                    model="broken",
                    reasoning="fixed",
                    command=[sys.executable, str(MOCK), "--behavior", "malformed"],
                    capabilities=("json", "workspace_write"),
                )
            ]
            system = LoopstrapSystem.create(
                root_dir=root / "run",
                workflow=workflow_definition(),
                role_treatments={
                    "version": 1,
                    "role_treatments": rows,
                },
                role_policy={
                    "version": 1,
                    "roles": {
                        "implementer": {
                            "role_treatment": "broken"
                        }
                    },
                },
                source_dir=source,
                certification_authority=certification_authority(rows, root),
            )
            system.create_root(
                "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
            )
            system.accept_contract("root")
            system.freeze_tests(
                "root",
                visible_digest=digest("visible"),
                holdout_digest=digest("holdout"),
                obligation_map={"O1": ["test"]},
                executable=True,
            )
            system.record_plan(
                "root", plan_digest=digest("plan"), responsibilities={"O1": "implementation"}
            )
            system.record_pre_review("root", accepted=True, leaf=True, unresolved_seams=[])
            before = system.current_snapshot()
            view = system.control_view("root")
            auth = Authorization.from_dict(
                {
                    "authorization_id": "auth-broken",
                    "run_id": system.run_id,
                    "cell_id": "root",
                    "revision": view.revision,
                    "role": "implementer",
                    "role_treatment_id": "broken",
                    "act": "dispatch",
                }
            )
            with self.assertRaises(HarnessProtocolError):
                system.dispatch(
                    auth,
                    prompt_ref="sha256:" + digest("prompt"),
                    context_manifest_ref="sha256:" + digest("context"),
                    context_lineage="lineage",
                    cache_lineage=None,
                )
            self.assertEqual(system.current_snapshot(), before)
            self.assertIn(
                "harness.failed",
                [event["type"] for event in system.ledger.verify()],
            )
