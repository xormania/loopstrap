from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .errors import EvidenceError


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


@dataclass(frozen=True)
class EvidenceSource:
    source_id: str
    uri: str
    sha256: str
    retrieved_at: datetime
    authority: str
    citations: tuple[str, ...]
    propositions: tuple[str, ...]

    def validate(self, proposition: str) -> None:
        if not self.source_id or not self.uri:
            raise EvidenceError("corpus source identity and URI are required")
        if not _valid_digest(self.sha256):
            raise EvidenceError(f"corpus source digest is invalid: {self.source_id}")
        if self.retrieved_at.tzinfo is None:
            raise EvidenceError(f"corpus retrieval time lacks timezone: {self.source_id}")
        if not self.authority:
            raise EvidenceError(f"corpus source authority is absent: {self.source_id}")
        if not self.citations or any(not citation for citation in self.citations):
            raise EvidenceError(f"corpus source citations are absent: {self.source_id}")
        if proposition not in self.propositions:
            raise EvidenceError(f"corpus source does not support packet proposition: {self.source_id}")


@dataclass(frozen=True)
class EvidencePacket:
    packet_id: str
    proposition: str
    sources: tuple[EvidenceSource, ...]
    conflicts: tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        packet_id: str,
        proposition: str,
        sources: list[EvidenceSource],
        conflicts: tuple[str, ...] = (),
    ) -> "EvidencePacket":
        if not packet_id or not proposition or not sources:
            raise EvidenceError("evidence packet identity, proposition, and sources are required")
        if len({source.source_id for source in sources}) != len(sources):
            raise EvidenceError("evidence packet source ids must be unique")
        for source in sources:
            source.validate(proposition)
        return cls(
            packet_id=packet_id,
            proposition=proposition,
            sources=tuple(sources),
            conflicts=tuple(conflicts),
        )


@dataclass(frozen=True)
class EvidenceAssessment:
    sufficient: bool
    basis: str


@dataclass(frozen=True)
class EvidencePolicy:
    version: int
    minimum_independent_sources: int

    def assess(self, packet: EvidencePacket) -> EvidenceAssessment:
        if self.version < 1 or self.minimum_independent_sources < 1:
            raise EvidenceError("evidence policy values must be positive")
        if packet.conflicts:
            return EvidenceAssessment(False, "conflict")
        if len(packet.sources) < self.minimum_independent_sources:
            return EvidenceAssessment(False, "insufficient_sources")
        return EvidenceAssessment(True, "policy_satisfied")


@dataclass(frozen=True)
class ResolutionRequest:
    request_id: str
    cell_id: str
    proposition: str
    impact: str
    nearest_capable_ancestor: str


@dataclass(frozen=True)
class ResolutionDecision:
    action: str
    target_cell_id: str
    policy_version: int
    basis: str


class CorpusResolver:
    CONTRACT_IMPACTS = {
        "observable_behavior",
        "authority",
        "ownership",
        "guarantee",
        "product_judgment",
    }

    @classmethod
    def resolve(
        cls,
        request: ResolutionRequest,
        packet: EvidencePacket,
        policy: EvidencePolicy,
    ) -> ResolutionDecision:
        if request.proposition != packet.proposition:
            raise EvidenceError("resolution request and evidence packet propositions differ")
        assessment = policy.assess(packet)
        if request.impact == "interior_implementation" and assessment.sufficient:
            return ResolutionDecision(
                action="auto_resolve",
                target_cell_id=request.cell_id,
                policy_version=policy.version,
                basis=assessment.basis,
            )
        if request.impact != "interior_implementation" and request.impact not in cls.CONTRACT_IMPACTS:
            raise EvidenceError(f"unknown resolution impact: {request.impact}")
        return ResolutionDecision(
            action="route",
            target_cell_id=request.nearest_capable_ancestor,
            policy_version=policy.version,
            basis=assessment.basis if not assessment.sufficient else "contract_impact",
        )

