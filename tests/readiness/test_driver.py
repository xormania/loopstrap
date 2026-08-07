from __future__ import annotations

import tempfile
import unittest

from support import compiled_specification, digest, make_system


def valid_result(request):
    kind = request.phase_kind
    cell = request.cell
    if kind == "contract":
        return {"accepted": True}
    if kind == "tests":
        return {
            "visible_digest": digest(f"{cell.cell_id}.visible"),
            "holdout_digest": digest(f"{cell.cell_id}.holdout"),
            "obligation_map": {
                obligation: [f"test::{cell.cell_id}::{obligation}"]
                for obligation in cell.obligations
            },
            "executable": True,
        }
    if kind == "plan":
        return {
            "plan_digest": digest(f"{cell.cell_id}.plan"),
            "responsibilities": {
                obligation: "implementation"
                for obligation in cell.obligations
            },
        }
    if kind == "pre_review":
        if cell.parent_id is None:
            return {
                "accepted": True,
                "leaf": False,
                "unresolved_seams": [],
                "children": [
                    {
                        "cell_id": "root.parse",
                        "obligations": ["G1"],
                        "owner": "parser",
                        "scope": ["root", "parse"],
                        "contract_ref": "contract.parse",
                    },
                    {
                        "cell_id": "root.analyze",
                        "obligations": ["G2"],
                        "owner": "analyzer",
                        "scope": ["root", "analyze"],
                        "contract_ref": "contract.analyze",
                    },
                ],
            }
        return {"accepted": True, "leaf": True, "unresolved_seams": []}
    if kind == "implementation":
        return {
            "passed": True,
            "evidence_refs": ["sha256:" + digest(f"{cell.cell_id}.tests")],
        }
    if kind == "integration":
        return {
            "passed": True,
            "evidence_refs": ["sha256:" + digest(f"{cell.cell_id}.integration")],
        }
    if kind == "post_review":
        return {
            "accepted": True,
            "evidence_refs": ["sha256:" + digest(f"{cell.cell_id}.review")],
        }
    raise AssertionError(f"unexpected driver phase: {kind}")


class DriverReadiness(unittest.TestCase):
    def test_driver_recurses_through_children_and_integrates_root(self) -> None:
        from loopstrap_core.driver import LoopDriver

        with tempfile.TemporaryDirectory() as raw:
            system = make_system(raw, specification=compiled_specification())
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1", "G2"],
            )
            outcome = LoopDriver(system, valid_result).run()
            self.assertEqual(outcome.status, "complete")
            self.assertEqual(system.graph.phase_kind("root"), "closed")
            self.assertEqual(
                {cell_id for cell_id in system.graph.cells},
                {"root", "root.parse", "root.analyze"},
            )
            self.assertTrue(
                all(
                    system.graph.phase_kind(cell_id) == "closed"
                    for cell_id in system.graph.cells
                )
            )
            event_types = [event["type"] for event in system.ledger.verify()]
            self.assertIn("integration.recorded", event_types)

    def test_driver_never_dispatches_implementation_early(self) -> None:
        from loopstrap_core.driver import LoopDriver

        seen: dict[str, list[str]] = {}

        def recording(request):
            seen.setdefault(request.cell.cell_id, []).append(request.phase_kind)
            return valid_result(request)

        with tempfile.TemporaryDirectory() as raw:
            system = make_system(raw, specification=compiled_specification())
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1", "G2"],
            )
            LoopDriver(system, recording).run()
            for order in seen.values():
                if "implementation" not in order:
                    continue
                self.assertLess(order.index("tests"), order.index("implementation"))
                self.assertLess(order.index("pre_review"), order.index("implementation"))

    def test_invalid_role_result_parks_without_guessing(self) -> None:
        from loopstrap_core.driver import LoopDriver

        with tempfile.TemporaryDirectory() as raw:
            system = make_system(raw, specification=compiled_specification())
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1"],
            )
            outcome = LoopDriver(system, lambda request: {}).run()
            self.assertEqual(outcome.status, "parked")
            self.assertEqual(system.run_status, "parked")
            self.assertEqual(system.graph.phase_kind("root"), "contract")
            self.assertIn(
                "run.parked",
                [event["type"] for event in system.ledger.verify()],
            )
