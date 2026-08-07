from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MOCK = ROOT / "tests" / "acceptance" / "mock_harness.py"
RICH_MOCK = ROOT / "tests" / "integration" / "rich_mock_harness.py"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def treatment(
    role_treatment_id: str,
    *,
    behavior: str,
    role: str | None = None,
    capabilities: tuple[str, ...] = ("json", "workspace_write"),
) -> dict[str, object]:
    return {
        "id": role_treatment_id,
        "role": role or role_treatment_id,
        "harness": "mock",
        "model_route": {
            "provider": "mock",
            "selector": f"deterministic-{role_treatment_id}",
            "allowed_resolved_models": [f"deterministic-{role_treatment_id}"],
            "fallback_policy": "deny",
        },
        "reasoning": {
            "control": "fixed",
            "requested": "fixed",
            "expected_wire": "fixed",
            "orchestration": "single-agent",
            "proof_sources": ["runtime_event"],
        },
        "wrapper": {
            "id": sys.executable,
            "version": "1",
            "vendor_executable": "mock",
        },
        "configuration": {"behavior": behavior},
        "capabilities": list(capabilities),
        "enabled": True,
        "command": [sys.executable, str(MOCK), "--behavior", behavior],
    }


def make_system(
    raw: str,
    *,
    roles: dict[str, dict[str, object]],
    treatments: list[dict[str, object]] | None = None,
):
    from loopstrap_core.system import LoopstrapSystem

    base = Path(raw)
    source = base / "source"
    source.mkdir()
    (source / "base.txt").write_text("base\n", encoding="utf-8")
    rows = treatments or [treatment("implementer", behavior="write")]
    from loopstrap_core.artifacts import ArtifactStore
    from loopstrap_core.certification import (
        CertificationAuthority,
        CertificationContract,
        CertificationReceipt,
        ExecutableIdentity,
    )
    from loopstrap_core.harness import RoleTreatment

    contract = CertificationContract.from_dict(
        json.loads(
            (ROOT / "config" / "harness-certification.v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    cert_artifacts = ArtifactStore(base / "certification-artifacts")
    receipts = []
    for row in rows:
        parsed = RoleTreatment.from_dict(row)
        refs = tuple(
            cert_artifacts.put_bytes(
                f"{parsed.id}:{layer}".encode("utf-8"), media_type="text/plain"
            )
            for layer in contract.required_layers
        )
        receipts.append(
            CertificationReceipt.issue(
                role_treatment=parsed,
                executables=(
                    ExecutableIdentity.observe(
                        Path(parsed.command[0]), version="deterministic-test"
                    ),
                ),
                contract_digest=contract.digest,
                run_id="integration-certification",
                layer_results={layer: "PASS" for layer in contract.required_layers},
                evidence_refs=refs,
                report_ref=None,
                issued_at="2026-07-23T00:00:00Z",
            )
        )
    certs = CertificationAuthority(
        contract_digest=contract.digest,
        artifacts=cert_artifacts,
        receipts=receipts,
    )
    return LoopstrapSystem.create(
        root_dir=base / "run",
        workflow=json.loads(
            (ROOT / "config" / "workflow.v1.json").read_text(encoding="utf-8")
        ),
        role_treatments={
            "version": 1,
            "role_treatments": rows,
        },
        role_policy={"version": 1, "roles": roles},
        source_dir=source,
        certification_authority=certs,
    )


def prepare_cell(system, cell_id: str, *, leaf: bool, test_digests=None) -> None:
    system.accept_contract(cell_id)
    visible, holdout = test_digests or (
        digest(f"{cell_id}-visible"),
        digest(f"{cell_id}-holdout"),
    )
    obligations = system.graph.cell(cell_id).obligations
    system.freeze_tests(
        cell_id,
        visible_digest=visible,
        holdout_digest=holdout,
        obligation_map={item: [f"test::{item}"] for item in obligations},
        executable=True,
    )
    system.record_plan(
        cell_id,
        plan_digest=digest(f"{cell_id}-plan"),
        responsibilities={item: "implementation" for item in obligations},
    )
    system.record_pre_review(
        cell_id, accepted=True, leaf=leaf, unresolved_seams=[]
    )


def authorization(system, cell_id: str, role: str, role_treatment_id: str, act: str = "dispatch"):
    from loopstrap_core.authority import Authorization

    view = system.control_view(cell_id)
    return Authorization.from_dict(
        {
            "authorization_id": f"auth-{cell_id}-{role}-{view.revision}",
            "run_id": system.run_id,
            "cell_id": cell_id,
            "revision": view.revision,
            "role": role,
            "role_treatment_id": role_treatment_id,
            "act": act,
        }
    )


def dispatch(system, cell_id: str, role: str, role_treatment_id: str, lineage: str, act: str = "dispatch"):
    return system.dispatch(
        authorization(system, cell_id, role, role_treatment_id, act),
        prompt_ref="sha256:" + digest(f"{cell_id}-{role}-prompt"),
        context_manifest_ref="sha256:" + digest(f"{cell_id}-{role}-context"),
        context_lineage=lineage,
        cache_lineage=None,
    )


class BudgetSafetyIntegration(unittest.TestCase):
    def test_invalid_resource_values_cannot_reduce_or_invert_budget_accounting(self) -> None:
        from loopstrap_core.budget import (
            BudgetLedger,
            HardLimits,
            MarginalValuePolicy,
            ResourceUsage,
        )
        from loopstrap_core.errors import SchemaError

        ledger = BudgetLedger(limits=HardLimits(money=10.0, tokens=100))
        for invalid in (
            ResourceUsage(money=-0.01),
            ResourceUsage(tokens=-1),
            ResourceUsage(money=math.nan),
            ResourceUsage(latency_seconds=math.inf),
        ):
            with self.assertRaises(SchemaError):
                ledger.charge(invalid)
        with self.assertRaises(SchemaError):
            BudgetLedger(limits=HardLimits(tokens=-1))
        for prices in ({"money": -1.0}, {"money": math.nan}, {"typo": 1.0}):
            with self.assertRaises(SchemaError):
                ledger.authorize(
                    MarginalValuePolicy(version=1, shadow_prices=prices),
                    expected_loss_before=10.0,
                    expected_loss_after=5.0,
                    usage=ResourceUsage(money=1.0),
                )
        with self.assertRaises(SchemaError):
            ledger.authorize(
                MarginalValuePolicy(version=1, shadow_prices={"money": 1.0}),
                expected_loss_before=math.nan,
                expected_loss_after=0.0,
                usage=ResourceUsage(money=1.0),
            )
        self.assertEqual(ledger.totals(), ResourceUsage())


class AuthorizationAndSchemaIntegration(unittest.TestCase):
    def test_dispatch_rejects_non_dispatch_authorization(self) -> None:
        from loopstrap_core.errors import AuthorityError

        with tempfile.TemporaryDirectory() as raw:
            system = make_system(
                raw,
                roles={
                    "implementer": {
                        "role_treatment": "implementer",
                        "requires": [],
                    }
                },
            )
            system.create_root(
                "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
            )
            prepare_cell(system, "root", leaf=True)
            with self.assertRaises(AuthorityError):
                dispatch(
                    system,
                    "root",
                    "implementer",
                    "implementer",
                    "implementation-lineage",
                    act="advance",
                )
            self.assertEqual(system.jobs, {})

    def test_configuration_rejects_boolean_coercion_and_bad_containers(self) -> None:
        from loopstrap_core.errors import SchemaError
        from loopstrap_core.harness import RoleRouter, RoleTreatmentRegistry

        row = treatment("one", behavior="clean")
        row["enabled"] = "false"
        with self.assertRaises(SchemaError):
            RoleTreatmentRegistry.from_dict(
                {"version": 1, "role_treatments": [row]}
            )
        with self.assertRaises(SchemaError):
            RoleTreatmentRegistry.from_dict(
                {"version": 1, "role_treatments": {}}
            )

        registry = RoleTreatmentRegistry.from_dict(
            {
                "version": 1,
                "role_treatments": [treatment("one", behavior="clean")],
            }
        )
        with self.assertRaises(SchemaError):
            RoleRouter.from_dict(
                registry,
                {
                    "version": 1,
                    "roles": {},
                    "independence": [
                        {
                            "role": "reviewer",
                            "from_role": "worker",
                            "different_role_treatment": "true",
                            "different_context_lineage": True,
                        }
                    ],
                },
            )
        with self.assertRaises(SchemaError):
            RoleRouter.from_dict(
                registry, {"version": 1, "roles": [], "independence": []}
            )


class WorkflowTransactionIntegration(unittest.TestCase):
    def make_graph(self):
        from loopstrap_core.workflow import RunGraph, WorkflowDefinition

        definition = WorkflowDefinition.from_dict(
            json.loads(
                (ROOT / "config" / "workflow.v1.json").read_text(encoding="utf-8")
            )
        )
        graph = RunGraph("run-test", definition)
        graph.create_root(
            "root",
            contract_ref="sha256:" + digest("contract"),
            obligations=["O1", "O2"],
            scope=("root",),
        )
        graph.accept_contract("root")
        graph.freeze_tests(
            "root",
            visible_digest=digest("visible"),
            holdout_digest=digest("holdout"),
            obligation_map={"O1": ["T1"], "O2": ["T2"]},
            executable=True,
        )
        graph.record_plan(
            "root",
            plan_digest=digest("plan"),
            responsibilities={"O1": "a", "O2": "b"},
        )
        return graph

    def test_decomposition_rejects_overlapping_obligation_ownership(self) -> None:
        from loopstrap_core.errors import DecompositionError
        from loopstrap_core.workflow import ChildSpec

        graph = self.make_graph()
        graph.record_pre_review("root", accepted=True, leaf=False, unresolved_seams=[])
        with self.assertRaises(DecompositionError):
            graph.decompose(
                "root",
                [
                    ChildSpec("root.1", ("O1",), "a", ("root", "one")),
                    ChildSpec("root.2", ("O1", "O2"), "b", ("root", "two")),
                ],
            )
        self.assertEqual(graph.cell("root").children, [])

    def test_rejected_pre_review_is_atomic(self) -> None:
        from loopstrap_core.errors import TransitionError

        graph = self.make_graph()
        cell = graph.cell("root")
        before = (
            cell.revision,
            cell.phase,
            cell.pre_review_accepted,
            cell.leaf,
            tuple(cell.unresolved_seams),
            len(graph.events),
        )
        with self.assertRaises(TransitionError):
            graph.record_pre_review(
                "root", accepted=True, leaf=True, unresolved_seams=["open-seam"]
            )
        after = (
            cell.revision,
            cell.phase,
            cell.pre_review_accepted,
            cell.leaf,
            tuple(cell.unresolved_seams),
            len(graph.events),
        )
        self.assertEqual(after, before)


class SystemFacadeIntegration(unittest.TestCase):
    def test_structured_harness_artifacts_and_claims_are_persisted(self) -> None:
        rich = treatment("rich", role="implementer", behavior="echo")
        rich["command"] = [sys.executable, str(RICH_MOCK)]
        rich["wrapper"]["id"] = sys.executable
        with tempfile.TemporaryDirectory() as raw:
            system = make_system(
                raw,
                roles={
                    "implementer": {
                        "role_treatment": "rich",
                        "requires": [],
                    }
                },
                treatments=[rich],
            )
            system.create_root(
                "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
            )
            prepare_cell(system, "root", leaf=True)
            job = dispatch(
                system,
                "root",
                "implementer",
                "rich",
                "implementation-lineage",
            )
            response = json.loads(system.artifacts.get_bytes(job.response_ref))
            self.assertEqual(response["artifacts"][0]["kind"], "analysis")
            self.assertEqual(response["claims"][0]["claim_id"], "model-claim-1")
            completed = [
                event
                for event in system.ledger.verify()
                if event["type"] == "harness.completed"
            ][0]
            self.assertEqual(completed["payload"]["artifacts"], response["artifacts"])
            self.assertEqual(completed["payload"]["claims"], response["claims"])

    def test_configured_reviews_require_job_provenance_and_see_candidate(self) -> None:
        from loopstrap_core.errors import AuthorityError

        treatments = [
            treatment(
                "pre-review",
                role="independent-adversary",
                behavior="echo",
                capabilities=("json",),
            ),
            treatment("implementer", behavior="write"),
            treatment(
                "post-review",
                role="independent-reviewer",
                behavior="echo",
                capabilities=("json",),
            ),
        ]
        roles = {
            "independent-adversary": {
                "role_treatment": "pre-review",
                "requires": ["json"],
            },
            "implementer": {
                "role_treatment": "implementer",
                "requires": ["workspace_write"],
            },
            "independent-reviewer": {
                "role_treatment": "post-review",
                "requires": ["json"],
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            system = make_system(raw, roles=roles, treatments=treatments)
            system.create_root(
                "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
            )
            system.accept_contract("root")
            system.freeze_tests(
                "root",
                visible_digest=digest("visible"),
                holdout_digest=digest("holdout"),
                obligation_map={"O1": ["T1"]},
                executable=True,
            )
            system.record_plan(
                "root",
                plan_digest=digest("plan"),
                responsibilities={"O1": "implementation"},
            )
            with self.assertRaises(AuthorityError):
                system.record_pre_review(
                    "root", accepted=True, leaf=True, unresolved_seams=[]
                )
            pre = dispatch(
                system,
                "root",
                "independent-adversary",
                "pre-review",
                "pre-review-lineage",
            )
            system.record_pre_review(
                "root",
                accepted=True,
                leaf=True,
                unresolved_seams=[],
                review_job_id=pre.job_id,
            )
            implementation = dispatch(
                system,
                "root",
                "implementer",
                "implementer",
                "implementation-lineage",
            )
            system.verify_job(
                implementation.job_id,
                passed=True,
                evidence_refs=["sha256:" + digest("tests-green")],
            )
            with self.assertRaises(AuthorityError):
                system.record_post_review(
                    "root",
                    accepted=True,
                    evidence_refs=["sha256:" + digest("review-green")],
                )
            review = dispatch(
                system,
                "root",
                "independent-reviewer",
                "post-review",
                "post-review-lineage",
            )
            self.assertTrue((review.workspace.path / "agent-output.txt").is_file())
            system.record_post_review(
                "root",
                accepted=True,
                evidence_refs=["sha256:" + digest("review-green")],
                review_job_id=review.job_id,
            )
            system.promote_job(implementation.job_id)
            system.close("root")

    def test_verified_claim_blocks_promotion(self) -> None:
        from loopstrap_core.errors import PromotionError

        with tempfile.TemporaryDirectory() as raw:
            system = make_system(
                raw,
                roles={
                    "implementer": {
                        "role_treatment": "implementer",
                        "requires": [],
                    }
                },
            )
            system.create_root(
                "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
            )
            prepare_cell(system, "root", leaf=True)
            job = dispatch(
                system,
                "root",
                "implementer",
                "implementer",
                "implementation-lineage",
            )
            system.verify_job(
                job.job_id,
                passed=True,
                evidence_refs=["sha256:" + digest("tests-green")],
            )
            system.record_post_review(
                "root",
                accepted=True,
                evidence_refs=["sha256:" + digest("review-green")],
            )
            system.graph.add_claim(
                "root",
                claim_id="counterexample",
                proposition="candidate violates O1",
                status="verified",
                evidence_refs=["sha256:" + digest("witness")],
            )
            with self.assertRaises(PromotionError):
                system.promote_job(job.job_id)

    def test_recursive_child_then_parent_integration_is_ledgered(self) -> None:
        from loopstrap_core.workflow import ChildSpec

        with tempfile.TemporaryDirectory() as raw:
            system = make_system(
                raw,
                roles={
                    "implementer": {
                        "role_treatment": "implementer",
                        "requires": [],
                    }
                },
            )
            system.create_root(
                "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
            )
            prepare_cell(system, "root", leaf=False)
            system.decompose(
                "root",
                [ChildSpec("root.1", ("O1",), "owner", ("root", "child"))],
            )
            prepare_cell(system, "root.1", leaf=True)
            job = dispatch(
                system,
                "root.1",
                "implementer",
                "implementer",
                "child-implementation",
            )
            system.verify_job(
                job.job_id,
                passed=True,
                evidence_refs=["sha256:" + digest("child-tests")],
            )
            system.record_post_review(
                "root.1",
                accepted=True,
                evidence_refs=["sha256:" + digest("child-review")],
            )
            system.promote_job(job.job_id)
            system.close("root.1")
            system.record_integration(
                "root",
                passed=True,
                evidence_refs=["sha256:" + digest("integration-green")],
            )
            system.record_post_review(
                "root",
                accepted=True,
                evidence_refs=["sha256:" + digest("parent-review")],
            )
            system.close("root")
            self.assertEqual(system.graph.phase_kind("root"), "closed")
            events = system.ledger.verify()
            event_types = [event["type"] for event in events]
            self.assertIn("cell.decomposed", event_types)
            self.assertGreaterEqual(event_types.count("cell.created"), 2)
            self.assertIn("integration.recorded", event_types)

    def test_digest_bound_visible_and_holdout_verification_plan(self) -> None:
        from loopstrap_core.errors import PromotionError
        from loopstrap_core.verification import TestCommand, VerificationPlan

        commands = [
            TestCommand(
                name="visible-output",
                visibility="visible",
                argv=(
                    sys.executable,
                    "-c",
                    "from pathlib import Path; assert Path('agent-output.txt').is_file()",
                ),
            ),
            TestCommand(
                name="holdout-content",
                visibility="holdout",
                argv=(
                    sys.executable,
                    "-c",
                    "from pathlib import Path; assert 'workspace' in Path('agent-output.txt').read_text()",
                ),
            ),
        ]
        plan = VerificationPlan.create(commands)
        with tempfile.TemporaryDirectory() as raw:
            system = make_system(
                raw,
                roles={
                    "implementer": {
                        "role_treatment": "implementer",
                        "requires": [],
                    }
                },
            )
            system.create_root(
                "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
            )
            prepare_cell(
                system,
                "root",
                leaf=True,
                test_digests=(plan.visible_digest, plan.holdout_digest),
            )
            job = dispatch(
                system,
                "root",
                "implementer",
                "implementer",
                "implementation-lineage",
            )
            wrong_plan = VerificationPlan.create(
                [
                    TestCommand(
                        name="different-visible-basis",
                        visibility=commands[0].visibility,
                        argv=commands[0].argv,
                    ),
                    commands[1],
                ]
            )
            with self.assertRaises(PromotionError):
                system.verify_job_with_plan(job.job_id, wrong_plan)
            self.assertEqual(system.graph.phase_kind("root"), "implementation")
            report_ref = system.verify_job_with_plan(job.job_id, plan)
            report = json.loads(system.artifacts.get_bytes(report_ref))
            self.assertTrue(report["passed"])
            self.assertEqual(
                {receipt["visibility"] for receipt in report["receipts"]},
                {"visible", "holdout"},
            )
            self.assertTrue(all(receipt["stdout_bytes"] >= 0 for receipt in report["receipts"]))
            self.assertEqual(system.graph.phase_kind("root"), "post_review")
