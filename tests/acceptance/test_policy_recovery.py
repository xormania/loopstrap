from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from support import digest


class BudgetAcceptance(unittest.TestCase):
    def test_budget_accounts_for_each_resource_without_currency_collapse(self) -> None:
        from loopstrap_core.budget import BudgetLedger, ResourceUsage

        ledger = BudgetLedger()
        ledger.charge(
            ResourceUsage(
                money=1.25,
                tokens=900,
                latency_seconds=3.5,
                compute=2.0,
                retries=1,
                risk=0.2,
                human_attention=0.5,
            )
        )
        self.assertEqual(
            ledger.totals().to_dict(),
            {
                "money": 1.25,
                "tokens": 900,
                "latency_seconds": 3.5,
                "compute": 2.0,
                "retries": 1,
                "risk": 0.2,
                "human_attention": 0.5,
            },
        )

    def test_hard_limit_overrides_positive_expected_value(self) -> None:
        from loopstrap_core.budget import (
            BudgetLedger,
            HardLimits,
            MarginalValuePolicy,
            ResourceUsage,
        )

        usage = ResourceUsage(money=11, tokens=1, human_attention=0)
        policy = MarginalValuePolicy(
            version=1,
            shadow_prices={"money": 1.0, "tokens": 0.0, "human_attention": 100.0},
        )
        self.assertTrue(
            policy.should_continue(
                expected_loss_before=1_000,
                expected_loss_after=0,
                marginal_usage=usage,
            )
        )
        ledger = BudgetLedger(limits=HardLimits(money=10))
        decision = ledger.authorize(policy, 1_000, 0, usage)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.basis, "hard_limit")

    def test_marginal_value_uses_configured_shadow_prices(self) -> None:
        from loopstrap_core.budget import MarginalValuePolicy, ResourceUsage

        policy = MarginalValuePolicy(
            version=9,
            shadow_prices={
                "money": 1.0,
                "tokens": 0.001,
                "latency_seconds": 0.5,
                "compute": 2.0,
                "retries": 5.0,
                "risk": 100.0,
                "human_attention": 500.0,
            },
        )
        cheap = ResourceUsage(money=1, tokens=100)
        expensive_attention = ResourceUsage(money=1, tokens=100, human_attention=1)
        self.assertTrue(
            policy.should_continue(
                expected_loss_before=100, expected_loss_after=90, marginal_usage=cheap
            )
        )
        self.assertFalse(
            policy.should_continue(
                expected_loss_before=100,
                expected_loss_after=90,
                marginal_usage=expensive_attention,
            )
        )


class CorpusAcceptance(unittest.TestCase):
    def packet(self, *, count: int = 2, conflicts: tuple[str, ...] = ()):
        from loopstrap_core.corpus import EvidencePacket, EvidenceSource

        sources = [
            EvidenceSource(
                source_id=f"source-{index}",
                uri=f"https://example.invalid/{index}",
                sha256=digest(f"source-{index}"),
                retrieved_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
                authority="primary" if index == 0 else "independent",
                citations=(f"section-{index}",),
                propositions=("choice-x-is-conventional",),
            )
            for index in range(count)
        ]
        return EvidencePacket.create(
            packet_id="packet-1",
            proposition="choice-x-is-conventional",
            sources=sources,
            conflicts=conflicts,
        )

    def test_evidence_packet_requires_hashes_citations_time_and_propositions(self) -> None:
        from loopstrap_core.corpus import EvidencePacket, EvidenceSource
        from loopstrap_core.errors import EvidenceError

        packet = self.packet()
        self.assertEqual(len(packet.sources), 2)
        self.assertEqual(packet.sources[0].sha256, digest("source-0"))
        invalid = EvidenceSource(
            source_id="bad",
            uri="https://example.invalid/bad",
            sha256="not-a-digest",
            retrieved_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
            authority="primary",
            citations=(),
            propositions=("choice-x-is-conventional",),
        )
        with self.assertRaises(EvidenceError):
            EvidencePacket.create(
                packet_id="bad",
                proposition="choice-x-is-conventional",
                sources=[invalid],
            )

    def test_sufficiency_policy_is_versioned_and_configurable(self) -> None:
        from loopstrap_core.corpus import EvidencePolicy

        one = self.packet(count=1)
        permissive = EvidencePolicy(version=1, minimum_independent_sources=1)
        strict = EvidencePolicy(version=2, minimum_independent_sources=2)
        self.assertTrue(permissive.assess(one).sufficient)
        self.assertFalse(strict.assess(one).sufficient)
        self.assertNotEqual(permissive.version, strict.version)

    def test_only_interior_nonobservable_choice_can_auto_resolve(self) -> None:
        from loopstrap_core.corpus import CorpusResolver, EvidencePolicy, ResolutionRequest

        packet = self.packet()
        policy = EvidencePolicy(version=1, minimum_independent_sources=2)
        interior = ResolutionRequest(
            request_id="r1",
            cell_id="root.1",
            proposition="choice-x-is-conventional",
            impact="interior_implementation",
            nearest_capable_ancestor="root.1",
        )
        self.assertEqual(CorpusResolver.resolve(interior, packet, policy).action, "auto_resolve")
        for impact in (
            "observable_behavior",
            "authority",
            "ownership",
            "guarantee",
            "product_judgment",
        ):
            request = ResolutionRequest(
                request_id=f"r-{impact}",
                cell_id="root.1",
                proposition="choice-x-is-conventional",
                impact=impact,
                nearest_capable_ancestor="root",
            )
            decision = CorpusResolver.resolve(request, packet, policy)
            self.assertEqual(decision.action, "route")
            self.assertEqual(decision.target_cell_id, "root")

    def test_conflict_or_insufficiency_routes_instead_of_guessing(self) -> None:
        from loopstrap_core.corpus import CorpusResolver, EvidencePolicy, ResolutionRequest

        request = ResolutionRequest(
            request_id="r1",
            cell_id="root.1.2",
            proposition="choice-x-is-conventional",
            impact="interior_implementation",
            nearest_capable_ancestor="root.1",
        )
        policy = EvidencePolicy(version=1, minimum_independent_sources=2)
        for packet in (self.packet(count=1), self.packet(conflicts=("source disagreement",))):
            decision = CorpusResolver.resolve(request, packet, policy)
            self.assertEqual(decision.action, "route")
            self.assertEqual(decision.target_cell_id, "root.1")


class RecoveryAcceptance(unittest.TestCase):
    def test_duplicate_dispatch_reservation_reuses_original_job(self) -> None:
        from loopstrap_core.ledger import EventLedger
        from loopstrap_core.recovery import DispatchJournal

        with tempfile.TemporaryDirectory() as raw:
            ledger = EventLedger(Path(raw) / "events.jsonl", run_id="run-1")
            journal = DispatchJournal(ledger)
            first = journal.reserve(
                dispatch_key="root.1:r3:implementer",
                cell_id="root.1",
                cell_revision=3,
                role="implementer",
                role_treatment_id="codex-sol",
            )
            second = DispatchJournal(ledger).reserve(
                dispatch_key="root.1:r3:implementer",
                cell_id="root.1",
                cell_revision=3,
                role="implementer",
                role_treatment_id="codex-sol",
            )
            self.assertEqual(first.job_id, second.job_id)
            events = ledger.verify()
            self.assertEqual(
                [event["type"] for event in events].count("job.reserved"),
                1,
            )

    def test_superseded_response_is_recorded_but_rejected_from_state(self) -> None:
        from loopstrap_core.errors import StaleResultError
        from loopstrap_core.ledger import EventLedger
        from loopstrap_core.recovery import DispatchJournal

        with tempfile.TemporaryDirectory() as raw:
            ledger = EventLedger(Path(raw) / "events.jsonl", run_id="run-1")
            journal = DispatchJournal(ledger)
            reservation = journal.reserve(
                dispatch_key="root:r2:planner",
                cell_id="root",
                cell_revision=2,
                role="planner",
                role_treatment_id="claude-fable",
            )
            with self.assertRaises(StaleResultError):
                journal.accept_response(
                    reservation.job_id,
                    response_revision=2,
                    current_cell_revision=3,
                    response_ref="sha256:" + digest("late response"),
                )
            types = [event["type"] for event in ledger.verify()]
            self.assertIn("job.result_rejected_stale", types)
            self.assertNotIn("job.result_accepted", types)

