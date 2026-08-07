from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from support import (
    CUE_BINARY,
    CUE_PIN,
    CUE_SCHEMA,
    PROJECT_FIXTURE,
    compiled_specification,
    compiler,
    make_system,
)


class SpecificationReadiness(unittest.TestCase):
    def test_cue_tool_pin_rejects_wrong_digest_or_version(self) -> None:
        from loopstrap_core.errors import IntegrityError
        from loopstrap_core.specification import CUECompiler, ToolPin

        pin_data = json.loads(CUE_PIN.read_text(encoding="utf-8"))
        valid = CUECompiler(
            binary=CUE_BINARY,
            pin=ToolPin(
                version=pin_data["version"],
                sha256=pin_data["binary_sha256"],
            ),
            schema_root=CUE_SCHEMA,
        )
        valid.verify_tool()
        with self.assertRaises(IntegrityError):
            CUECompiler(
                binary=CUE_BINARY,
                pin=ToolPin(version=pin_data["version"], sha256="0" * 64),
                schema_root=CUE_SCHEMA,
            ).verify_tool()
        with self.assertRaises(IntegrityError):
            CUECompiler(
                binary=CUE_BINARY,
                pin=ToolPin(
                    version="v0.0.0",
                    sha256=pin_data["binary_sha256"],
                ),
                schema_root=CUE_SCHEMA,
            ).verify_tool()

    def test_cross_document_reference_failure_is_rejected(self) -> None:
        from loopstrap_core.errors import SpecificationError

        with tempfile.TemporaryDirectory() as raw:
            candidate = Path(raw) / "project"
            shutil.copytree(PROJECT_FIXTURE, candidate)
            contracts = candidate / "contracts.cue"
            contracts.write_text(
                contracts.read_text(encoding="utf-8").replace(
                    '"term.document"', '"term.missing"'
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SpecificationError):
                compiler().compile(candidate)

    def test_snapshot_is_canonical_roundtrippable_and_digest_bound(self) -> None:
        from loopstrap_core.specification import SpecificationSnapshot

        first = compiled_specification()
        second = compiled_specification()
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.to_bytes(), second.to_bytes())
        self.assertTrue(first.digest.startswith("sha256:"))
        restored = SpecificationSnapshot.from_bytes(first.to_bytes())
        self.assertEqual(restored, first)
        mutated = json.loads(first.to_bytes())
        mutated["project"]["name"] = "different"
        with self.assertRaises(ValueError):
            SpecificationSnapshot.from_bytes(
                json.dumps(mutated, sort_keys=True).encode("utf-8"),
                expected_digest=first.digest,
            )

    def test_run_and_root_cell_bind_exact_specification(self) -> None:
        snapshot = compiled_specification()
        with tempfile.TemporaryDirectory() as raw:
            system = make_system(raw, specification=snapshot)
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["guarantee.root"],
            )
            self.assertEqual(system.specification.digest, snapshot.digest)
            self.assertEqual(
                system.graph.cell("root").specification_digest,
                snapshot.digest,
            )
            events = system.ledger.verify()
            self.assertEqual(
                events[0]["payload"]["specification_digest"],
                snapshot.digest,
            )
            created = next(event for event in events if event["type"] == "cell.created")
            self.assertEqual(
                created["payload"]["specification_digest"],
                snapshot.digest,
            )
