from __future__ import annotations

import unittest

from support import digest, workflow_definition


class AuthorityAcceptance(unittest.TestCase):
    def test_control_view_is_compact_and_rejects_content_plane_fields(self) -> None:
        from loopstrap_core.authority import ControlView
        from loopstrap_core.errors import SchemaError

        view = ControlView.from_dict(
            {
                "run_id": "run-1",
                "cell_id": "root",
                "phase": "planning",
                "revision": 4,
                "pending_claim_ids": ["claim-1"],
                "evidence_refs": ["sha256:" + digest("evidence")],
                "budget_remaining": {"money": 10.0},
            }
        )
        encoded = view.to_dict()
        forbidden = {"source", "code", "patch", "diff", "logs", "transcript", "prompt", "credential"}
        self.assertTrue(forbidden.isdisjoint(encoded))
        for key in forbidden:
            bad = dict(encoded)
            bad[key] = "content that must not enter the control plane"
            with self.assertRaises(SchemaError, msg=key):
                ControlView.from_dict(bad)

    def test_conductor_authorization_cannot_grant_write_or_git_acts(self) -> None:
        from loopstrap_core.authority import Authorization
        from loopstrap_core.errors import AuthorityError

        base = {
            "authorization_id": "auth-1",
            "run_id": "run-1",
            "cell_id": "root",
            "revision": 2,
            "role": "planner",
            "role_treatment_id": "claude-fable",
        }
        for act in ("write", "edit", "promote", "commit", "push", "merge", "git"):
            with self.assertRaises(AuthorityError, msg=act):
                Authorization.from_dict({**base, "act": act})
        for act in ("dispatch", "advance", "park", "reopen"):
            self.assertEqual(Authorization.from_dict({**base, "act": act}).act, act)

    def test_authorization_is_bound_to_exact_control_revision_and_treatment(self) -> None:
        from loopstrap_core.authority import Authorization, AuthorizationValidator, ControlView
        from loopstrap_core.errors import StaleResultError

        view = ControlView.from_dict(
            {
                "run_id": "run-1",
                "cell_id": "root.1",
                "phase": "implementation",
                "revision": 7,
                "pending_claim_ids": [],
                "evidence_refs": [],
                "budget_remaining": {},
            }
        )
        auth = Authorization.from_dict(
            {
                "authorization_id": "auth-7",
                "run_id": "run-1",
                "cell_id": "root.1",
                "revision": 7,
                "role": "implementer",
                "role_treatment_id": "codex-sol",
                "act": "dispatch",
            }
        )
        AuthorizationValidator.validate(auth, view, required_role="implementer", role_treatment_id="codex-sol")
        for changed in (
            {"revision": 8},
            {"cell_id": "root.2"},
            {"run_id": "run-2"},
        ):
            with self.assertRaises(StaleResultError):
                AuthorizationValidator.validate(
                    auth,
                    ControlView.from_dict({**view.to_dict(), **changed}),
                    required_role="implementer",
                    role_treatment_id="codex-sol",
                )
        with self.assertRaises(StaleResultError):
            AuthorizationValidator.validate(
                auth, view, required_role="implementer", role_treatment_id="grok-build"
            )


class WorkflowAcceptance(unittest.TestCase):
    def make_graph(self):
        from loopstrap_core.workflow import RunGraph, WorkflowDefinition

        return RunGraph("run-1", WorkflowDefinition.from_dict(workflow_definition()))

    def ready_for_pre_review(self, graph, cell_id: str, obligations: tuple[str, ...]) -> None:
        graph.accept_contract(cell_id)
        graph.freeze_tests(
            cell_id,
            visible_digest=digest(cell_id + "-visible"),
            holdout_digest=digest(cell_id + "-holdout"),
            obligation_map={item: [f"test::{item}"] for item in obligations},
            executable=True,
        )
        graph.record_plan(
            cell_id,
            plan_digest=digest(cell_id + "-plan"),
            responsibilities={item: "implementation" for item in obligations},
        )

    def test_workflow_names_and_roles_come_from_versioned_data(self) -> None:
        from loopstrap_core.workflow import RunGraph, WorkflowDefinition

        data = workflow_definition()
        data["version"] = 73
        phases = data["phases"]
        phases["tests_before_plan"]["role"] = "arbitrary_role_name"
        definition = WorkflowDefinition.from_dict(data)
        graph = RunGraph("run-x", definition)
        graph.create_root("root", contract_ref="sha256:" + digest("contract"), obligations=["O1"])
        graph.accept_contract("root")
        self.assertEqual(definition.version, 73)
        self.assertEqual(graph.required_role("root"), "arbitrary_role_name")

    def test_planning_is_impossible_before_frozen_obligation_mapped_tests(self) -> None:
        from loopstrap_core.errors import TransitionError

        graph = self.make_graph()
        graph.create_root("root", contract_ref="sha256:" + digest("contract"), obligations=["O1", "O2"])
        graph.accept_contract("root")
        with self.assertRaises(TransitionError):
            graph.record_plan("root", plan_digest=digest("plan"), responsibilities={"O1": "x"})
        with self.assertRaises(TransitionError):
            graph.freeze_tests(
                "root",
                visible_digest=digest("visible"),
                holdout_digest=digest("holdout"),
                obligation_map={"O1": ["test-o1"]},
                executable=True,
            )
        graph.freeze_tests(
            "root",
            visible_digest=digest("visible"),
            holdout_digest=digest("holdout"),
            obligation_map={"O1": ["test-o1"], "O2": ["test-o2"]},
            executable=True,
        )
        self.assertEqual(graph.phase_kind("root"), "plan")

    def test_test_writer_context_structurally_excludes_implementation_material(self) -> None:
        from loopstrap_core.context import ContextManifest
        from loopstrap_core.errors import ContextBoundaryError

        allowed = ContextManifest.for_role(
            role_kind="tests",
            artifact_refs={
                "contract": "sha256:" + digest("contract"),
                "corpus": "sha256:" + digest("corpus"),
            },
        )
        self.assertEqual(set(allowed.artifact_refs), {"contract", "corpus"})
        for forbidden in ("implementation", "candidate_diff", "patch", "transcript"):
            with self.assertRaises(ContextBoundaryError):
                ContextManifest.for_role(
                    role_kind="tests",
                    artifact_refs={
                        "contract": "sha256:" + digest("contract"),
                        forbidden: "sha256:" + digest(forbidden),
                    },
                )

    def test_frozen_test_revision_reopens_and_invalidates_downstream_evidence(self) -> None:
        graph = self.make_graph()
        graph.create_root("root", contract_ref="sha256:" + digest("contract"), obligations=["O1"])
        self.ready_for_pre_review(graph, "root", ("O1",))
        graph.record_pre_review("root", accepted=True, leaf=True, unresolved_seams=[])
        old_revision = graph.cell("root").revision
        graph.revise_tests(
            "root",
            visible_digest=digest("revised-visible"),
            holdout_digest=digest("revised-holdout"),
            obligation_map={"O1": ["test-revised"]},
            executable=True,
            reason="verified test defect",
        )
        cell = graph.cell("root")
        self.assertGreater(cell.revision, old_revision)
        self.assertEqual(graph.phase_kind("root"), "plan")
        self.assertIsNone(cell.plan_digest)
        self.assertTrue(any(event["type"] == "tests.revised" for event in graph.events))

    def test_pre_review_is_required_before_leaf_or_decomposition(self) -> None:
        from loopstrap_core.errors import TransitionError
        from loopstrap_core.workflow import ChildSpec

        graph = self.make_graph()
        graph.create_root("root", contract_ref="sha256:" + digest("contract"), obligations=["O1", "O2"])
        self.ready_for_pre_review(graph, "root", ("O1", "O2"))
        with self.assertRaises(TransitionError):
            graph.decompose(
                "root",
                [
                    ChildSpec("root.1", ("O1",), "owner-a", ("root", "a")),
                    ChildSpec("root.2", ("O2",), "owner-b", ("root", "b")),
                ],
            )
        with self.assertRaises(TransitionError):
            graph.record_verification("root", passed=True, evidence_refs=["sha256:" + digest("green")])

    def test_decomposition_requires_coverage_ownership_and_real_narrowing(self) -> None:
        from loopstrap_core.errors import DecompositionError
        from loopstrap_core.workflow import ChildSpec

        graph = self.make_graph()
        graph.create_root(
            "root", contract_ref="sha256:" + digest("contract"), obligations=["O1", "O2"], scope=("root",)
        )
        self.ready_for_pre_review(graph, "root", ("O1", "O2"))
        graph.record_pre_review("root", accepted=True, leaf=False, unresolved_seams=[])
        invalid_sets = (
            [ChildSpec("root.1", ("O1",), "owner", ("root", "a"))],
            [
                ChildSpec("root.1", ("O1",), "", ("root", "a")),
                ChildSpec("root.2", ("O2",), "owner", ("root", "b")),
            ],
            [ChildSpec("root.1", ("O1", "O2"), "owner", ("root",))],
            [
                ChildSpec("root.1", ("O1",), "owner", ("root", "a")),
                ChildSpec("root.1", ("O2",), "owner", ("root", "b")),
            ],
        )
        for children in invalid_sets:
            with self.assertRaises(DecompositionError):
                graph.decompose("root", children)
        graph.decompose(
            "root",
            [
                ChildSpec("root.1", ("O1",), "owner-a", ("root", "a")),
                ChildSpec("root.2", ("O2",), "owner-b", ("root", "b")),
            ],
        )
        self.assertEqual(graph.cell("root").children, ["root.1", "root.2"])

    def test_recursion_is_evidence_bounded_not_depth_bounded(self) -> None:
        from loopstrap_core.workflow import ChildSpec

        graph = self.make_graph()
        graph.create_root(
            "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"], scope=("root",)
        )
        parent = "root"
        for depth in range(1, 9):
            self.ready_for_pre_review(graph, parent, ("O1",))
            graph.record_pre_review(parent, accepted=True, leaf=False, unresolved_seams=[])
            child = f"{parent}.1"
            graph.decompose(
                parent,
                [ChildSpec(child, ("O1",), f"owner-{depth}", tuple(["root", *map(str, range(1, depth + 1))]))],
            )
            parent = child
        self.assertEqual(graph.cell(parent).depth, 8)

    def test_leaf_readiness_reports_each_missing_evidence_class(self) -> None:
        graph = self.make_graph()
        graph.create_root("root", contract_ref="sha256:" + digest("contract"), obligations=["O1"])
        missing = graph.leaf_readiness("root")
        self.assertTrue(
            {
                "tests_frozen",
                "obligations_tested",
                "responsibilities_mapped",
                "owner_assigned",
                "tests_executable",
                "seams_resolved",
                "pre_review_accepted",
            }.issubset(set(missing))
        )
        self.ready_for_pre_review(graph, "root", ("O1",))
        graph.record_pre_review("root", accepted=True, leaf=True, unresolved_seams=[])
        self.assertEqual(graph.leaf_readiness("root"), [])

    def test_verified_counterexample_blocks_closure_but_suspicion_does_not(self) -> None:
        from loopstrap_core.errors import ClosureError

        graph = self.make_graph()
        graph.create_root("root", contract_ref="sha256:" + digest("contract"), obligations=["O1"])
        self.ready_for_pre_review(graph, "root", ("O1",))
        graph.record_pre_review("root", accepted=True, leaf=True, unresolved_seams=[])
        graph.record_verification("root", passed=True, evidence_refs=["sha256:" + digest("green")])
        graph.add_claim(
            "root",
            claim_id="suspicion",
            proposition="something may be wrong",
            status="suspected",
            evidence_refs=[],
        )
        graph.record_post_review("root", accepted=True, evidence_refs=["sha256:" + digest("review")])
        graph.close("root")
        graph.reopen("root", reason="new verified evidence")
        graph.add_claim(
            "root",
            claim_id="counterexample",
            proposition="O1 fails for witness W",
            status="verified",
            evidence_refs=["sha256:" + digest("witness")],
        )
        graph.add_approval("root", reviewer_id="a")
        graph.add_approval("root", reviewer_id="b")
        graph.add_approval("root", reviewer_id="c")
        with self.assertRaises(ClosureError):
            graph.close("root")
        graph.resolve_claim(
            "root",
            "counterexample",
            resolution_ref="sha256:" + digest("fix"),
            verification_ref="sha256:" + digest("fix-verified"),
        )
        graph.close("root")

    def test_composite_waits_for_children_integration_and_post_review(self) -> None:
        from loopstrap_core.errors import ClosureError
        from loopstrap_core.workflow import ChildSpec

        graph = self.make_graph()
        graph.create_root("root", contract_ref="sha256:" + digest("contract"), obligations=["O1"])
        self.ready_for_pre_review(graph, "root", ("O1",))
        graph.record_pre_review("root", accepted=True, leaf=False, unresolved_seams=[])
        graph.decompose("root", [ChildSpec("root.1", ("O1",), "owner", ("root", "child"))])
        with self.assertRaises(ClosureError):
            graph.close("root")
        self.ready_for_pre_review(graph, "root.1", ("O1",))
        graph.record_pre_review("root.1", accepted=True, leaf=True, unresolved_seams=[])
        graph.record_verification(
            "root.1", passed=True, evidence_refs=["sha256:" + digest("child-green")]
        )
        graph.record_post_review(
            "root.1", accepted=True, evidence_refs=["sha256:" + digest("child-review")]
        )
        graph.close("root.1")
        with self.assertRaises(ClosureError):
            graph.close("root")
        graph.record_integration("root", passed=True, evidence_refs=["sha256:" + digest("integration")])
        with self.assertRaises(ClosureError):
            graph.close("root")
        graph.record_post_review("root", accepted=True, evidence_refs=["sha256:" + digest("parent-review")])
        graph.close("root")

    def test_ancestor_defect_routes_to_lowest_common_ancestor_and_reopens_it(self) -> None:
        from loopstrap_core.workflow import ChildSpec

        graph = self.make_graph()
        graph.create_root(
            "root", contract_ref="sha256:" + digest("contract"), obligations=["O1", "O2"], scope=("root",)
        )
        self.ready_for_pre_review(graph, "root", ("O1", "O2"))
        graph.record_pre_review("root", accepted=True, leaf=False, unresolved_seams=[])
        graph.decompose(
            "root",
            [
                ChildSpec("root.1", ("O1",), "owner-a", ("root", "a")),
                ChildSpec("root.2", ("O2",), "owner-b", ("root", "b")),
            ],
        )
        self.assertEqual(graph.lowest_common_ancestor(["root.1", "root.2"]), "root")
        target = graph.route_verified_issue(
            affected_cells=["root.1", "root.2"],
            claim_id="seam",
            proposition="the sibling boundary is incomplete",
            evidence_refs=["sha256:" + digest("seam-witness")],
        )
        self.assertEqual(target, "root")
        self.assertEqual(graph.phase_kind("root"), "pre_review")
        self.assertIn("seam", graph.cell("root").claims)

