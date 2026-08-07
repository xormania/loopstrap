from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from support import (
    authorization,
    certification_authority,
    compiled_specification,
    digest,
    dispatch,
    make_system,
    prepare_leaf,
    treatment,
    workflow,
)


class RecoveryReadiness(unittest.TestCase):
    def test_open_reconstructs_graph_jobs_and_specification_binding(self) -> None:
        from loopstrap_core.system import LoopstrapSystem

        spec = compiled_specification()
        roles = {
            "implementer": {
                "role_treatment": "mock",
                "requires": [],
            }
        }
        rows = [treatment("mock", behavior="write")]
        with tempfile.TemporaryDirectory() as raw:
            system = make_system(
                raw,
                roles=roles,
                treatments=rows,
                specification=spec,
            )
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1"],
            )
            prepare_leaf(system, "root")
            job = dispatch(system, "root", "implementer", "mock", "implementation")
            reopened = LoopstrapSystem.open(
                root_dir=Path(raw) / "run",
                workflow=workflow(),
                role_treatments={
                    "version": 1,
                    "role_treatments": rows,
                },
                role_policy={"version": 1, "roles": roles},
                specification=spec,
                certification_authority=certification_authority(
                    rows, Path(raw)
                ),
            )
            self.assertEqual(reopened.run_id, system.run_id)
            self.assertEqual(reopened.specification.digest, spec.digest)
            self.assertEqual(reopened.graph.to_dict(), system.graph.to_dict())
            self.assertIn(job.job_id, reopened.jobs)
            self.assertEqual(
                reopened.jobs[job.job_id].response_ref,
                job.response_ref,
            )

    def test_resume_reuses_completed_dispatch(self) -> None:
        from loopstrap_core.system import LoopstrapSystem

        spec = compiled_specification()
        roles = {
            "implementer": {
                "role_treatment": "mock",
                "requires": [],
            }
        }
        rows = [treatment("mock", behavior="write")]
        with tempfile.TemporaryDirectory() as raw:
            system = make_system(
                raw,
                roles=roles,
                treatments=rows,
                specification=spec,
            )
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1"],
            )
            prepare_leaf(system, "root")
            original = dispatch(system, "root", "implementer", "mock", "implementation")
            reopened = LoopstrapSystem.open(
                root_dir=Path(raw) / "run",
                workflow=workflow(),
                role_treatments={
                    "version": 1,
                    "role_treatments": rows,
                },
                role_policy={"version": 1, "roles": roles},
                specification=spec,
                certification_authority=certification_authority(
                    rows, Path(raw)
                ),
            )
            before = len(
                [
                    event
                    for event in reopened.ledger.verify()
                    if event["type"] == "harness.completed"
                ]
            )
            reused = reopened.dispatch(
                authorization(reopened, "root", "implementer", "mock"),
                prompt_ref="sha256:" + digest("root.implementer.prompt"),
                context_manifest_ref="sha256:" + digest("root.implementer.context"),
                context_lineage="implementation",
                cache_lineage=None,
            )
            after = len(
                [
                    event
                    for event in reopened.ledger.verify()
                    if event["type"] == "harness.completed"
                ]
            )
            self.assertEqual(reused.job_id, original.job_id)
            self.assertEqual(after, before)

    def test_competing_promotions_record_one_conflict(self) -> None:
        from loopstrap_core.errors import StaleResultError
        from loopstrap_core.workflow import ChildSpec

        spec = compiled_specification()
        roles = {
            "implementer": {
                "role_treatment": "mock",
                "requires": [],
            }
        }
        rows = [treatment("mock", behavior="write")]
        with tempfile.TemporaryDirectory() as raw:
            system = make_system(
                raw,
                roles=roles,
                treatments=rows,
                specification=spec,
            )
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1", "G2"],
            )
            system.accept_contract("root")
            system.freeze_tests(
                "root",
                visible_digest=digest("root.visible"),
                holdout_digest=digest("root.holdout"),
                obligation_map={"G1": ["T1"], "G2": ["T2"]},
                executable=True,
            )
            system.record_plan(
                "root",
                plan_digest=digest("root.plan"),
                responsibilities={"G1": "one", "G2": "two"},
            )
            system.record_pre_review(
                "root", accepted=True, leaf=False, unresolved_seams=[]
            )
            system.decompose(
                "root",
                [
                    ChildSpec(
                        "root.one",
                        ("G1",),
                        "one",
                        ("root", "one"),
                        contract_ref="contract.one",
                    ),
                    ChildSpec(
                        "root.two",
                        ("G2",),
                        "two",
                        ("root", "two"),
                        contract_ref="contract.two",
                    ),
                ],
            )
            for child_id in ("root.one", "root.two"):
                prepare_leaf(system, child_id)
            first = dispatch(system, "root.one", "implementer", "mock", "first")
            second = dispatch(system, "root.two", "implementer", "mock", "second")
            system.verify_job(
                first.job_id,
                passed=True,
                evidence_refs=["sha256:" + digest("first.tests")],
            )
            system.verify_job(
                second.job_id,
                passed=True,
                evidence_refs=["sha256:" + digest("second.tests")],
            )
            system.record_post_review(
                "root.one",
                accepted=True,
                evidence_refs=["sha256:" + digest("first.review")],
            )
            system.record_post_review(
                "root.two",
                accepted=True,
                evidence_refs=["sha256:" + digest("second.review")],
            )
            system.promote_job(first.job_id)
            with self.assertRaises(StaleResultError):
                system.promote_job(second.job_id)
            conflicts = [
                event
                for event in system.ledger.verify()
                if event["type"] == "promotion.conflict"
            ]
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0]["payload"]["job_id"], second.job_id)

    def test_pause_halt_intervention_and_owner_resume_are_replayable(self) -> None:
        from loopstrap_core.errors import AuthorityError, TransitionError

        with tempfile.TemporaryDirectory() as raw:
            system = make_system(raw, specification=compiled_specification())
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1"],
            )
            system.pause(reason="operator inspection")
            with self.assertRaises(TransitionError):
                system.accept_contract("root")
            with self.assertRaises(AuthorityError):
                system.resume(owner_authorization_ref="")
            system.record_intervention(
                owner_authorization_ref="owner:1",
                action="continue",
                reason="inspection complete",
            )
            system.resume(owner_authorization_ref="owner:1")
            system.accept_contract("root")
            system.halt(reason="hard stop")
            with self.assertRaises(TransitionError):
                system.resume(owner_authorization_ref="owner:1")
            state = system.replay_state()
            self.assertEqual(state["run_status"], "halted")
            self.assertEqual(len(state["interventions"]), 1)
