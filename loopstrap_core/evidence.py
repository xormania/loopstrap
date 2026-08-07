from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable

from .artifacts import ArtifactStore
from .atomic import canonical_json
from .errors import EvidenceError
from .specification import CUECompiler


DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SCOPE_KINDS = {"cell", "composite", "root"}


def _exact(data: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != fields:
        missing = fields - set(data) if isinstance(data, dict) else fields
        unknown = set(data) - fields if isinstance(data, dict) else set()
        raise EvidenceError(
            f"{label} fields invalid: missing={sorted(missing)} "
            f"unknown={sorted(unknown)}"
        )
    return data


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceError(f"{label} must be a nonempty string")
    return value


def _digest(value: Any, label: str) -> str:
    result = _text(value, label)
    if not DIGEST_RE.fullmatch(result):
        raise EvidenceError(f"{label} must be a SHA-256 reference")
    return result


def _strings(
    value: Any,
    label: str,
    *,
    nonempty: bool = True,
    unique: bool = True,
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise EvidenceError(f"{label} must be a valid string list")
    result = tuple(value)
    if unique and len(set(result)) != len(result):
        raise EvidenceError(f"{label} must be unique")
    return result


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    specification_digest: str
    cell_id: str
    cell_revision: int
    scope_kind: str
    scope_id: str
    role_treatment_id: str
    producer_id: str
    producer_class: str
    subject_producer_ids: tuple[str, ...]
    obligation_ids: tuple[str, ...]
    execution_ref: str
    artifact_refs: tuple[str, ...]
    observation: dict[str, Any]
    finding_ids: tuple[str, ...]

    FIELDS = {
        "id",
        "specification_digest",
        "cell_id",
        "cell_revision",
        "scope_kind",
        "scope_id",
        "role_treatment_id",
        "producer_id",
        "producer_class",
        "subject_producer_ids",
        "obligation_ids",
        "execution_ref",
        "artifact_refs",
        "observation",
        "finding_ids",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRecord":
        row = _exact(data, cls.FIELDS, "evidence record")
        revision = row["cell_revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise EvidenceError("Cell revision must be a positive integer")
        scope_kind = _text(row["scope_kind"], "evidence scope kind")
        if scope_kind not in SCOPE_KINDS:
            raise EvidenceError(f"unsupported evidence scope: {scope_kind}")
        observation = row["observation"]
        if not isinstance(observation, dict) or not observation:
            raise EvidenceError("evidence observation must be a nonempty object")
        return cls(
            evidence_id=_text(row["id"], "evidence id"),
            specification_digest=_digest(
                row["specification_digest"], "evidence specification digest"
            ),
            cell_id=_text(row["cell_id"], "evidence Cell id"),
            cell_revision=revision,
            scope_kind=scope_kind,
            scope_id=_text(row["scope_id"], "evidence scope id"),
            role_treatment_id=_text(
                row["role_treatment_id"], "evidence Role-Treatment id"
            ),
            producer_id=_text(row["producer_id"], "evidence producer id"),
            producer_class=_text(
                row["producer_class"], "evidence producer class"
            ),
            subject_producer_ids=_strings(
                row["subject_producer_ids"], "subject producer ids"
            ),
            obligation_ids=_strings(row["obligation_ids"], "evidence obligations"),
            execution_ref=_digest(row["execution_ref"], "execution reference"),
            artifact_refs=tuple(
                _digest(reference, "artifact reference")
                for reference in _strings(
                    row["artifact_refs"], "implementation artifact references"
                )
            ),
            observation=dict(observation),
            finding_ids=_strings(
                row["finding_ids"], "evidence finding ids", nonempty=False
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.evidence_id,
            "specification_digest": self.specification_digest,
            "cell_id": self.cell_id,
            "cell_revision": self.cell_revision,
            "scope_kind": self.scope_kind,
            "scope_id": self.scope_id,
            "role_treatment_id": self.role_treatment_id,
            "producer_id": self.producer_id,
            "producer_class": self.producer_class,
            "subject_producer_ids": list(self.subject_producer_ids),
            "obligation_ids": list(self.obligation_ids),
            "execution_ref": self.execution_ref,
            "artifact_refs": list(self.artifact_refs),
            "observation": dict(self.observation),
            "finding_ids": list(self.finding_ids),
        }


@dataclass(frozen=True)
class AcceptanceObligation:
    obligation_id: str
    scope_kind: str
    scope_id: str
    eligible_producer_classes: tuple[str, ...]
    minimum_evidence: int
    independent: bool

    FIELDS = {
        "id",
        "scope_kind",
        "scope_id",
        "eligible_producer_classes",
        "minimum_evidence",
        "independent",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AcceptanceObligation":
        row = _exact(data, cls.FIELDS, "acceptance obligation")
        scope_kind = _text(row["scope_kind"], "acceptance scope kind")
        if scope_kind not in SCOPE_KINDS:
            raise EvidenceError(f"unsupported acceptance scope: {scope_kind}")
        minimum = row["minimum_evidence"]
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            raise EvidenceError("minimum evidence must be a positive integer")
        if not isinstance(row["independent"], bool):
            raise EvidenceError("independence must be a boolean")
        return cls(
            obligation_id=_text(row["id"], "acceptance obligation id"),
            scope_kind=scope_kind,
            scope_id=_text(row["scope_id"], "acceptance scope id"),
            eligible_producer_classes=_strings(
                row["eligible_producer_classes"],
                "eligible producer classes",
            ),
            minimum_evidence=minimum,
            independent=row["independent"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.obligation_id,
            "scope_kind": self.scope_kind,
            "scope_id": self.scope_id,
            "eligible_producer_classes": list(self.eligible_producer_classes),
            "minimum_evidence": self.minimum_evidence,
            "independent": self.independent,
        }


@dataclass(frozen=True)
class AcceptanceRecord:
    acceptance_id: str
    specification_digest: str
    accepted: bool
    satisfied_obligation_ids: tuple[str, ...]
    unsatisfied_obligation_ids: tuple[str, ...]
    qualifying_evidence_ids: tuple[str, ...]
    unresolved_finding_ids: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AcceptanceRecord":
        row = _exact(
            data,
            {
                "id",
                "specification_digest",
                "accepted",
                "satisfied_obligation_ids",
                "unsatisfied_obligation_ids",
                "qualifying_evidence_ids",
                "unresolved_finding_ids",
            },
            "acceptance record",
        )
        if not isinstance(row["accepted"], bool):
            raise EvidenceError("acceptance verdict must be a boolean")
        return cls(
            acceptance_id=_text(row["id"], "acceptance record id"),
            specification_digest=_digest(
                row["specification_digest"], "acceptance record specification digest"
            ),
            accepted=row["accepted"],
            satisfied_obligation_ids=_strings(
                row["satisfied_obligation_ids"],
                "satisfied acceptance obligations",
                nonempty=False,
            ),
            unsatisfied_obligation_ids=_strings(
                row["unsatisfied_obligation_ids"],
                "unsatisfied acceptance obligations",
                nonempty=False,
            ),
            qualifying_evidence_ids=_strings(
                row["qualifying_evidence_ids"],
                "qualifying evidence ids",
                nonempty=False,
            ),
            unresolved_finding_ids=_strings(
                row["unresolved_finding_ids"],
                "unresolved acceptance findings",
                nonempty=False,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["id"] = result.pop("acceptance_id")
        for key in (
            "satisfied_obligation_ids",
            "unsatisfied_obligation_ids",
            "qualifying_evidence_ids",
            "unresolved_finding_ids",
        ):
            result[key] = list(result[key])
        return result


class AcceptanceEngine:
    @staticmethod
    def _qualifies(
        evidence: EvidenceRecord,
        obligation: AcceptanceObligation,
        *,
        specification_digest: str,
        current_revisions: dict[str, int],
    ) -> bool:
        return (
            evidence.specification_digest == specification_digest
            and evidence.scope_kind == obligation.scope_kind
            and evidence.scope_id == obligation.scope_id
            and obligation.obligation_id in evidence.obligation_ids
            and evidence.producer_class in obligation.eligible_producer_classes
            and current_revisions.get(evidence.cell_id) == evidence.cell_revision
            and not evidence.finding_ids
            and (
                not obligation.independent
                or evidence.producer_id not in evidence.subject_producer_ids
            )
        )

    def evaluate(
        self,
        *,
        acceptance_id: str,
        specification_digest: str,
        current_revisions: dict[str, int],
        obligations: Iterable[AcceptanceObligation],
        evidence: Iterable[EvidenceRecord],
        unresolved_finding_ids: Iterable[str],
    ) -> AcceptanceRecord:
        acceptance_id = _text(acceptance_id, "acceptance id")
        specification_digest = _digest(
            specification_digest, "acceptance specification digest"
        )
        if not isinstance(current_revisions, dict) or any(
            not isinstance(cell_id, str)
            or not cell_id
            or isinstance(revision, bool)
            or not isinstance(revision, int)
            or revision < 1
            for cell_id, revision in current_revisions.items()
        ):
            raise EvidenceError("current Cell revisions are invalid")
        obligation_rows = tuple(obligations)
        evidence_rows = tuple(evidence)
        unresolved = tuple(unresolved_finding_ids)
        if not obligation_rows:
            raise EvidenceError("acceptance requires at least one obligation")
        if len({item.obligation_id for item in obligation_rows}) != len(
            obligation_rows
        ):
            raise EvidenceError("acceptance obligation ids must be unique")
        if len({item.evidence_id for item in evidence_rows}) != len(evidence_rows):
            raise EvidenceError("evidence ids must be unique")
        if any(not isinstance(item, str) or not item for item in unresolved):
            raise EvidenceError("unresolved finding ids are invalid")

        satisfied: list[str] = []
        unsatisfied: list[str] = []
        qualifying: set[str] = set()
        for obligation in obligation_rows:
            matches = {
                item.evidence_id
                for item in evidence_rows
                if self._qualifies(
                    item,
                    obligation,
                    specification_digest=specification_digest,
                    current_revisions=current_revisions,
                )
            }
            if len(matches) >= obligation.minimum_evidence:
                satisfied.append(obligation.obligation_id)
                qualifying.update(matches)
            else:
                unsatisfied.append(obligation.obligation_id)
        return AcceptanceRecord(
            acceptance_id=acceptance_id,
            specification_digest=specification_digest,
            accepted=not unsatisfied and not unresolved,
            satisfied_obligation_ids=tuple(sorted(satisfied)),
            unsatisfied_obligation_ids=tuple(sorted(unsatisfied)),
            qualifying_evidence_ids=tuple(sorted(qualifying)),
            unresolved_finding_ids=tuple(sorted(set(unresolved))),
        )


class EvidenceCompiler:
    def __init__(self, cue: CUECompiler) -> None:
        self.cue = cue

    def record(self, data: dict[str, Any]) -> EvidenceRecord:
        self.cue.validate_data(
            data,
            schema_file="evidence.cue",
            definition="#EvidenceRecord",
        )
        return EvidenceRecord.from_dict(data)

    def evaluate(self, data: dict[str, Any]) -> AcceptanceRecord:
        self.cue.validate_data(
            data,
            schema_file="evidence.cue",
            definition="#AcceptanceRequest",
        )
        row = _exact(
            data,
            {
                "acceptance_id",
                "specification_digest",
                "current_revisions",
                "obligations",
                "evidence",
                "unresolved_finding_ids",
            },
            "acceptance request",
        )
        return AcceptanceEngine().evaluate(
            acceptance_id=row["acceptance_id"],
            specification_digest=row["specification_digest"],
            current_revisions=dict(row["current_revisions"]),
            obligations=[
                AcceptanceObligation.from_dict(item)
                for item in row["obligations"]
            ],
            evidence=[EvidenceRecord.from_dict(item) for item in row["evidence"]],
            unresolved_finding_ids=list(row["unresolved_finding_ids"]),
        )


@dataclass(frozen=True)
class RawExecutionRecord:
    artifact_ref: str
    redaction_count: int


class RawExecutionCustodian:
    _KEY_VALUE = re.compile(
        r"(?im)\b(api[_-]?key|token|password|secret|credential)\b"
        r"(\s*[:=]\s*)([^\s]+)"
    )
    _BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{8,}")

    def __init__(self, artifacts: ArtifactStore) -> None:
        self.artifacts = artifacts

    @classmethod
    def _redact(cls, value: bytes) -> tuple[str, int]:
        text = value.decode("utf-8", errors="replace")
        text, first = cls._KEY_VALUE.subn(
            lambda match: (
                f"{match.group(1)}{match.group(2)}[REDACTED]"
            ),
            text,
        )
        text, second = cls._BEARER.subn("Bearer [REDACTED]", text)
        return text, first + second

    def retain(self, *, stdout: bytes, stderr: bytes) -> RawExecutionRecord:
        if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
            raise EvidenceError("raw execution streams must be bytes")
        safe_stdout, stdout_count = self._redact(stdout)
        safe_stderr, stderr_count = self._redact(stderr)
        artifact_ref = self.artifacts.put_bytes(
            canonical_json(
                {
                    "stdout": safe_stdout,
                    "stderr": safe_stderr,
                    "redaction_count": stdout_count + stderr_count,
                }
            ),
            media_type="application/json",
        )
        return RawExecutionRecord(
            artifact_ref=artifact_ref,
            redaction_count=stdout_count + stderr_count,
        )
