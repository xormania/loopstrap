from __future__ import annotations

import ast
import copy
from pathlib import Path
from typing import Any
import unittest

from support import ROOT, contract_graph_data, minimal_cell


def interior(
    template: dict[str, Any],
    composite_id: str,
    controls: str,
    members: tuple[str, str],
) -> dict[str, Any]:
    """A composite declared as the interior of `controls`, holding `members`."""
    composite = copy.deepcopy(template)
    composite["id"] = composite_id
    composite["cell_id"] = controls
    composite["members"] = list(members)
    composite["connections"] = [
        {
            "source": {"cell_id": members[0], "port_id": "out"},
            "target": {"cell_id": members[1], "port_id": "in"},
        }
    ]
    composite["external_inputs"] = [{"cell_id": members[0], "port_id": "in"}]
    composite["external_outputs"] = [{"cell_id": members[1], "port_id": "out"}]
    guarantee = composite["guarantees"][0]
    guarantee["id"] = f"guarantee.{composite_id}"
    guarantee["supported_by"] = [f"guarantee.{member}" for member in members]
    guarantee["verification_obligation_ids"] = [f"verify.{composite_id}"]
    composite["verification_obligations"][0]["id"] = f"verify.{composite_id}"
    return composite


def containment_data(*, cyclic: bool) -> dict[str, Any]:
    """Three levels of containment, closing on themselves or not.

    Both graphs declare the same six Cells and the same three composites. The
    only difference is what cell.third's interior holds: two fresh Cells, or
    cell.first again — so the contrast isolates the cycle and nothing else.

    No composite ever contains the Cell it is the interior of, so a check that
    only compares a composite's own members against its controlling Cell admits
    the cyclic graph while the recursion still never bottoms out.
    """
    data = contract_graph_data()
    for source, sink in (("cell.third", "cell.fourth"), ("cell.fifth", "cell.sixth")):
        data["cells"].append(minimal_cell(source, contract_ref=f"contract.{source}"))
        data["cells"].append(
            minimal_cell(
                sink,
                input_schema="schema.analysis",
                output_schema="schema.result",
                contract_ref=f"contract.{sink}",
            )
        )

    template = data["composites"][0]
    deeper = ("cell.first", "cell.second") if cyclic else ("cell.fifth", "cell.sixth")
    data["composites"].extend(
        [
            interior(template, "composite.inner", "cell.first", ("cell.third", "cell.fourth")),
            interior(template, "composite.deeper", "cell.third", deeper),
        ]
    )
    return data


class ContractReadiness(unittest.TestCase):
    def test_cell_contract_requires_complete_mechanical_boundary(self) -> None:
        from loopstrap_core.contracts import ContractGraph
        from loopstrap_core.errors import SchemaError

        data = contract_graph_data()
        del data["cells"][0]["outputs"]
        with self.assertRaises(SchemaError):
            ContractGraph.from_dict(data)

    def test_composite_rejects_incompatible_connection(self) -> None:
        from loopstrap_core.contracts import ContractGraph
        from loopstrap_core.errors import DecompositionError

        data = contract_graph_data()
        data["cells"][1]["inputs"][0]["schema_ref"] = "schema.incompatible"
        with self.assertRaises(DecompositionError):
            ContractGraph.from_dict(data)

    def test_composite_guarantee_requires_real_support(self) -> None:
        from loopstrap_core.contracts import ContractGraph
        from loopstrap_core.errors import DecompositionError

        data = contract_graph_data()
        data["composites"][0]["guarantees"][0]["supported_by"] = [
            "guarantee.unknown"
        ]
        with self.assertRaises(DecompositionError):
            ContractGraph.from_dict(data)

    def test_responsibility_modes_distinguish_overlap_from_exclusivity(self) -> None:
        from loopstrap_core.contracts import ContractGraph
        from loopstrap_core.errors import DecompositionError

        shared = contract_graph_data()
        for cell in shared["cells"]:
            cell["contract_refs"] = ["contract.shared"]
            cell["guarantees"][0]["contract_refs"] = ["contract.shared"]
            cell["guarantees"][0]["responsibility"] = "shared"
        ContractGraph.from_dict(shared)

        exclusive = contract_graph_data()
        for cell in exclusive["cells"]:
            cell["contract_refs"] = ["contract.exclusive"]
            cell["guarantees"][0]["contract_refs"] = ["contract.exclusive"]
            cell["guarantees"][0]["responsibility"] = "exclusive"
        with self.assertRaises(DecompositionError):
            ContractGraph.from_dict(exclusive)

    def test_cell_dependency_must_name_a_declared_cell(self) -> None:
        from loopstrap_core.contracts import ContractGraph
        from loopstrap_core.errors import DecompositionError

        declared = contract_graph_data()
        declared["cells"][1]["dependencies"] = ["cell.first"]
        ContractGraph.from_dict(declared)

        undeclared = contract_graph_data()
        undeclared["cells"][1]["dependencies"] = ["cell.undeclared"]
        with self.assertRaises(DecompositionError):
            ContractGraph.from_dict(undeclared)

    def test_composite_containment_cannot_form_a_cycle(self) -> None:
        from loopstrap_core.contracts import ContractGraph
        from loopstrap_core.errors import DecompositionError

        ContractGraph.from_dict(containment_data(cyclic=False))

        with self.assertRaises(DecompositionError):
            ContractGraph.from_dict(containment_data(cyclic=True))

    def test_cell_is_the_only_recursive_work_unit_name(self) -> None:
        class_names: set[str] = set()
        for path in (ROOT / "loopstrap_core").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            class_names.update(
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            )
        self.assertIn("Cell", class_names)
        self.assertNotIn("Slice", class_names)
