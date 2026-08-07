from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import math
from typing import Any

from .errors import SchemaError


INTEGER_RESOURCES = {"tokens", "retries"}


def _nonnegative_number(name: str, value: Any, *, integer: bool) -> None:
    if isinstance(value, bool):
        raise SchemaError(f"{name} must be a nonnegative {'integer' if integer else 'number'}")
    if integer:
        if not isinstance(value, int) or value < 0:
            raise SchemaError(f"{name} must be a nonnegative integer")
        return
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
        raise SchemaError(f"{name} must be a finite nonnegative number")


@dataclass
class ResourceUsage:
    money: float = 0.0
    tokens: int = 0
    latency_seconds: float = 0.0
    compute: float = 0.0
    retries: int = 0
    risk: float = 0.0
    human_attention: float = 0.0

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)

    def validate(self) -> None:
        for field in fields(ResourceUsage):
            _nonnegative_number(
                f"resource usage {field.name}",
                getattr(self, field.name),
                integer=field.name in INTEGER_RESOURCES,
            )

    def __add__(self, other: "ResourceUsage") -> "ResourceUsage":
        self.validate()
        other.validate()
        result = ResourceUsage(
            **{
                field.name: getattr(self, field.name) + getattr(other, field.name)
                for field in fields(ResourceUsage)
            }
        )
        result.validate()
        return result


@dataclass(frozen=True)
class HardLimits:
    money: float | None = None
    tokens: int | None = None
    latency_seconds: float | None = None
    compute: float | None = None
    retries: int | None = None
    risk: float | None = None
    human_attention: float | None = None

    def validate(self) -> None:
        for field in fields(HardLimits):
            value = getattr(self, field.name)
            if value is not None:
                _nonnegative_number(
                    f"hard limit {field.name}",
                    value,
                    integer=field.name in INTEGER_RESOURCES,
                )


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    basis: str
    marginal_cost: float | None = None
    expected_loss_reduction: float | None = None


@dataclass(frozen=True)
class MarginalValuePolicy:
    version: int
    shadow_prices: dict[str, float]

    def validate(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise SchemaError("marginal-value policy version must be a positive integer")
        if not isinstance(self.shadow_prices, dict):
            raise SchemaError("shadow prices must be an object")
        known = {field.name for field in fields(ResourceUsage)}
        unknown = set(self.shadow_prices) - known
        if unknown:
            raise SchemaError(f"unknown shadow-price resources: {sorted(unknown)}")
        for name, value in self.shadow_prices.items():
            _nonnegative_number(f"shadow price {name}", value, integer=False)

    def marginal_cost(self, usage: ResourceUsage) -> float:
        self.validate()
        usage.validate()
        return sum(
            float(getattr(usage, field.name)) * float(self.shadow_prices.get(field.name, 0.0))
            for field in fields(ResourceUsage)
        )

    def should_continue(
        self,
        *,
        expected_loss_before: float,
        expected_loss_after: float,
        marginal_usage: ResourceUsage,
    ) -> bool:
        _nonnegative_number("expected loss before", expected_loss_before, integer=False)
        _nonnegative_number("expected loss after", expected_loss_after, integer=False)
        reduction = expected_loss_before - expected_loss_after
        return reduction > self.marginal_cost(marginal_usage)


class BudgetLedger:
    def __init__(self, *, limits: HardLimits | None = None) -> None:
        self.limits = limits or HardLimits()
        self.limits.validate()
        self._totals = ResourceUsage()

    def charge(self, usage: ResourceUsage) -> None:
        usage.validate()
        self._totals = self._totals + usage

    def totals(self) -> ResourceUsage:
        return ResourceUsage(**self._totals.to_dict())

    def _hard_limit_breached(self, prospective: ResourceUsage) -> bool:
        for field in fields(HardLimits):
            limit = getattr(self.limits, field.name)
            if limit is not None and getattr(prospective, field.name) > limit:
                return True
        return False

    def authorize(
        self,
        policy: MarginalValuePolicy,
        expected_loss_before: float,
        expected_loss_after: float,
        usage: ResourceUsage,
    ) -> BudgetDecision:
        policy.validate()
        usage.validate()
        _nonnegative_number("expected loss before", expected_loss_before, integer=False)
        _nonnegative_number("expected loss after", expected_loss_after, integer=False)
        prospective = self._totals + usage
        if self._hard_limit_breached(prospective):
            return BudgetDecision(False, "hard_limit")
        cost = policy.marginal_cost(usage)
        reduction = expected_loss_before - expected_loss_after
        return BudgetDecision(
            allowed=reduction > cost,
            basis="marginal_value",
            marginal_cost=cost,
            expected_loss_reduction=reduction,
        )
