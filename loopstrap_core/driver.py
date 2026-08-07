from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .errors import LoopstrapError, SchemaError
from .system import LoopstrapSystem, SystemJob
from .workflow import Cell, ChildSpec


class RoleResultProvider(Protocol):
    def __call__(self, request: "DriverRequest") -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class DriverRequest:
    run_id: str
    cell: Cell
    phase_kind: str
    role: str | None


@dataclass(frozen=True)
class DriverOutcome:
    status: str
    actions: int
    root_cell_id: str


def _exact(result: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(result, dict) or set(result) != fields:
        raise SchemaError(f"{label} result fields are invalid")
    return result


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise SchemaError(f"{label} must be explicit true")


def _strings(value: Any, label: str, *, nonempty: bool = True) -> list[str]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise SchemaError(f"{label} must be a valid string list")
    return list(value)


class LoopDriver:
    def __init__(
        self,
        system: LoopstrapSystem,
        result_provider: RoleResultProvider,
    ) -> None:
        self.system = system
        self.result_provider = result_provider

    def _root(self) -> Cell:
        roots = [cell for cell in self.system.graph.cells.values() if cell.parent_id is None]
        if len(roots) != 1:
            raise SchemaError("driver requires exactly one root Cell")
        return roots[0]

    def _next(self) -> tuple[str, Cell] | None:
        cells = sorted(
            self.system.graph.cells.values(),
            key=lambda cell: (-cell.depth, cell.cell_id),
        )
        for cell in cells:
            kind = self.system.graph.phase_kind(cell.cell_id)
            if kind == "closed":
                continue
            if kind == "children":
                if not cell.children:
                    raise SchemaError(
                        f"composite Cell has no decomposed children: {cell.cell_id}"
                    )
                if all(
                    self.system.graph.phase_kind(child_id) == "closed"
                    for child_id in cell.children
                ):
                    return ("begin_integration", cell)
                continue
            return ("role_result", cell)
        return None

    def _children(self, value: Any) -> list[ChildSpec]:
        if not isinstance(value, list) or not value:
            raise SchemaError("composite pre-review must provide child Cells")
        rows: list[ChildSpec] = []
        for raw in value:
            fields = {"cell_id", "obligations", "owner", "scope", "contract_ref"}
            item = _exact(raw, fields, "child Cell")
            obligations = tuple(_strings(item["obligations"], "child obligations"))
            scope = tuple(_strings(item["scope"], "child scope"))
            owner = item["owner"]
            cell_id = item["cell_id"]
            contract_ref = item["contract_ref"]
            if (
                not isinstance(owner, str)
                or not owner
                or not isinstance(cell_id, str)
                or not cell_id
                or not isinstance(contract_ref, str)
                or not contract_ref
            ):
                raise SchemaError("child Cell identity, owner, and contract are required")
            rows.append(
                ChildSpec(
                    cell_id=cell_id,
                    obligations=obligations,
                    owner=owner,
                    scope=scope,
                    contract_ref=contract_ref,
                )
            )
        return rows

    def _apply(self, cell: Cell, kind: str, raw: Any) -> None:
        if kind == "contract":
            result = _exact(raw, {"accepted"}, "contract")
            _true(result["accepted"], "contract acceptance")
            self.system.accept_contract(cell.cell_id)
            return
        if kind == "tests":
            result = _exact(
                raw,
                {
                    "visible_digest",
                    "holdout_digest",
                    "obligation_map",
                    "executable",
                },
                "tests",
            )
            _true(result["executable"], "test executability")
            if not isinstance(result["obligation_map"], dict):
                raise SchemaError("test obligation map must be an object")
            obligation_map = {
                str(key): _strings(value, f"tests for {key}")
                for key, value in result["obligation_map"].items()
            }
            self.system.freeze_tests(
                cell.cell_id,
                visible_digest=str(result["visible_digest"]),
                holdout_digest=str(result["holdout_digest"]),
                obligation_map=obligation_map,
                executable=True,
            )
            return
        if kind == "plan":
            result = _exact(raw, {"plan_digest", "responsibilities"}, "plan")
            if not isinstance(result["responsibilities"], dict):
                raise SchemaError("plan responsibilities must be an object")
            self.system.record_plan(
                cell.cell_id,
                plan_digest=str(result["plan_digest"]),
                responsibilities={
                    str(key): str(value)
                    for key, value in result["responsibilities"].items()
                },
            )
            return
        if kind == "pre_review":
            if not isinstance(raw, dict) or "leaf" not in raw:
                raise SchemaError("pre-review result is invalid")
            leaf = raw["leaf"]
            if not isinstance(leaf, bool):
                raise SchemaError("pre-review leaf decision must be boolean")
            expected = (
                {"accepted", "leaf", "unresolved_seams"}
                if leaf
                else {"accepted", "leaf", "unresolved_seams", "children"}
            )
            result = _exact(raw, expected, "pre-review")
            _true(result["accepted"], "pre-review acceptance")
            seams = _strings(
                result["unresolved_seams"],
                "unresolved seams",
                nonempty=False,
            )
            children = [] if leaf else self._children(result["children"])

            trial = deepcopy(self.system.graph)
            trial.record_pre_review(
                cell.cell_id,
                accepted=True,
                leaf=leaf,
                unresolved_seams=seams,
            )
            if not leaf:
                trial.decompose(cell.cell_id, children)

            self.system.record_pre_review(
                cell.cell_id,
                accepted=True,
                leaf=leaf,
                unresolved_seams=seams,
            )
            if not leaf:
                self.system.decompose(cell.cell_id, children)
            return
        if kind == "implementation":
            result = _exact(raw, {"passed", "evidence_refs"}, "implementation")
            _true(result["passed"], "implementation verification")
            self.system._record_orchestrated_verification(
                cell.cell_id,
                passed=True,
                evidence_refs=_strings(
                    result["evidence_refs"], "implementation evidence"
                ),
            )
            return
        if kind == "integration":
            result = _exact(raw, {"passed", "evidence_refs"}, "integration")
            _true(result["passed"], "integration verification")
            self.system.record_integration(
                cell.cell_id,
                passed=True,
                evidence_refs=_strings(
                    result["evidence_refs"], "integration evidence"
                ),
            )
            return
        if kind == "post_review":
            result = _exact(raw, {"accepted", "evidence_refs"}, "post-review")
            _true(result["accepted"], "post-review acceptance")
            self.system.record_post_review(
                cell.cell_id,
                accepted=True,
                evidence_refs=_strings(
                    result["evidence_refs"], "post-review evidence"
                ),
            )
            self.system.close(cell.cell_id)
            return
        raise SchemaError(f"driver cannot apply phase kind: {kind}")

    def run(self) -> DriverOutcome:
        root = self._root()
        actions = 0
        while True:
            if self.system.run_status != "active":
                return DriverOutcome(self.system.run_status, actions, root.cell_id)
            if self.system.graph.phase_kind(root.cell_id) == "closed":
                return DriverOutcome("complete", actions, root.cell_id)
            try:
                next_action = self._next()
                if next_action is None:
                    raise SchemaError("Cell graph has no runnable work and root is not closed")
                action, cell = next_action
                if action == "begin_integration":
                    self.system.begin_integration(cell.cell_id)
                else:
                    kind = self.system.graph.phase_kind(cell.cell_id)
                    request = DriverRequest(
                        run_id=self.system.run_id,
                        cell=deepcopy(cell),
                        phase_kind=kind,
                        role=self.system.graph.required_role(cell.cell_id),
                    )
                    result = self.result_provider(request)
                    self._apply(cell, kind, result)
                actions += 1
            except (LoopstrapError, TypeError, ValueError, KeyError) as exc:
                self.system.park(reason=f"driver refusal: {type(exc).__name__}: {exc}")
                return DriverOutcome("parked", actions, root.cell_id)


class HarnessRoleExecutor:
    def __init__(
        self,
        system: LoopstrapSystem,
        authorization_factory: Callable[[DriverRequest], Any],
        invocation_factory: Callable[[DriverRequest], dict[str, Any]],
        result_decoder: Callable[[DriverRequest, SystemJob], dict[str, Any]],
    ) -> None:
        self.system = system
        self.authorization_factory = authorization_factory
        self.invocation_factory = invocation_factory
        self.result_decoder = result_decoder

    def __call__(self, request: DriverRequest) -> dict[str, Any]:
        if request.role is None:
            raise SchemaError(
                f"phase has no configured dispatch role: {request.phase_kind}"
            )
        invocation = self.invocation_factory(request)
        expected = {
            "prompt_ref",
            "context_manifest_ref",
            "context_lineage",
            "cache_lineage",
        }
        if not isinstance(invocation, dict) or set(invocation) != expected:
            raise SchemaError("driver invocation fields are invalid")
        job = self.system.dispatch(
            self.authorization_factory(request),
            **invocation,
        )
        return self.result_decoder(request, job)
