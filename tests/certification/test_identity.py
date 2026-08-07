from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from support import authority, issue_receipt, load_contract, treatment


class CertificationIdentity(unittest.TestCase):
    def test_enablement_is_not_certification(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.certification import CertificationAuthority
        from loopstrap_core.harness import RoleTreatmentRegistry

        row = treatment(enabled=True)
        parsed = RoleTreatmentRegistry.from_dict(
            {"version": 1, "role_treatments": [row]}
        ).get(row["id"])
        self.assertTrue(parsed.enabled)
        self.assertNotIn("available", parsed.to_dict())
        with tempfile.TemporaryDirectory() as raw:
            empty = CertificationAuthority(
                contract_digest=load_contract().digest,
                artifacts=ArtifactStore(Path(raw) / "artifacts"),
                receipts=(),
            )
            self.assertFalse(empty.is_certified(parsed))

    def test_complete_identity_and_executable_drift_invalidate(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.harness import RoleTreatment

        with tempfile.TemporaryDirectory() as raw:
            executable = Path(raw) / "vendor-cli"
            executable.write_bytes(b"vendor-v1\n")
            row = treatment()
            row["command"] = [str(executable), "--structured"]
            row["wrapper"]["id"] = str(executable)
            artifacts = ArtifactStore(Path(raw) / "artifacts")
            certs = authority(row, artifacts)
            original = RoleTreatment.from_dict(row)
            self.assertTrue(certs.is_certified(original))
            changed = deepcopy(row)
            changed["reasoning"]["requested"] = "different"
            self.assertFalse(certs.is_certified(RoleTreatment.from_dict(changed)))

            receipt = issue_receipt(row, artifacts)
            self.assertEqual(
                receipt.executables[0].sha256,
                "sha256:" + __import__("hashlib").sha256(executable.read_bytes()).hexdigest(),
            )
            executable.write_bytes(b"vendor-v2\n")
            self.assertFalse(certs.is_certified(original))

    def test_receipt_is_machine_owned_canonical_and_evidence_bound(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.certification import CertificationReceipt

        with tempfile.TemporaryDirectory() as raw:
            artifacts = ArtifactStore(Path(raw) / "artifacts")
            receipt = issue_receipt(treatment(), artifacts)
            self.assertEqual(receipt.issuer, "loopstrap-certifier-v1")
            self.assertEqual(receipt, CertificationReceipt.from_dict(receipt.to_dict()))
            self.assertTrue(all(artifacts.get_bytes(ref) for ref in receipt.evidence_refs))
            self.assertIsNone(receipt.report_ref)
            self.assertEqual(receipt.reference, receipt.reference_for(receipt.to_dict()))

    def test_nonpass_layer_cannot_become_certified(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.harness import RoleTreatment

        for status in ("FAIL", "BLOCKED", "WARN", "INFO", "SKIP"):
            with tempfile.TemporaryDirectory() as raw:
                artifacts = ArtifactStore(Path(raw) / "artifacts")
                certs = authority(
                    treatment(),
                    artifacts,
                    statuses={
                        "mechanical": "PASS",
                        "inference": status,
                        "loopstrap": "PASS",
                    },
                )
                self.assertFalse(
                    certs.is_certified(RoleTreatment.from_dict(treatment()))
                )

    def test_router_requires_enabled_and_matching_receipt(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.certification import CertificationAuthority
        from loopstrap_core.errors import RoleTreatmentUnavailableError
        from loopstrap_core.harness import RoleRouter, RoleTreatmentRegistry

        policy = {
            "version": 1,
            "roles": {
                "implementer": {
                    "role_treatment": "mock-certified",
                    "requires": [],
                }
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            artifacts = ArtifactStore(Path(raw) / "artifacts")
            row = treatment()
            registry = RoleTreatmentRegistry.from_dict(
                {"version": 1, "role_treatments": [row]}
            )
            empty = CertificationAuthority(
                contract_digest=load_contract().digest,
                artifacts=artifacts,
                receipts=(),
            )
            router = RoleRouter.from_dict(
                registry, policy, certification_authority=empty
            )
            with self.assertRaises(RoleTreatmentUnavailableError):
                router.resolve("implementer", assignments=[])

            certified = RoleRouter.from_dict(
                registry,
                policy,
                certification_authority=authority(row, artifacts),
            )
            self.assertEqual(
                certified.resolve("implementer", assignments=[]).id,
                "mock-certified",
            )

            disabled_row = treatment(enabled=False)
            disabled_registry = RoleTreatmentRegistry.from_dict(
                {"version": 1, "role_treatments": [disabled_row]}
            )
            disabled = RoleRouter.from_dict(
                disabled_registry,
                policy,
                certification_authority=authority(disabled_row, artifacts),
            )
            with self.assertRaises(RoleTreatmentUnavailableError):
                disabled.resolve("implementer", assignments=[])
