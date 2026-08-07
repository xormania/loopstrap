from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .errors import ClosureError, DecompositionError, SchemaError, TransitionError


@dataclass(frozen=True)
class PhaseDefinition:
    name: str
    kind: str
    role: str | None
    outcomes: dict[str, str]


@dataclass(frozen=True)
class WorkflowDefinition:
    version: int
    initial: str
    phases: dict[str, PhaseDefinition]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowDefinition":
        if set(data) != {"version", "initial", "phases"}:
            raise SchemaError("workflow definition requires exactly version, initial, and phases")
        if not isinstance(data["version"], int) or data["version"] < 1:
            raise SchemaError("workflow version must be a positive integer")
        raw_phases = data["phases"]
        if not isinstance(raw_phases, dict) or not raw_phases:
            raise SchemaError("workflow phases must be a nonempty mapping")
        phases: dict[str, PhaseDefinition] = {}
        for name, raw in raw_phases.items():
            if not isinstance(raw, dict) or set(raw) != {"kind", "role", "on"}:
                raise SchemaError(f"workflow phase {name} has invalid fields")
            outcomes = raw["on"]
            if not isinstance(outcomes, dict):
                raise SchemaError(f"workflow phase {name} outcomes must be a mapping")
            phases[str(name)] = PhaseDefinition(
                name=str(name),
                kind=str(raw["kind"]),
                role=None if raw["role"] is None else str(raw["role"]),
                outcomes={str(outcome): str(target) for outcome, target in outcomes.items()},
            )
        initial = str(data["initial"])
        if initial not in phases:
            raise SchemaError("workflow initial phase does not exist")
        for phase in phases.values():
            unknown = set(phase.outcomes.values()) - set(phases)
            if unknown:
                raise SchemaError(f"workflow phase {phase.name} targets unknown phases: {sorted(unknown)}")
        required_kinds = {
            "contract",
            "tests",
            "plan",
            "pre_review",
            "children",
            "implementation",
            "integration",
            "post_review",
            "closed",
        }
        found_kinds = {phase.kind for phase in phases.values()}
        missing = required_kinds - found_kinds
        if missing:
            raise SchemaError(f"workflow lacks lifecycle phase kinds: {sorted(missing)}")
        return cls(version=data["version"], initial=initial, phases=phases)

    def phase_for_kind(self, kind: str) -> str:
        matches = [phase.name for phase in self.phases.values() if phase.kind == kind]
        if len(matches) != 1:
            raise SchemaError(f"workflow must have exactly one phase of kind {kind}")
        return matches[0]


@dataclass(frozen=True)
class ChildSpec:
    cell_id: str
    obligations: tuple[str, ...]
    owner: str
    scope: tuple[str, ...]
    contract_ref: str | None = None


@dataclass
class Claim:
    claim_id: str
    proposition: str
    status: str
    evidence_refs: list[str]
    resolution_ref: str | None = None
    verification_ref: str | None = None

    @property
    def blocking(self) -> bool:
        return self.status == "verified"


@dataclass
class Cell:
    cell_id: str
    parent_id: str | None
    contract_ref: str
    obligations: tuple[str, ...]
    scope: tuple[str, ...]
    depth: int
    phase: str
    specification_digest: str | None = None
    cell_contract_ref: str | None = None
    composite_contract_ref: str | None = None
    owner: str | None = None
    revision: int = 1
    visible_tests_digest: str | None = None
    holdout_tests_digest: str | None = None
    obligation_map: dict[str, list[str]] = field(default_factory=dict)
    tests_executable: bool = False
    plan_digest: str | None = None
    responsibilities: dict[str, str] = field(default_factory=dict)
    pre_review_accepted: bool = False
    leaf: bool | None = None
    unresolved_seams: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    verification_passed: bool = False
    integration_passed: bool = False
    post_review_accepted: bool = False
    claims: dict[str, Claim] = field(default_factory=dict)
    approvals: list[str] = field(default_factory=list)


class RunGraph:
    def __init__(self, run_id: str, definition: WorkflowDefinition) -> None:
        self.run_id = run_id
        self.definition = definition
        self.cells: dict[str, Cell] = {}
        self.events: list[dict[str, Any]] = []

    def _event(self, event_type: str, cell: Cell, **payload: Any) -> None:
        self.events.append(
            {
                "type": event_type,
                "cell_id": cell.cell_id,
                "revision": cell.revision,
                **payload,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        cells: dict[str, dict[str, Any]] = {}
        for cell_id, cell in sorted(self.cells.items()):
            cells[cell_id] = {
                "cell_id": cell.cell_id,
                "parent_id": cell.parent_id,
                "contract_ref": cell.contract_ref,
                "obligations": list(cell.obligations),
                "scope": list(cell.scope),
                "depth": cell.depth,
                "phase": cell.phase,
                "specification_digest": cell.specification_digest,
                "cell_contract_ref": cell.cell_contract_ref,
                "composite_contract_ref": cell.composite_contract_ref,
                "owner": cell.owner,
                "revision": cell.revision,
                "visible_tests_digest": cell.visible_tests_digest,
                "holdout_tests_digest": cell.holdout_tests_digest,
                "obligation_map": deepcopy(cell.obligation_map),
                "tests_executable": cell.tests_executable,
                "plan_digest": cell.plan_digest,
                "responsibilities": dict(cell.responsibilities),
                "pre_review_accepted": cell.pre_review_accepted,
                "leaf": cell.leaf,
                "unresolved_seams": list(cell.unresolved_seams),
                "children": list(cell.children),
                "verification_passed": cell.verification_passed,
                "integration_passed": cell.integration_passed,
                "post_review_accepted": cell.post_review_accepted,
                "claims": {
                    claim_id: {
                        "claim_id": claim.claim_id,
                        "proposition": claim.proposition,
                        "status": claim.status,
                        "evidence_refs": list(claim.evidence_refs),
                        "resolution_ref": claim.resolution_ref,
                        "verification_ref": claim.verification_ref,
                    }
                    for claim_id, claim in sorted(cell.claims.items())
                },
                "approvals": list(cell.approvals),
            }
        return {
            "run_id": self.run_id,
            "definition_version": self.definition.version,
            "cells": cells,
            "events": deepcopy(self.events),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        definition: WorkflowDefinition,
        expected_run_id: str,
    ) -> "RunGraph":
        required = {"run_id", "definition_version", "cells", "events"}
        if not isinstance(data, dict) or set(data) != required:
            raise SchemaError("run graph checkpoint fields are invalid")
        if (
            data["run_id"] != expected_run_id
            or data["definition_version"] != definition.version
        ):
            raise SchemaError("run graph checkpoint binding differs")
        raw_cells = data["cells"]
        if not isinstance(raw_cells, dict) or not isinstance(data["events"], list):
            raise SchemaError("run graph checkpoint containers are invalid")
        graph = cls(expected_run_id, definition)
        for cell_id, raw in raw_cells.items():
            if not isinstance(raw, dict) or raw.get("cell_id") != cell_id:
                raise SchemaError("run graph checkpoint Cell identity is invalid")
            raw_claims = raw.get("claims")
            if not isinstance(raw_claims, dict):
                raise SchemaError("run graph checkpoint claims are invalid")
            claims: dict[str, Claim] = {}
            for claim_id, claim in raw_claims.items():
                if not isinstance(claim, dict) or claim.get("claim_id") != claim_id:
                    raise SchemaError("run graph checkpoint claim identity is invalid")
                claims[claim_id] = Claim(
                    claim_id=claim_id,
                    proposition=str(claim["proposition"]),
                    status=str(claim["status"]),
                    evidence_refs=list(claim["evidence_refs"]),
                    resolution_ref=claim["resolution_ref"],
                    verification_ref=claim["verification_ref"],
                )
            try:
                cell = Cell(
                    cell_id=cell_id,
                    parent_id=raw["parent_id"],
                    contract_ref=raw["contract_ref"],
                    obligations=tuple(raw["obligations"]),
                    scope=tuple(raw["scope"]),
                    depth=raw["depth"],
                    phase=raw["phase"],
                    specification_digest=raw["specification_digest"],
                    cell_contract_ref=raw["cell_contract_ref"],
                    composite_contract_ref=raw["composite_contract_ref"],
                    owner=raw["owner"],
                    revision=raw["revision"],
                    visible_tests_digest=raw["visible_tests_digest"],
                    holdout_tests_digest=raw["holdout_tests_digest"],
                    obligation_map=deepcopy(raw["obligation_map"]),
                    tests_executable=raw["tests_executable"],
                    plan_digest=raw["plan_digest"],
                    responsibilities=dict(raw["responsibilities"]),
                    pre_review_accepted=raw["pre_review_accepted"],
                    leaf=raw["leaf"],
                    unresolved_seams=list(raw["unresolved_seams"]),
                    children=list(raw["children"]),
                    verification_passed=raw["verification_passed"],
                    integration_passed=raw["integration_passed"],
                    post_review_accepted=raw["post_review_accepted"],
                    claims=claims,
                    approvals=list(raw["approvals"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise SchemaError("run graph checkpoint Cell is invalid") from exc
            if cell.phase not in definition.phases:
                raise SchemaError("run graph checkpoint phase is unknown")
            graph.cells[cell_id] = cell
        for cell in graph.cells.values():
            if cell.parent_id is not None and cell.parent_id not in graph.cells:
                raise SchemaError("run graph checkpoint parent is unknown")
            if any(child_id not in graph.cells for child_id in cell.children):
                raise SchemaError("run graph checkpoint child is unknown")
        graph.events = deepcopy(data["events"])
        return graph

    def _kind(self, cell: Cell) -> str:
        return self.definition.phases[cell.phase].kind

    def _require_kind(self, cell: Cell, expected: str) -> None:
        actual = self._kind(cell)
        if actual != expected:
            raise TransitionError(
                f"cell {cell.cell_id} is in phase kind {actual}, expected {expected}"
            )

    def _transition(self, cell: Cell, outcome: str) -> None:
        phase = self.definition.phases[cell.phase]
        target = phase.outcomes.get(outcome)
        if target is None:
            raise TransitionError(
                f"phase {phase.name} does not accept outcome {outcome}"
            )
        previous = cell.phase
        cell.phase = target
        cell.revision += 1
        self._event("cell.transitioned", cell, previous=previous, current=target, outcome=outcome)

    def create_root(
        self,
        cell_id: str,
        *,
        contract_ref: str,
        obligations: list[str],
        scope: tuple[str, ...] | None = None,
        specification_digest: str | None = None,
        composite_contract_ref: str | None = None,
    ) -> Cell:
        if self.cells:
            raise TransitionError("run graph already has a root")
        if not obligations or len(set(obligations)) != len(obligations):
            raise SchemaError("root obligations must be nonempty and unique")
        cell = Cell(
            cell_id=cell_id,
            parent_id=None,
            contract_ref=contract_ref,
            obligations=tuple(obligations),
            scope=scope or (cell_id,),
            depth=0,
            phase=self.definition.initial,
            specification_digest=specification_digest,
            composite_contract_ref=composite_contract_ref,
        )
        self.cells[cell_id] = cell
        self._event("cell.created", cell, parent_id=None)
        return cell

    def cell(self, cell_id: str) -> Cell:
        try:
            return self.cells[cell_id]
        except KeyError as exc:
            raise SchemaError(f"unknown cell: {cell_id}") from exc

    def phase_kind(self, cell_id: str) -> str:
        return self._kind(self.cell(cell_id))

    def required_role(self, cell_id: str) -> str | None:
        return self.definition.phases[self.cell(cell_id).phase].role

    def accept_contract(self, cell_id: str) -> None:
        cell = self.cell(cell_id)
        self._require_kind(cell, "contract")
        self._transition(cell, "accepted")

    @staticmethod
    def _validate_test_basis(
        cell: Cell,
        visible_digest: str,
        holdout_digest: str,
        obligation_map: dict[str, list[str]],
    ) -> None:
        if not visible_digest or not holdout_digest:
            raise TransitionError("visible and holdout test digests are required")
        if set(obligation_map) != set(cell.obligations):
            raise TransitionError("frozen tests must map every and only cell obligation")
        if any(not tests or any(not test for test in tests) for tests in obligation_map.values()):
            raise TransitionError("every obligation must map to at least one named test")

    def freeze_tests(
        self,
        cell_id: str,
        *,
        visible_digest: str,
        holdout_digest: str,
        obligation_map: dict[str, list[str]],
        executable: bool,
    ) -> None:
        cell = self.cell(cell_id)
        self._require_kind(cell, "tests")
        self._validate_test_basis(cell, visible_digest, holdout_digest, obligation_map)
        cell.visible_tests_digest = visible_digest
        cell.holdout_tests_digest = holdout_digest
        cell.obligation_map = {key: list(value) for key, value in obligation_map.items()}
        cell.tests_executable = bool(executable)
        self._event(
            "tests.frozen",
            cell,
            visible_digest=visible_digest,
            holdout_digest=holdout_digest,
        )
        self._transition(cell, "frozen")

    def revise_tests(
        self,
        cell_id: str,
        *,
        visible_digest: str,
        holdout_digest: str,
        obligation_map: dict[str, list[str]],
        executable: bool,
        reason: str,
    ) -> None:
        cell = self.cell(cell_id)
        if not cell.visible_tests_digest:
            raise TransitionError("tests cannot be revised before their first freeze")
        self._validate_test_basis(cell, visible_digest, holdout_digest, obligation_map)
        if (
            visible_digest == cell.visible_tests_digest
            and holdout_digest == cell.holdout_tests_digest
            and obligation_map == cell.obligation_map
        ):
            raise TransitionError("test revision did not change the test basis")
        cell.visible_tests_digest = visible_digest
        cell.holdout_tests_digest = holdout_digest
        cell.obligation_map = {key: list(value) for key, value in obligation_map.items()}
        cell.tests_executable = bool(executable)
        cell.plan_digest = None
        cell.responsibilities = {}
        cell.pre_review_accepted = False
        cell.leaf = None
        cell.unresolved_seams = []
        cell.children = []
        cell.verification_passed = False
        cell.integration_passed = False
        cell.post_review_accepted = False
        cell.phase = self.definition.phase_for_kind("plan")
        cell.revision += 1
        self._event("tests.revised", cell, reason=reason)

    def record_plan(
        self,
        cell_id: str,
        *,
        plan_digest: str,
        responsibilities: dict[str, str],
    ) -> None:
        cell = self.cell(cell_id)
        self._require_kind(cell, "plan")
        if not cell.visible_tests_digest or set(cell.obligation_map) != set(cell.obligations):
            raise TransitionError("planning requires a complete frozen test basis")
        if set(responsibilities) != set(cell.obligations) or any(
            not owner for owner in responsibilities.values()
        ):
            raise TransitionError("plan must assign a responsibility for every obligation")
        cell.plan_digest = plan_digest
        cell.responsibilities = dict(responsibilities)
        self._event("plan.recorded", cell, plan_digest=plan_digest)
        self._transition(cell, "planned")

    def record_pre_review(
        self,
        cell_id: str,
        *,
        accepted: bool,
        leaf: bool,
        unresolved_seams: list[str],
    ) -> None:
        cell = self.cell(cell_id)
        self._require_kind(cell, "pre_review")
        if not accepted:
            raise TransitionError("rejected decomposition review cannot advance")
        if leaf and unresolved_seams:
            raise TransitionError("cell with unresolved seams cannot be accepted as a leaf")
        cell.pre_review_accepted = True
        cell.leaf = bool(leaf)
        cell.unresolved_seams = list(unresolved_seams)
        self._event(
            "pre_review.recorded",
            cell,
            accepted=True,
            leaf=leaf,
            unresolved_seams=list(unresolved_seams),
        )
        self._transition(cell, "leaf" if leaf else "composite")

    def decompose(self, cell_id: str, children: list[ChildSpec]) -> None:
        cell = self.cell(cell_id)
        self._require_kind(cell, "children")
        if not cell.pre_review_accepted or cell.leaf is not False:
            raise TransitionError("decomposition requires accepted composite pre-review")
        if not children:
            raise DecompositionError("decomposition must create at least one child")
        child_ids = [child.cell_id for child in children]
        if len(set(child_ids)) != len(child_ids) or any(child_id in self.cells for child_id in child_ids):
            raise DecompositionError("child ids must be new and unique")
        covered: set[str] = set()
        assigned: set[str] = set()
        parent_obligations = set(cell.obligations)
        for child in children:
            child_obligations = set(child.obligations)
            if not child.owner:
                raise DecompositionError(f"child {child.cell_id} has no owner")
            if not child_obligations or not child_obligations.issubset(parent_obligations):
                raise DecompositionError(f"child {child.cell_id} has invalid obligations")
            if child.scope[: len(cell.scope)] != cell.scope or len(child.scope) <= len(cell.scope):
                raise DecompositionError(f"child {child.cell_id} does not narrow parent scope")
            overlap = assigned & child_obligations
            if overlap:
                raise DecompositionError(
                    f"child {child.cell_id} overlaps obligation ownership: {sorted(overlap)}"
                )
            assigned.update(child_obligations)
            covered.update(child_obligations)
        if covered != parent_obligations:
            raise DecompositionError("child obligation union must cover the parent exactly")
        for child in children:
            created = Cell(
                cell_id=child.cell_id,
                parent_id=cell.cell_id,
                contract_ref=child.contract_ref or cell.contract_ref,
                obligations=tuple(child.obligations),
                scope=tuple(child.scope),
                depth=cell.depth + 1,
                phase=self.definition.initial,
                owner=child.owner,
                specification_digest=cell.specification_digest,
                cell_contract_ref=child.contract_ref,
            )
            self.cells[child.cell_id] = created
            self._event("cell.created", created, parent_id=cell.cell_id)
        cell.children = child_ids
        cell.revision += 1
        self._event("cell.decomposed", cell, children=child_ids)

    def leaf_readiness(self, cell_id: str) -> list[str]:
        cell = self.cell(cell_id)
        missing: list[str] = []
        if not cell.visible_tests_digest or not cell.holdout_tests_digest:
            missing.append("tests_frozen")
        if set(cell.obligation_map) != set(cell.obligations) or any(
            not tests for tests in cell.obligation_map.values()
        ):
            missing.append("obligations_tested")
        if set(cell.responsibilities) != set(cell.obligations):
            missing.append("responsibilities_mapped")
        if not cell.owner and not any(cell.responsibilities.values()):
            missing.append("owner_assigned")
        if not cell.tests_executable:
            missing.append("tests_executable")
        if cell.unresolved_seams or cell.leaf is not True:
            missing.append("seams_resolved")
        if not cell.pre_review_accepted:
            missing.append("pre_review_accepted")
        return missing

    def record_verification(
        self,
        cell_id: str,
        *,
        passed: bool,
        evidence_refs: list[str],
    ) -> None:
        cell = self.cell(cell_id)
        self._require_kind(cell, "implementation")
        missing = self.leaf_readiness(cell_id)
        if missing:
            raise TransitionError(f"leaf is not ready: {missing}")
        if not passed or not evidence_refs:
            raise TransitionError("verification must be green and evidence-backed to advance")
        cell.verification_passed = True
        self._event("verification.recorded", cell, passed=True, evidence_refs=list(evidence_refs))
        self._transition(cell, "verified")

    def begin_integration(self, cell_id: str) -> None:
        cell = self.cell(cell_id)
        self._require_kind(cell, "children")
        if not cell.children or any(self._kind(self.cell(child)) != "closed" for child in cell.children):
            raise ClosureError("all children must close before parent integration")
        self._transition(cell, "integrated")
        self._require_kind(cell, "integration")

    def record_integration(
        self,
        cell_id: str,
        *,
        passed: bool,
        evidence_refs: list[str],
    ) -> None:
        cell = self.cell(cell_id)
        if self._kind(cell) == "children":
            self.begin_integration(cell_id)
        self._require_kind(cell, "integration")
        if not passed or not evidence_refs:
            raise ClosureError("integration must be green and evidence-backed")
        cell.integration_passed = True
        self._event("verification.recorded", cell, passed=True, evidence_refs=list(evidence_refs))
        self._transition(cell, "verified")

    def record_post_review(
        self,
        cell_id: str,
        *,
        accepted: bool,
        evidence_refs: list[str],
    ) -> None:
        cell = self.cell(cell_id)
        self._require_kind(cell, "post_review")
        if not accepted or not evidence_refs:
            raise TransitionError("post-result review must be accepted and evidence-backed")
        cell.post_review_accepted = True
        self._event("post_review.recorded", cell, accepted=True, evidence_refs=list(evidence_refs))

    def add_claim(
        self,
        cell_id: str,
        *,
        claim_id: str,
        proposition: str,
        status: str,
        evidence_refs: list[str],
    ) -> None:
        cell = self.cell(cell_id)
        if claim_id in cell.claims:
            raise SchemaError(f"duplicate claim id in cell: {claim_id}")
        if status not in {"suspected", "verified"}:
            raise SchemaError(f"unsupported claim status: {status}")
        if status == "verified" and not evidence_refs:
            raise SchemaError("verified claim requires evidence")
        cell.claims[claim_id] = Claim(
            claim_id=claim_id,
            proposition=proposition,
            status=status,
            evidence_refs=list(evidence_refs),
        )
        cell.revision += 1
        self._event("claim.recorded", cell, claim_id=claim_id, status=status)

    def resolve_claim(
        self,
        cell_id: str,
        claim_id: str,
        *,
        resolution_ref: str,
        verification_ref: str,
    ) -> None:
        cell = self.cell(cell_id)
        try:
            claim = cell.claims[claim_id]
        except KeyError as exc:
            raise SchemaError(f"unknown claim: {claim_id}") from exc
        if claim.status != "verified" or not resolution_ref or not verification_ref:
            raise ClosureError("only an evidence-backed resolution can close a verified claim")
        claim.status = "resolved"
        claim.resolution_ref = resolution_ref
        claim.verification_ref = verification_ref
        cell.revision += 1
        self._event("claim.resolved", cell, claim_id=claim_id)

    def add_approval(self, cell_id: str, *, reviewer_id: str) -> None:
        cell = self.cell(cell_id)
        cell.approvals.append(reviewer_id)
        self._event("approval.recorded", cell, reviewer_id=reviewer_id)

    def close(self, cell_id: str) -> None:
        cell = self.cell(cell_id)
        if self._kind(cell) != "post_review":
            raise ClosureError(
                f"cell {cell.cell_id} cannot close from phase kind {self._kind(cell)}"
            )
        blocking = sorted(claim.claim_id for claim in cell.claims.values() if claim.blocking)
        if blocking:
            raise ClosureError(f"verified claims block closure: {blocking}")
        if not cell.post_review_accepted:
            raise ClosureError("post-result adversarial review has not accepted the cell")
        if cell.children:
            if any(self._kind(self.cell(child)) != "closed" for child in cell.children):
                raise ClosureError("all children must be closed")
            if not cell.integration_passed:
                raise ClosureError("parent integration evidence is not green")
        elif not cell.verification_passed:
            raise ClosureError("leaf verification evidence is not green")
        self._transition(cell, "accepted")
        self._event("cell.closed", cell)

    def reopen(self, cell_id: str, *, reason: str) -> None:
        cell = self.cell(cell_id)
        if self._kind(cell) != "closed":
            raise TransitionError("only a closed cell may be reopened explicitly")
        cell.phase = self.definition.phase_for_kind("post_review")
        cell.revision += 1
        self._event("cell.reopened", cell, reason=reason)

    def _ancestors(self, cell_id: str) -> list[str]:
        result: list[str] = []
        current: str | None = cell_id
        while current is not None:
            result.append(current)
            current = self.cell(current).parent_id
        return result

    def lowest_common_ancestor(self, cell_ids: list[str]) -> str:
        if not cell_ids:
            raise SchemaError("cannot route an issue without affected cells")
        ancestor_lists = [self._ancestors(cell_id) for cell_id in cell_ids]
        common = set(ancestor_lists[0]).intersection(*map(set, ancestor_lists[1:]))
        if not common:
            raise SchemaError("affected cells have no common ancestor")
        return max(common, key=lambda item: self.cell(item).depth)

    def route_verified_issue(
        self,
        *,
        affected_cells: list[str],
        claim_id: str,
        proposition: str,
        evidence_refs: list[str],
    ) -> str:
        target_id = self.lowest_common_ancestor(affected_cells)
        target = self.cell(target_id)
        self.add_claim(
            target_id,
            claim_id=claim_id,
            proposition=proposition,
            status="verified",
            evidence_refs=evidence_refs,
        )
        target.phase = self.definition.phase_for_kind("pre_review")
        target.pre_review_accepted = False
        target.leaf = None
        target.unresolved_seams = [claim_id]
        target.verification_passed = False
        target.integration_passed = False
        target.post_review_accepted = False
        target.revision += 1
        self._event("cell.reopened_for_issue", target, claim_id=claim_id)
        return target_id
