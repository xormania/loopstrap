from __future__ import annotations

import tempfile
import unittest

from support import (
    digest,
    dispatch,
    evidence_data,
    make_system,
    prepare_leaf,
    treatment,
)


class EvidenceReadiness(unittest.TestCase):
    def test_evidence_record_requires_complete_bindings(self) -> None:
        from loopstrap_core.evidence import EvidenceRecord
        from loopstrap_core.errors import EvidenceError

        complete = EvidenceRecord.from_dict(evidence_data())
        self.assertEqual(complete.cell_revision, 7)
        for field in (
            "specification_digest",
            "cell_revision",
            "role_treatment_id",
            "producer_class",
            "obligation_ids",
            "execution_ref",
            "artifact_refs",
        ):
            incomplete = evidence_data()
            del incomplete[field]
            with self.assertRaises(EvidenceError, msg=field):
                EvidenceRecord.from_dict(incomplete)

    def test_independence_rejects_self_authored_evidence(self) -> None:
        from loopstrap_core.evidence import (
            AcceptanceEngine,
            AcceptanceObligation,
            EvidenceRecord,
        )

        row = evidence_data(producer_id="implementer")
        row["subject_producer_ids"] = ["implementer"]
        evidence = EvidenceRecord.from_dict(row)
        obligation = AcceptanceObligation.from_dict(
            {
                "id": "verify.cell.first",
                "scope_kind": "cell",
                "scope_id": "cell.first",
                "eligible_producer_classes": ["test_harness"],
                "minimum_evidence": 1,
                "independent": True,
            }
        )
        result = AcceptanceEngine().evaluate(
            acceptance_id="accept.cell.first",
            specification_digest=row["specification_digest"],
            current_revisions={"cell.first": 7},
            obligations=[obligation],
            evidence=[evidence],
            unresolved_finding_ids=[],
        )
        self.assertFalse(result.accepted)
        self.assertIn("verify.cell.first", result.unsatisfied_obligation_ids)

    def test_acceptance_requires_evidence_at_each_scope(self) -> None:
        from loopstrap_core.evidence import (
            AcceptanceEngine,
            AcceptanceObligation,
            EvidenceRecord,
        )

        obligations = [
            AcceptanceObligation.from_dict(
                {
                    "id": "verify.cell.first",
                    "scope_kind": "cell",
                    "scope_id": "cell.first",
                    "eligible_producer_classes": ["test_harness"],
                    "minimum_evidence": 1,
                    "independent": True,
                }
            ),
            AcceptanceObligation.from_dict(
                {
                    "id": "verify.composite.root",
                    "scope_kind": "composite",
                    "scope_id": "composite.root",
                    "eligible_producer_classes": ["integration_harness"],
                    "minimum_evidence": 1,
                    "independent": True,
                }
            ),
            AcceptanceObligation.from_dict(
                {
                    "id": "verify.system.root",
                    "scope_kind": "root",
                    "scope_id": "root",
                    "eligible_producer_classes": ["system_harness"],
                    "minimum_evidence": 1,
                    "independent": True,
                }
            ),
        ]
        cell_only = EvidenceRecord.from_dict(evidence_data())
        result = AcceptanceEngine().evaluate(
            acceptance_id="accept.root",
            specification_digest=cell_only.specification_digest,
            current_revisions={"cell.first": 7},
            obligations=obligations,
            evidence=[cell_only],
            unresolved_finding_ids=[],
        )
        self.assertFalse(result.accepted)
        self.assertEqual(
            set(result.unsatisfied_obligation_ids),
            {"verify.composite.root", "verify.system.root"},
        )

    def test_raw_execution_is_retained_with_secret_redaction(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.evidence import RawExecutionCustodian

        with tempfile.TemporaryDirectory() as raw:
            store = ArtifactStore(__import__("pathlib").Path(raw))
            record = RawExecutionCustodian(store).retain(
                stdout=b"analysis complete\napi_key=super-secret\n",
                stderr=b"warning without credential\n",
            )
            retained = store.get_bytes(record.artifact_ref)
            self.assertIn(b"analysis complete", retained)
            self.assertIn(b"warning without credential", retained)
            self.assertNotIn(b"super-secret", retained)
            self.assertIn(b"[REDACTED]", retained)
            self.assertEqual(record.redaction_count, 1)

        roles = {
            "implementer": {
                "role_treatment": "mock",
                "requires": [],
            }
        }
        rows = [treatment("mock", behavior="write")]
        with tempfile.TemporaryDirectory() as raw:
            system = make_system(raw, roles=roles, treatments=rows)
            system.create_root(
                "root",
                contract_ref="contract.root",
                obligations=["G1"],
            )
            prepare_leaf(system, "root")
            job = dispatch(
                system,
                "root",
                "implementer",
                "mock",
                "implementation",
            )
            self.assertIsNotNone(job.result.execution_ref)
            captured = system.artifacts.get_bytes(job.result.execution_ref)
            self.assertIn(b"invocation_id", captured)
            completed = next(
                event
                for event in system.ledger.verify()
                if event["type"] == "harness.completed"
            )
            self.assertEqual(
                completed["payload"]["execution_ref"],
                job.result.execution_ref,
            )

    def test_stale_wrong_incomplete_or_findings_block_acceptance(self) -> None:
        from loopstrap_core.evidence import (
            AcceptanceEngine,
            AcceptanceObligation,
            EvidenceRecord,
        )

        row = evidence_data()
        evidence = EvidenceRecord.from_dict(row)
        obligation = AcceptanceObligation.from_dict(
            {
                "id": "verify.cell.first",
                "scope_kind": "cell",
                "scope_id": "cell.first",
                "eligible_producer_classes": ["test_harness"],
                "minimum_evidence": 1,
                "independent": True,
            }
        )
        engine = AcceptanceEngine()
        cases = (
            {
                "specification_digest": "sha256:" + digest("wrong"),
                "current_revisions": {"cell.first": 7},
                "unresolved_finding_ids": [],
            },
            {
                "specification_digest": row["specification_digest"],
                "current_revisions": {"cell.first": 8},
                "unresolved_finding_ids": [],
            },
            {
                "specification_digest": row["specification_digest"],
                "current_revisions": {"cell.first": 7},
                "unresolved_finding_ids": ["finding.open"],
            },
        )
        for case in cases:
            result = engine.evaluate(
                acceptance_id="accept.cell.first",
                obligations=[obligation],
                evidence=[evidence],
                **case,
            )
            self.assertFalse(result.accepted)
