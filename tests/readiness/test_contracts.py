from __future__ import annotations

import ast
from pathlib import Path
import unittest

from support import ROOT, contract_graph_data


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
