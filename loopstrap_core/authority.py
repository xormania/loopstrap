from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, ClassVar

from .errors import AuthorityError, SchemaError, StaleResultError


def _exact_fields(data: dict[str, Any], allowed: set[str], object_name: str) -> None:
    unknown = set(data) - allowed
    missing = allowed - set(data)
    if unknown or missing:
        raise SchemaError(
            f"{object_name} fields invalid: missing={sorted(missing)} unknown={sorted(unknown)}"
        )


@dataclass(frozen=True)
class ControlView:
    run_id: str
    cell_id: str
    phase: str
    revision: int
    pending_claim_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    budget_remaining: dict[str, float]

    FIELDS: ClassVar[set[str]] = {
        "run_id",
        "cell_id",
        "phase",
        "revision",
        "pending_claim_ids",
        "evidence_refs",
        "budget_remaining",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ControlView":
        _exact_fields(data, cls.FIELDS, "control view")
        if not isinstance(data["revision"], int) or data["revision"] < 0:
            raise SchemaError("control view revision must be a nonnegative integer")
        return cls(
            run_id=str(data["run_id"]),
            cell_id=str(data["cell_id"]),
            phase=str(data["phase"]),
            revision=data["revision"],
            pending_claim_ids=tuple(str(item) for item in data["pending_claim_ids"]),
            evidence_refs=tuple(str(item) for item in data["evidence_refs"]),
            budget_remaining={str(key): float(value) for key, value in data["budget_remaining"].items()},
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["pending_claim_ids"] = list(self.pending_claim_ids)
        result["evidence_refs"] = list(self.evidence_refs)
        return result


@dataclass(frozen=True)
class Authorization:
    authorization_id: str
    run_id: str
    cell_id: str
    revision: int
    role: str
    role_treatment_id: str
    act: str

    FIELDS: ClassVar[set[str]] = {
        "authorization_id",
        "run_id",
        "cell_id",
        "revision",
        "role",
        "role_treatment_id",
        "act",
    }
    COORDINATION_ACTS: ClassVar[set[str]] = {"dispatch", "advance", "park", "reopen"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Authorization":
        _exact_fields(data, cls.FIELDS, "authorization")
        act = str(data["act"])
        if act not in cls.COORDINATION_ACTS:
            raise AuthorityError(f"Conductor cannot authorize act: {act}")
        if not isinstance(data["revision"], int) or data["revision"] < 0:
            raise SchemaError("authorization revision must be a nonnegative integer")
        return cls(
            authorization_id=str(data["authorization_id"]),
            run_id=str(data["run_id"]),
            cell_id=str(data["cell_id"]),
            revision=data["revision"],
            role=str(data["role"]),
            role_treatment_id=str(data["role_treatment_id"]),
            act=act,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuthorizationValidator:
    @staticmethod
    def validate(
        authorization: Authorization,
        view: ControlView,
        *,
        required_role: str,
        role_treatment_id: str,
    ) -> None:
        bindings = (
            authorization.run_id == view.run_id,
            authorization.cell_id == view.cell_id,
            authorization.revision == view.revision,
            authorization.role == required_role,
            authorization.role_treatment_id == role_treatment_id,
        )
        if not all(bindings):
            raise StaleResultError("authorization bindings do not match current control state")
