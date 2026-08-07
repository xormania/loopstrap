from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any
import uuid

from .artifacts import ArtifactStore
from .atomic import canonical_json
from .authority import Authorization, AuthorizationValidator, ControlView
from .errors import (
    AuthorityError,
    HarnessProtocolError,
    IntegrityError,
    IdempotencyError,
    PromotionError,
    SchemaError,
    StaleResultError,
    TransitionError,
)
from .executor import Executor
from .evidence import (
    AcceptanceEngine,
    AcceptanceObligation,
    AcceptanceRecord,
    EvidenceRecord,
    RawExecutionCustodian,
)
from .bounded import sanitized_environment
from .harness import (
    Assignment,
    HarnessDispatcher,
    Invocation,
    InvocationResult,
    RoleRouter,
    RoleTreatmentRegistry,
)
from .ledger import EventLedger
from .recovery import DispatchJournal, JobReservation
from .state import StateReducer
from .verification import DeterministicVerifier, VerificationPlan
from .workflow import ChildSpec, RunGraph, WorkflowDefinition
from .workspace import SnapshotStore, Workspace, WorkspaceManager
from .specification import SpecificationSnapshot
from .contracts import ContractGraph
from .certification import CertificationAuthority, UsageChargeLedger
from .telemetry import TelemetryStore


@dataclass
class SystemJob:
    job_id: str
    cell_id: str
    reservation: JobReservation
    workspace: Workspace
    base_snapshot: str
    result: InvocationResult
    response_ref: str
    candidate_snapshot: str | None = None
    verified: bool = False
    promoted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "cell_id": self.cell_id,
            "reservation": {
                "job_id": self.reservation.job_id,
                "dispatch_key": self.reservation.dispatch_key,
                "cell_id": self.reservation.cell_id,
                "cell_revision": self.reservation.cell_revision,
                "role": self.reservation.role,
                "role_treatment_id": self.reservation.role_treatment_id,
            },
            "workspace": {
                "job_id": self.workspace.job_id,
                "base_snapshot": self.workspace.base_snapshot,
            },
            "base_snapshot": self.base_snapshot,
            "result": self.result.evidence(),
            "response_ref": self.response_ref,
            "candidate_snapshot": self.candidate_snapshot,
            "verified": self.verified,
            "promoted": self.promoted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, workspaces_root: Path) -> "SystemJob":
        required = {
            "job_id",
            "cell_id",
            "reservation",
            "workspace",
            "base_snapshot",
            "result",
            "response_ref",
            "candidate_snapshot",
            "verified",
            "promoted",
        }
        if not isinstance(data, dict) or set(data) != required:
            raise SchemaError("job checkpoint fields are invalid")
        reservation = JobReservation(**data["reservation"])
        workspace_data = data["workspace"]
        result_data = data["result"]
        if (
            not isinstance(workspace_data, dict)
            or set(workspace_data) != {"job_id", "base_snapshot"}
            or not isinstance(result_data, dict)
        ):
            raise SchemaError("job checkpoint payload is invalid")
        result = InvocationResult(
            invocation_id=result_data["invocation_id"],
            cell_revision=result_data["cell_revision"],
            status=result_data["status"],
            requested_role_treatment=dict(
                result_data["requested_role_treatment"]
            ),
            launch_attestation=dict(result_data["launch_attestation"]),
            artifacts=tuple(result_data["artifacts"]),
            claims=tuple(result_data["claims"]),
            usage=dict(result_data["usage"]),
            cache_lineage=result_data["cache_lineage"],
            prompt_ref=result_data["prompt_ref"],
            context_manifest_ref=result_data["context_manifest_ref"],
            context_lineage=result_data["context_lineage"],
            latency_ms=result_data["latency_ms"],
            execution_ref=result_data["execution_ref"],
            raw_redaction_count=result_data["raw_redaction_count"],
            process_trace=dict(result_data["process_trace"]),
        )
        workspace = Workspace(
            job_id=workspace_data["job_id"],
            path=Path(workspaces_root) / workspace_data["job_id"],
            base_snapshot=workspace_data["base_snapshot"],
        )
        if not workspace.path.is_dir() or workspace.path.is_symlink():
            raise IntegrityError(f"recovered job workspace is unavailable: {workspace.job_id}")
        job = cls(
            job_id=data["job_id"],
            cell_id=data["cell_id"],
            reservation=reservation,
            workspace=workspace,
            base_snapshot=data["base_snapshot"],
            result=result,
            response_ref=data["response_ref"],
            candidate_snapshot=data["candidate_snapshot"],
            verified=data["verified"],
            promoted=data["promoted"],
        )
        if (
            job.job_id != reservation.job_id
            or job.cell_id != reservation.cell_id
            or workspace.job_id != job.job_id
            or workspace.base_snapshot != job.base_snapshot
        ):
            raise IntegrityError("recovered job bindings differ")
        return job


class LoopstrapSystem:
    def __init__(
        self,
        *,
        root_dir: Path,
        run_id: str,
        graph: RunGraph,
        registry: RoleTreatmentRegistry,
        router: RoleRouter,
        ledger: EventLedger,
        artifacts: ArtifactStore,
        snapshots: SnapshotStore,
        workspaces: WorkspaceManager,
        specification: SpecificationSnapshot | None = None,
        contract_graph: ContractGraph | None = None,
        certification_authority: CertificationAuthority | None = None,
    ) -> None:
        self.root_dir = root_dir
        self.run_id = run_id
        self.graph = graph
        self.registry = registry
        self.router = router
        self.ledger = ledger
        self.artifacts = artifacts
        self.snapshots = snapshots
        self.workspaces = workspaces
        self.specification = specification
        self.contract_graph = contract_graph
        self.run_status = "active"
        self.executor = Executor("loopstrap-executor")
        self.dispatcher = HarnessDispatcher(
            allow_live=False,
            execution_custodian=RawExecutionCustodian(artifacts),
        )
        self.verifier = DeterministicVerifier()
        self.journal = DispatchJournal(ledger)
        self.assignments: list[Assignment] = []
        self.jobs: dict[str, SystemJob] = {}
        self.interventions: list[dict[str, str]] = []
        self.evidence_records: dict[str, EvidenceRecord] = {}
        self.acceptance_records: dict[str, AcceptanceRecord] = {}
        self.usage_ledger = UsageChargeLedger()
        self.telemetry = TelemetryStore(self.root_dir / "telemetry.sqlite3")

    @classmethod
    def create(
        cls,
        *,
        root_dir: Path,
        workflow: dict[str, Any],
        role_treatments: dict[str, Any],
        role_policy: dict[str, Any],
        source_dir: Path,
        specification: SpecificationSnapshot | None = None,
        contract_graph: ContractGraph | None = None,
        certification_authority: CertificationAuthority | None = None,
    ) -> "LoopstrapSystem":
        root_dir = Path(root_dir)
        root_dir.mkdir(parents=True, exist_ok=False)
        definition = WorkflowDefinition.from_dict(workflow)
        registry = RoleTreatmentRegistry.from_dict(role_treatments)
        router = RoleRouter.from_dict(
            registry,
            role_policy,
            certification_authority=certification_authority,
        )
        run_id = "run-" + uuid.uuid4().hex
        ledger = EventLedger(root_dir / "events.jsonl", run_id=run_id)
        artifacts = ArtifactStore(root_dir / "artifacts")
        snapshots = SnapshotStore(root_dir / "snapshots")
        base_snapshot = snapshots.capture(Path(source_dir))
        workspaces = WorkspaceManager(
            snapshots,
            root_dir / "workspaces",
            root_dir / "candidate.json",
        )
        workspaces.initialize(base_snapshot)
        system = cls(
            root_dir=root_dir,
            run_id=run_id,
            graph=RunGraph(run_id, definition),
            registry=registry,
            router=router,
            ledger=ledger,
            artifacts=artifacts,
            snapshots=snapshots,
            workspaces=workspaces,
            specification=specification,
            contract_graph=contract_graph,
        )
        if specification is not None:
            reference = artifacts.put_bytes(
                specification.to_bytes(), media_type="application/json"
            )
            if reference != specification.digest:
                raise IntegrityError("specification artifact digest differs from snapshot")
        if contract_graph is not None:
            if specification is not None:
                contract_graph.validate_against_specification(specification)
            artifacts.put_bytes(
                contract_graph.to_bytes(), media_type="application/json"
            )
        system._append(
            "run.created",
            {
                "workflow_version": definition.version,
                "role_treatment_registry_version": registry.version,
                "role_policy_version": router.version,
                "source_snapshot": base_snapshot,
                "specification_digest": (
                    specification.digest if specification is not None else None
                ),
                "contract_graph_digest": (
                    contract_graph.digest if contract_graph is not None else None
                ),
                "certification_contract_digest": (
                    certification_authority.contract_digest
                    if certification_authority is not None
                    else None
                ),
                "certification_receipt_refs": (
                    sorted(
                        receipt.reference
                        for receipt in certification_authority.receipts
                    )
                    if certification_authority is not None
                    else []
                ),
            },
            stable_key="run.created",
        )
        return system

    @classmethod
    def open(
        cls,
        *,
        root_dir: Path,
        workflow: dict[str, Any],
        role_treatments: dict[str, Any],
        role_policy: dict[str, Any],
        specification: SpecificationSnapshot | None = None,
        contract_graph: ContractGraph | None = None,
        certification_authority: CertificationAuthority | None = None,
    ) -> "LoopstrapSystem":
        root_dir = Path(root_dir)
        ledger_path = root_dir / "events.jsonl"
        try:
            first_line = ledger_path.read_bytes().splitlines()[0]
            run_id = json.loads(first_line)["run_id"]
        except (OSError, IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise IntegrityError("run ledger cannot identify a run") from exc
        if not isinstance(run_id, str) or not run_id:
            raise IntegrityError("run ledger has an invalid run identity")
        ledger = EventLedger(ledger_path, run_id=run_id)
        quarantined: Path | None = None
        raw = ledger_path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            quarantined = ledger.quarantine_partial_tail()
        events = ledger.verify()
        if not events or events[0]["type"] != "run.created":
            raise IntegrityError("run ledger lacks its creation event")
        checkpoints = [
            event for event in events if event["type"] == "state.checkpoint"
        ]
        if not checkpoints:
            raise IntegrityError("run ledger lacks a recoverable state checkpoint")
        state = checkpoints[-1]["payload"]
        required_state = {
            "graph",
            "jobs",
            "assignments",
            "run_status",
            "interventions",
            "specification_digest",
            "contract_graph_digest",
            "evidence_records",
            "acceptance_records",
        }
        if not isinstance(state, dict) or set(state) != required_state:
            raise IntegrityError("run state checkpoint fields are invalid")

        definition = WorkflowDefinition.from_dict(workflow)
        registry = RoleTreatmentRegistry.from_dict(role_treatments)
        router = RoleRouter.from_dict(
            registry,
            role_policy,
            certification_authority=certification_authority,
        )
        created = events[0]["payload"]
        if (
            created.get("workflow_version") != definition.version
            or created.get("role_treatment_registry_version") != registry.version
            or created.get("role_policy_version") != router.version
        ):
            raise IntegrityError("recovery configuration versions differ from the run")
        observed_contract = (
            certification_authority.contract_digest
            if certification_authority is not None
            else None
        )
        observed_receipts = (
            sorted(
                receipt.reference
                for receipt in certification_authority.receipts
            )
            if certification_authority is not None
            else []
        )
        if (
            created.get("certification_contract_digest") != observed_contract
            or created.get("certification_receipt_refs", []) != observed_receipts
        ):
            raise IntegrityError("recovery certification authority differs from the run")

        artifacts = ArtifactStore(root_dir / "artifacts")
        expected_specification = state["specification_digest"]
        if expected_specification is not None:
            recovered_specification = SpecificationSnapshot.from_bytes(
                artifacts.get_bytes(expected_specification),
                expected_digest=expected_specification,
            )
            if (
                specification is not None
                and specification.digest != recovered_specification.digest
            ):
                raise IntegrityError("supplied specification differs from the run")
            specification = recovered_specification
        elif specification is not None:
            raise IntegrityError("supplied specification was not bound to the run")

        expected_contract_graph = state["contract_graph_digest"]
        if expected_contract_graph is not None:
            recovered_contract_graph = ContractGraph.from_dict(
                json.loads(artifacts.get_bytes(expected_contract_graph))
            )
            if (
                contract_graph is not None
                and contract_graph.digest != recovered_contract_graph.digest
            ):
                raise IntegrityError("supplied contract graph differs from the run")
            contract_graph = recovered_contract_graph
        elif contract_graph is not None:
            raise IntegrityError("supplied contract graph was not bound to the run")

        graph = RunGraph.from_dict(
            state["graph"],
            definition=definition,
            expected_run_id=run_id,
        )
        snapshots = SnapshotStore(root_dir / "snapshots")
        workspaces = WorkspaceManager(
            snapshots,
            root_dir / "workspaces",
            root_dir / "candidate.json",
        )
        workspaces.current_snapshot()
        system = cls(
            root_dir=root_dir,
            run_id=run_id,
            graph=graph,
            registry=registry,
            router=router,
            ledger=ledger,
            artifacts=artifacts,
            snapshots=snapshots,
            workspaces=workspaces,
            specification=specification,
            contract_graph=contract_graph,
        )
        if state["run_status"] not in {"active", "parked", "paused", "halted"}:
            raise IntegrityError("recovered run status is invalid")
        if not isinstance(state["jobs"], dict) or not isinstance(
            state["assignments"], list
        ) or not isinstance(state["interventions"], list):
            raise IntegrityError("recovered run state containers are invalid")
        system.run_status = state["run_status"]
        system.jobs = {
            job_id: SystemJob.from_dict(
                job_data,
                workspaces_root=root_dir / "workspaces",
            )
            for job_id, job_data in state["jobs"].items()
        }
        system.assignments = [
            Assignment(
                role=item["role"],
                role_treatment_id=item["role_treatment_id"],
                context_lineage=item["context_lineage"],
            )
            for item in state["assignments"]
        ]
        system.interventions = [
            {
                "owner_authorization_ref": item["owner_authorization_ref"],
                "action": item["action"],
                "reason": item["reason"],
            }
            for item in state["interventions"]
        ]
        if not isinstance(state["evidence_records"], dict) or not isinstance(
            state["acceptance_records"], dict
        ):
            raise IntegrityError("recovered evidence state is invalid")
        system.evidence_records = {
            evidence_id: EvidenceRecord.from_dict(row)
            for evidence_id, row in state["evidence_records"].items()
        }
        system.acceptance_records = {
            acceptance_id: AcceptanceRecord.from_dict(row)
            for acceptance_id, row in state["acceptance_records"].items()
        }
        for job in system.jobs.values():
            if job.cell_id not in system.graph.cells:
                raise IntegrityError("recovered job cites an unknown Cell")
            if artifacts.get_bytes(job.response_ref) != canonical_json(
                job.result.evidence()
            ):
                raise IntegrityError("recovered job response artifact differs")
            system.usage_ledger.charge(
                dispatch_id=job.job_id,
                usage=job.result.usage,
                latency_ms=job.result.latency_ms,
            )
        if quarantined is not None:
            system._append(
                "ledger.partial_tail_quarantined",
                {"quarantine_name": quarantined.name},
                stable_key=f"ledger.partial_tail:{quarantined.name}",
            )
        else:
            system._sync_telemetry()
        return system

    def _state_snapshot(self) -> dict[str, Any]:
        return {
            "graph": self.graph.to_dict(),
            "jobs": {
                job_id: job.to_dict()
                for job_id, job in sorted(self.jobs.items())
            },
            "assignments": [
                {
                    "role": assignment.role,
                    "role_treatment_id": assignment.role_treatment_id,
                    "context_lineage": assignment.context_lineage,
                }
                for assignment in self.assignments
            ],
            "run_status": self.run_status,
            "interventions": [dict(item) for item in self.interventions],
            "specification_digest": (
                self.specification.digest if self.specification is not None else None
            ),
            "contract_graph_digest": (
                self.contract_graph.digest if self.contract_graph is not None else None
            ),
            "evidence_records": {
                evidence_id: record.to_dict()
                for evidence_id, record in sorted(self.evidence_records.items())
            },
            "acceptance_records": {
                acceptance_id: record.to_dict()
                for acceptance_id, record in sorted(self.acceptance_records.items())
            },
        }

    def _checkpoint(self, stable_key: str) -> None:
        event_id = hashlib.sha256(
            f"{self.run_id}:checkpoint:{stable_key}".encode("utf-8")
        ).hexdigest()
        self.ledger.append(
            event_id,
            "state.checkpoint",
            "executor",
            self._state_snapshot(),
        )

    def _event_id(self, stable_key: str) -> str:
        return hashlib.sha256(
            f"{self.run_id}:{stable_key}".encode("utf-8")
        ).hexdigest()

    def _sync_telemetry(self) -> None:
        events = self.ledger.verify()
        self.telemetry.ingest_ledger_events(
            events,
            ledger_path=self.ledger.path,
            run_root=self.root_dir,
        )
        self.telemetry.capture_available_references(
            artifacts=self.artifacts,
            snapshots=self.snapshots,
        )

    def _append(self, event_type: str, payload: dict[str, Any], *, stable_key: str) -> None:
        payload = dict(payload)
        if self.specification is not None:
            payload["specification_digest"] = self.specification.digest
        if self.contract_graph is not None:
            payload["contract_graph_digest"] = self.contract_graph.digest
        event_id = self._event_id(stable_key)
        self.ledger.append(event_id, event_type, "executor", payload)
        self._checkpoint(event_id)
        self._sync_telemetry()

    def _ensure_active(self) -> None:
        if self.run_status != "active":
            raise TransitionError(
                f"run is {self.run_status}; lifecycle mutation is blocked"
            )

    def create_root(self, cell_id: str, *, contract_ref: str, obligations: list[str]) -> None:
        self._ensure_active()
        cell = self.graph.create_root(
            cell_id,
            contract_ref=contract_ref,
            obligations=obligations,
            specification_digest=(
                self.specification.digest if self.specification is not None else None
            ),
            composite_contract_ref=(
                self.contract_graph.root_composite_id
                if self.contract_graph is not None
                else None
            ),
        )
        self._append(
            "cell.created",
            {
                "cell_id": cell.cell_id,
                "phase": cell.phase,
                "revision": cell.revision,
                "contract_ref": contract_ref,
                "obligations": list(cell.obligations),
                "specification_digest": cell.specification_digest,
                "composite_contract_ref": cell.composite_contract_ref,
            },
            stable_key=f"cell.created:{cell.cell_id}:{cell.revision}",
        )

    def accept_contract(self, cell_id: str) -> None:
        self._ensure_active()
        previous = self.graph.cell(cell_id).phase
        self.graph.accept_contract(cell_id)
        cell = self.graph.cell(cell_id)
        self._append(
            "cell.transitioned",
            {
                "cell_id": cell_id,
                "from": previous,
                "to": cell.phase,
                "revision": cell.revision,
            },
            stable_key=f"contract.accepted:{cell_id}:{cell.revision}",
        )

    def freeze_tests(
        self,
        cell_id: str,
        *,
        visible_digest: str,
        holdout_digest: str,
        obligation_map: dict[str, list[str]],
        executable: bool,
    ) -> None:
        self._ensure_active()
        self.graph.freeze_tests(
            cell_id,
            visible_digest=visible_digest,
            holdout_digest=holdout_digest,
            obligation_map=obligation_map,
            executable=executable,
        )
        cell = self.graph.cell(cell_id)
        self._append(
            "tests.frozen",
            {
                "cell_id": cell_id,
                "revision": cell.revision,
                "visible_digest": visible_digest,
                "holdout_digest": holdout_digest,
                "obligation_map": obligation_map,
                "executable": executable,
            },
            stable_key=f"tests.frozen:{cell_id}:{cell.revision}",
        )

    def record_plan(
        self,
        cell_id: str,
        *,
        plan_digest: str,
        responsibilities: dict[str, str],
    ) -> None:
        self._ensure_active()
        self.graph.record_plan(
            cell_id,
            plan_digest=plan_digest,
            responsibilities=responsibilities,
        )
        cell = self.graph.cell(cell_id)
        self._append(
            "plan.recorded",
            {
                "cell_id": cell_id,
                "revision": cell.revision,
                "plan_digest": plan_digest,
                "responsibilities": responsibilities,
            },
            stable_key=f"plan.recorded:{cell_id}:{cell.revision}",
        )

    def record_pre_review(
        self,
        cell_id: str,
        *,
        accepted: bool,
        leaf: bool,
        unresolved_seams: list[str],
        review_job_id: str | None = None,
    ) -> None:
        self._ensure_active()
        review_job = self._require_review_job(cell_id, review_job_id)
        self.graph.record_pre_review(
            cell_id,
            accepted=accepted,
            leaf=leaf,
            unresolved_seams=unresolved_seams,
        )
        cell = self.graph.cell(cell_id)
        self._append(
            "pre_review.recorded",
            {
                "cell_id": cell_id,
                "revision": cell.revision,
                "accepted": accepted,
                "leaf": leaf,
                "unresolved_seams": list(unresolved_seams),
                "review_job_id": review_job.job_id if review_job else None,
                "review_response_ref": review_job.response_ref if review_job else None,
            },
            stable_key=f"pre_review.recorded:{cell_id}:{cell.revision}",
        )

    def decompose(self, cell_id: str, children: list[ChildSpec]) -> None:
        self._ensure_active()
        if self.contract_graph is not None:
            parent = self.graph.cell(cell_id)
            if parent.composite_contract_ref is None:
                raise SchemaError(
                    f"Cell lacks an explicit composite contract: {cell_id}"
                )
            composite = self.contract_graph.composite(parent.composite_contract_ref)
            if set(composite.members) != {child.cell_id for child in children}:
                raise SchemaError(
                    "decomposition members differ from the compiled composite contract"
                )
            for child in children:
                contract = self.contract_graph.cell(child.cell_id)
                if (
                    child.contract_ref is not None
                    and child.contract_ref not in contract.contract_refs
                ):
                    raise SchemaError(
                        f"child {child.cell_id} contract reference is not declared"
                    )
        self.graph.decompose(cell_id, children)
        parent = self.graph.cell(cell_id)
        for child_id in parent.children:
            child = self.graph.cell(child_id)
            if self.contract_graph is not None:
                child.cell_contract_ref = child_id
                nested = self.contract_graph.composite_for_cell(child_id)
                child.composite_contract_ref = (
                    nested.composite_id if nested is not None else None
                )
            self._append(
                "cell.created",
                {
                    "cell_id": child.cell_id,
                    "parent_id": parent.cell_id,
                    "phase": child.phase,
                    "revision": child.revision,
                    "contract_ref": child.contract_ref,
                    "obligations": list(child.obligations),
                    "scope": list(child.scope),
                    "owner": child.owner,
                    "cell_contract_ref": child.cell_contract_ref,
                    "composite_contract_ref": child.composite_contract_ref,
                    "specification_digest": child.specification_digest,
                },
                stable_key=f"cell.created:{child.cell_id}:{child.revision}",
            )
        self._append(
            "cell.decomposed",
            {
                "cell_id": parent.cell_id,
                "revision": parent.revision,
                "children": list(parent.children),
            },
            stable_key=f"cell.decomposed:{parent.cell_id}:{parent.revision}",
        )

    def control_view(self, cell_id: str) -> ControlView:
        cell = self.graph.cell(cell_id)
        pending = sorted(
            claim.claim_id for claim in cell.claims.values() if claim.blocking
        )
        evidence = [
            reference
            for reference in (
                cell.contract_ref,
                cell.visible_tests_digest,
                cell.plan_digest,
            )
            if reference
        ]
        return ControlView.from_dict(
            {
                "run_id": self.run_id,
                "cell_id": cell_id,
                "phase": cell.phase,
                "revision": cell.revision,
                "pending_claim_ids": pending,
                "evidence_refs": evidence,
                "budget_remaining": {},
            }
        )

    def dispatch(
        self,
        authorization: Authorization,
        *,
        prompt_ref: str,
        context_manifest_ref: str,
        context_lineage: str,
        cache_lineage: str | None,
    ) -> SystemJob:
        self._ensure_active()
        if authorization.act != "dispatch":
            raise AuthorityError(
                f"authorization act {authorization.act!r} cannot start a harness"
            )
        cell = self.graph.cell(authorization.cell_id)
        role = self.graph.required_role(cell.cell_id)
        if role is None:
            raise SchemaError(f"cell phase has no dispatch role: {cell.phase}")
        role_treatment = self.router.resolve(
            role,
            assignments=self.assignments,
            context_lineage=context_lineage,
        )
        AuthorizationValidator.validate(
            authorization,
            self.control_view(cell.cell_id),
            required_role=role,
            role_treatment_id=role_treatment.id,
        )
        dispatch_key = (
            f"{cell.cell_id}:{cell.revision}:{role}:{authorization.authorization_id}"
        )
        reservation = self.journal.reserve(
            dispatch_key=dispatch_key,
            cell_id=cell.cell_id,
            cell_revision=cell.revision,
            role=role,
            role_treatment_id=role_treatment.id,
        )
        existing = self.jobs.get(reservation.job_id)
        if existing is not None:
            if (
                existing.result.prompt_ref != prompt_ref
                or existing.result.context_manifest_ref != context_manifest_ref
                or existing.result.context_lineage != context_lineage
                or existing.result.cache_lineage != cache_lineage
            ):
                raise IdempotencyError(
                    "completed dispatch was retried with different invocation bindings"
                )
            return existing
        base_snapshot = self._dispatch_base_snapshot(cell.cell_id)
        workspace = self.workspaces.prepare(reservation.job_id, base_snapshot)
        invocation = Invocation(
            invocation_id=reservation.job_id,
            run_id=self.run_id,
            cell_id=cell.cell_id,
            cell_revision=cell.revision,
            role=role,
            prompt_ref=prompt_ref,
            context_manifest_ref=context_manifest_ref,
            context_lineage=context_lineage,
            cache_lineage=cache_lineage,
            workspace=workspace.path,
            timeout_seconds=30.0,
            max_output_bytes=1_000_000,
            environment={},
        )
        reservation_event_id = (
            "dispatch:" + hashlib.sha256(dispatch_key.encode("utf-8")).hexdigest()
        )
        started_stable_key = f"harness.started:{reservation.job_id}"
        started_event_id = self._event_id(started_stable_key)
        self._append(
            "harness.started",
            {
                "job_id": reservation.job_id,
                "attempt_id": reservation.job_id,
                "cell_id": cell.cell_id,
                "cell_revision": cell.revision,
                "role": role,
                "role_treatment_id": role_treatment.id,
                "requested_role_treatment": role_treatment.effective_identity(),
                "role_treatment_static_identity": role_treatment.static_identity(),
                "role_treatment_static_digest": role_treatment.static_identity_digest(),
                "prompt_ref": prompt_ref,
                "context_manifest_ref": context_manifest_ref,
                "context_lineage": context_lineage,
                "cache_lineage": cache_lineage,
                "base_snapshot": base_snapshot,
                "timeout_seconds": invocation.timeout_seconds,
                "max_output_bytes": invocation.max_output_bytes,
                "environment": dict(invocation.environment),
                "effective_environment_keys": sorted(
                    sanitized_environment(invocation.environment)
                ),
                "live": False,
                "require_live": False,
                "cause_event_id": reservation_event_id,
                "observed_monotonic_ns": time.monotonic_ns(),
                "paths": {
                    "run_root": str(self.root_dir),
                    "workspace": str(workspace.path),
                    "artifact_root": str(self.artifacts.root),
                    "snapshot_root": str(self.snapshots.root),
                    "ledger_path": str(self.ledger.path),
                    "telemetry_path": str(self.telemetry.path),
                },
            },
            stable_key=started_stable_key,
        )
        dispatch_started_ns = time.monotonic_ns()
        try:
            result = self.dispatcher.dispatch(role_treatment, invocation)
        except BaseException as exc:
            ended_ns = time.monotonic_ns()
            process_trace = getattr(exc, "process_trace", None)
            self._append(
                "harness.failed",
                {
                    "job_id": reservation.job_id,
                    "attempt_id": reservation.job_id,
                    "cell_id": cell.cell_id,
                    "cell_revision": cell.revision,
                    "role": role,
                    "role_treatment_id": role_treatment.id,
                    "error_class": type(exc).__name__,
                    "execution_ref": getattr(exc, "execution_ref", None),
                    "raw_redaction_count": getattr(
                        exc, "raw_redaction_count", 0
                    ),
                    "latency_ms": int((ended_ns - dispatch_started_ns) / 1_000_000),
                    "duration_ns": ended_ns - dispatch_started_ns,
                    "process_trace": process_trace,
                    "parent_event_id": started_event_id,
                    "cause_event_id": reservation_event_id,
                    "paths": {
                        "run_root": str(self.root_dir),
                        "workspace": str(workspace.path),
                        "artifact_root": str(self.artifacts.root),
                        "snapshot_root": str(self.snapshots.root),
                    },
                },
                stable_key=f"harness.failed:{reservation.job_id}",
            )
            raise
        usage_charge = self.usage_ledger.charge(
            dispatch_id=reservation.job_id,
            usage=result.usage,
            latency_ms=result.latency_ms,
        )
        response_ref = self.artifacts.put_bytes(
            canonical_json(result.evidence()), media_type="application/json"
        )
        self.journal.accept_response(
            reservation.job_id,
            response_revision=result.cell_revision,
            current_cell_revision=cell.revision,
            response_ref=response_ref,
        )
        job = SystemJob(
            job_id=reservation.job_id,
            cell_id=cell.cell_id,
            reservation=reservation,
            workspace=workspace,
            base_snapshot=base_snapshot,
            result=result,
            response_ref=response_ref,
        )
        self.jobs[job.job_id] = job
        self.assignments.append(
            Assignment(
                role=role,
                role_treatment_id=role_treatment.id,
                context_lineage=context_lineage,
            )
        )
        self._checkpoint(f"job.completed:{job.job_id}")
        self._append(
            "harness.completed",
            {
                "job_id": reservation.job_id,
                "attempt_id": reservation.job_id,
                "cell_id": cell.cell_id,
                "cell_revision": cell.revision,
                "role": role,
                "role_treatment_id": role_treatment.id,
                "response_ref": response_ref,
                "usage_charge": usage_charge.to_dict(),
                "duration_ns": result.process_trace["duration_ns"],
                "parent_event_id": started_event_id,
                "cause_event_id": reservation_event_id,
                "paths": {
                    "run_root": str(self.root_dir),
                    "workspace": str(workspace.path),
                    "artifact_root": str(self.artifacts.root),
                    "snapshot_root": str(self.snapshots.root),
                },
                **result.evidence(),
            },
            stable_key=f"harness.completed:{reservation.job_id}",
        )
        return job

    def _dispatch_base_snapshot(self, cell_id: str) -> str:
        cell = self.graph.cell(cell_id)
        if self.graph.phase_kind(cell_id) == "post_review" and not cell.children:
            candidates = [
                job.candidate_snapshot
                for job in self.jobs.values()
                if job.cell_id == cell_id and job.verified and job.candidate_snapshot
            ]
            if len(candidates) != 1:
                raise PromotionError(
                    "leaf post-review requires exactly one verified candidate snapshot"
                )
            return candidates[0]
        return self.current_snapshot()

    def _require_review_job(
        self, cell_id: str, review_job_id: str | None
    ) -> SystemJob | None:
        role = self.graph.required_role(cell_id)
        if role is None:
            raise SchemaError(f"cell phase has no review role: {self.graph.cell(cell_id).phase}")
        if role not in self.router.roles:
            if review_job_id is not None:
                raise AuthorityError(
                    f"review job supplied for unconfigured role: {role}"
                )
            return None
        if review_job_id is None:
            raise AuthorityError(f"configured review role requires job provenance: {role}")
        try:
            job = self.jobs[review_job_id]
        except KeyError as exc:
            raise AuthorityError(f"unknown review job: {review_job_id}") from exc
        cell = self.graph.cell(cell_id)
        if (
            job.cell_id != cell_id
            or job.reservation.role != role
            or job.reservation.cell_revision != cell.revision
            or job.result.status != "completed"
        ):
            raise AuthorityError("review job does not bind to the current cell review phase")
        return job

    def _accept_verified_job(
        self,
        job: SystemJob,
        *,
        evidence_refs: list[str],
    ) -> None:
        if job.verified:
            raise PromotionError(f"job is already verified: {job.job_id}")
        if job.reservation.role != self.graph.required_role(job.cell_id):
            raise PromotionError("job role does not match the current implementation phase")
        candidate = self.workspaces.capture_result(job.workspace, verified=True)
        self.graph.record_verification(
            job.cell_id,
            passed=True,
            evidence_refs=evidence_refs,
        )
        job.candidate_snapshot = candidate
        job.verified = True
        cell = self.graph.cell(job.cell_id)
        self._append(
            "verification.recorded",
            {
                "job_id": job.job_id,
                "cell_id": job.cell_id,
                "revision": cell.revision,
                "passed": True,
                "evidence_refs": list(evidence_refs),
                "candidate_snapshot": candidate,
            },
            stable_key=f"verification.recorded:{job.job_id}",
        )

    def verify_job(
        self,
        job_id: str,
        *,
        passed: bool,
        evidence_refs: list[str],
    ) -> None:
        self._ensure_active()
        try:
            job = self.jobs[job_id]
        except KeyError as exc:
            raise SchemaError(f"unknown active job: {job_id}") from exc
        if not passed:
            raise PromotionError("failed job cannot enter candidate state")
        self._accept_verified_job(job, evidence_refs=evidence_refs)

    def verify_job_with_plan(
        self, job_id: str, plan: VerificationPlan
    ) -> str:
        self._ensure_active()
        try:
            job = self.jobs[job_id]
        except KeyError as exc:
            raise SchemaError(f"unknown active job: {job_id}") from exc
        cell = self.graph.cell(job.cell_id)
        if (
            plan.visible_digest != cell.visible_tests_digest
            or plan.holdout_digest != cell.holdout_tests_digest
        ):
            raise PromotionError("verification plan does not match the frozen test basis")
        report = self.verifier.run(job.workspace.path, plan)
        report_ref = self.artifacts.put_bytes(
            canonical_json(report.to_dict()), media_type="application/json"
        )
        self._append(
            "tests.executed",
            {
                "job_id": job.job_id,
                "attempt_id": job.job_id,
                "cell_id": job.cell_id,
                "revision": cell.revision,
                "visible_digest": report.visible_digest,
                "holdout_digest": report.holdout_digest,
                "passed": report.passed,
                "report_ref": report_ref,
                "receipts": [
                    receipt.to_dict() for receipt in report.receipts
                ],
                "total_duration_ns": sum(
                    receipt.duration_ns for receipt in report.receipts
                ),
                "parent_event_id": self._event_id(
                    f"harness.completed:{job.job_id}"
                ),
                "paths": {
                    "run_root": str(self.root_dir),
                    "workspace": str(job.workspace.path),
                    "artifact_root": str(self.artifacts.root),
                    "snapshot_root": str(self.snapshots.root),
                },
            },
            stable_key=f"tests.executed:{job.job_id}",
        )
        if not report.passed:
            raise PromotionError("visible or holdout verification failed")
        self._accept_verified_job(job, evidence_refs=[report_ref])
        return report_ref

    def record_integration(
        self,
        cell_id: str,
        *,
        passed: bool,
        evidence_refs: list[str],
    ) -> None:
        self._ensure_active()
        if self.graph.phase_kind(cell_id) == "children":
            self.begin_integration(cell_id)
        self.graph.record_integration(
            cell_id,
            passed=passed,
            evidence_refs=evidence_refs,
        )
        cell = self.graph.cell(cell_id)
        self._append(
            "integration.recorded",
            {
                "cell_id": cell_id,
                "revision": cell.revision,
                "passed": passed,
                "evidence_refs": list(evidence_refs),
            },
            stable_key=f"integration.recorded:{cell_id}:{cell.revision}",
        )

    def begin_integration(self, cell_id: str) -> None:
        self._ensure_active()
        self.graph.begin_integration(cell_id)
        cell = self.graph.cell(cell_id)
        self._append(
            "integration.started",
            {
                "cell_id": cell_id,
                "revision": cell.revision,
                "children": list(cell.children),
            },
            stable_key=f"integration.started:{cell_id}:{cell.revision}",
        )

    def _record_orchestrated_verification(
        self,
        cell_id: str,
        *,
        passed: bool,
        evidence_refs: list[str],
    ) -> None:
        self._ensure_active()
        self.graph.record_verification(
            cell_id,
            passed=passed,
            evidence_refs=evidence_refs,
        )
        cell = self.graph.cell(cell_id)
        self._append(
            "verification.recorded",
            {
                "cell_id": cell_id,
                "revision": cell.revision,
                "passed": passed,
                "evidence_refs": list(evidence_refs),
                "source": "role_result",
            },
            stable_key=f"orchestrated.verification:{cell_id}:{cell.revision}",
        )

    def park(self, *, reason: str) -> None:
        if not reason:
            raise SchemaError("parking reason is required")
        self._ensure_active()
        self.run_status = "parked"
        self._append(
            "run.parked",
            {"reason": reason},
            stable_key=f"run.parked:{len(self.ledger.verify())}",
        )

    def record_post_review(
        self,
        cell_id: str,
        *,
        accepted: bool,
        evidence_refs: list[str],
        review_job_id: str | None = None,
    ) -> None:
        self._ensure_active()
        review_job = self._require_review_job(cell_id, review_job_id)
        self.graph.record_post_review(
            cell_id,
            accepted=accepted,
            evidence_refs=evidence_refs,
        )
        cell = self.graph.cell(cell_id)
        self._append(
            "post_review.recorded",
            {
                "cell_id": cell_id,
                "revision": cell.revision,
                "accepted": accepted,
                "evidence_refs": list(evidence_refs),
                "review_job_id": review_job.job_id if review_job else None,
                "review_response_ref": review_job.response_ref if review_job else None,
            },
            stable_key=f"post_review.recorded:{cell_id}:{cell.revision}",
        )

    def promote_job(self, job_id: str) -> None:
        self._ensure_active()
        try:
            job = self.jobs[job_id]
        except KeyError as exc:
            raise SchemaError(f"unknown active job: {job_id}") from exc
        cell = self.graph.cell(job.cell_id)
        if (
            not job.verified
            or not job.candidate_snapshot
            or not cell.post_review_accepted
        ):
            raise PromotionError("promotion requires verified work and accepted post-review")
        blocking = sorted(
            claim.claim_id for claim in cell.claims.values() if claim.blocking
        )
        if blocking:
            raise PromotionError(f"verified claims block promotion: {blocking}")
        try:
            self.executor.promote(
                self.workspaces,
                job.candidate_snapshot,
                expected_current=job.base_snapshot,
            )
        except StaleResultError:
            self._append(
                "promotion.conflict",
                {
                    "job_id": job.job_id,
                    "cell_id": job.cell_id,
                    "candidate_snapshot": job.candidate_snapshot,
                    "expected_snapshot": job.base_snapshot,
                    "current_snapshot": self.current_snapshot(),
                },
                stable_key=f"promotion.conflict:{job.job_id}",
            )
            raise
        job.promoted = True
        self._append(
            "candidate.promoted",
            {
                "job_id": job.job_id,
                "cell_id": job.cell_id,
                "snapshot": job.candidate_snapshot,
                "previous_snapshot": job.base_snapshot,
            },
            stable_key=f"candidate.promoted:{job.job_id}",
        )

    def close(self, cell_id: str) -> None:
        self._ensure_active()
        candidate_jobs = [job for job in self.jobs.values() if job.cell_id == cell_id]
        if candidate_jobs and not any(job.promoted for job in candidate_jobs):
            raise PromotionError("implemented cell cannot close before candidate promotion")
        self.graph.close(cell_id)
        cell = self.graph.cell(cell_id)
        self._append(
            "cell.closed",
            {
                "cell_id": cell_id,
                "revision": cell.revision,
                "phase": cell.phase,
            },
            stable_key=f"cell.closed:{cell_id}:{cell.revision}",
        )

    def pause(self, *, reason: str) -> None:
        if not reason:
            raise SchemaError("pause reason is required")
        self._ensure_active()
        self.run_status = "paused"
        self._append(
            "run.paused",
            {"reason": reason},
            stable_key=f"run.paused:{len(self.ledger.verify())}",
        )

    def halt(self, *, reason: str) -> None:
        if not reason:
            raise SchemaError("halt reason is required")
        if self.run_status == "halted":
            raise TransitionError("run is already halted")
        self.run_status = "halted"
        self._append(
            "run.halted",
            {"reason": reason},
            stable_key=f"run.halted:{len(self.ledger.verify())}",
        )

    def record_intervention(
        self,
        *,
        owner_authorization_ref: str,
        action: str,
        reason: str,
    ) -> None:
        if not owner_authorization_ref:
            raise AuthorityError("owner authorization reference is required")
        if not action or not reason:
            raise SchemaError("intervention action and reason are required")
        intervention = {
            "owner_authorization_ref": owner_authorization_ref,
            "action": action,
            "reason": reason,
        }
        self.interventions.append(intervention)
        self._append(
            "owner.intervention",
            intervention,
            stable_key=(
                f"owner.intervention:{owner_authorization_ref}:"
                f"{len(self.interventions)}"
            ),
        )

    def resume(self, *, owner_authorization_ref: str) -> None:
        if not owner_authorization_ref:
            raise AuthorityError("owner authorization reference is required")
        if self.run_status == "halted":
            raise TransitionError("a halted run cannot resume")
        if self.run_status not in {"paused", "parked"}:
            raise TransitionError("only a paused or parked run can resume")
        eligible = [
            item
            for item in self.interventions
            if item["owner_authorization_ref"] == owner_authorization_ref
            and item["action"] == "continue"
        ]
        if not eligible:
            raise AuthorityError("resume lacks a matching owner intervention")
        previous = self.run_status
        self.run_status = "active"
        self._append(
            "run.resumed",
            {
                "from": previous,
                "owner_authorization_ref": owner_authorization_ref,
            },
            stable_key=f"run.resumed:{len(self.ledger.verify())}",
        )

    def replay_state(self) -> dict[str, Any]:
        return StateReducer.replay(self.ledger.verify())

    def record_evidence(self, record: EvidenceRecord) -> str:
        self._ensure_active()
        if self.specification is None:
            raise IntegrityError("evidence requires a bound project specification")
        if record.specification_digest != self.specification.digest:
            raise IntegrityError("evidence specification binding differs from the run")
        cell = self.graph.cell(record.cell_id)
        if record.cell_revision != cell.revision:
            raise StaleResultError("evidence is for a stale Cell revision")
        if record.scope_kind == "cell" and record.scope_id != record.cell_id:
            raise SchemaError("Cell evidence scope does not identify its Cell")
        if record.scope_kind == "composite":
            if (
                self.contract_graph is None
                or record.scope_id
                not in {
                    item.composite_id for item in self.contract_graph.composites
                }
            ):
                raise SchemaError("composite evidence scope is unknown")
        if record.scope_kind == "root":
            roots = [
                item.cell_id
                for item in self.graph.cells.values()
                if item.parent_id is None
            ]
            if roots != [record.scope_id]:
                raise SchemaError("root evidence scope does not identify the root Cell")
        self.artifacts.get_bytes(record.execution_ref)
        for reference in record.artifact_refs:
            try:
                self.artifacts.get_bytes(reference)
            except IntegrityError:
                self.snapshots.verify(reference)
        existing = self.evidence_records.get(record.evidence_id)
        if existing is not None and existing != record:
            raise IdempotencyError(
                f"evidence id reused with different content: {record.evidence_id}"
            )
        reference = self.artifacts.put_bytes(
            canonical_json(record.to_dict()), media_type="application/json"
        )
        self.evidence_records[record.evidence_id] = record
        self._append(
            "evidence.recorded",
            {
                "evidence_id": record.evidence_id,
                "cell_id": record.cell_id,
                "cell_revision": record.cell_revision,
                "scope_kind": record.scope_kind,
                "scope_id": record.scope_id,
                "obligation_ids": list(record.obligation_ids),
                "producer_id": record.producer_id,
                "producer_class": record.producer_class,
                "evidence_ref": reference,
            },
            stable_key=f"evidence.recorded:{record.evidence_id}",
        )
        return reference

    def evaluate_acceptance(
        self,
        *,
        acceptance_id: str,
        obligations: list[AcceptanceObligation],
        unresolved_finding_ids: list[str] | None = None,
    ) -> AcceptanceRecord:
        self._ensure_active()
        if self.specification is None:
            raise IntegrityError("acceptance requires a bound project specification")
        blocking = {
            claim.claim_id
            for cell in self.graph.cells.values()
            for claim in cell.claims.values()
            if claim.blocking
        }
        blocking.update(unresolved_finding_ids or [])
        result = AcceptanceEngine().evaluate(
            acceptance_id=acceptance_id,
            specification_digest=self.specification.digest,
            current_revisions={
                cell_id: cell.revision
                for cell_id, cell in self.graph.cells.items()
            },
            obligations=obligations,
            evidence=self.evidence_records.values(),
            unresolved_finding_ids=sorted(blocking),
        )
        existing = self.acceptance_records.get(result.acceptance_id)
        if existing is not None and existing != result:
            raise IdempotencyError(
                f"acceptance id reused with different result: {result.acceptance_id}"
            )
        reference = self.artifacts.put_bytes(
            canonical_json(result.to_dict()), media_type="application/json"
        )
        self.acceptance_records[result.acceptance_id] = result
        self._append(
            "acceptance.evaluated",
            {
                "acceptance_id": result.acceptance_id,
                "accepted": result.accepted,
                "satisfied_obligation_ids": list(
                    result.satisfied_obligation_ids
                ),
                "unsatisfied_obligation_ids": list(
                    result.unsatisfied_obligation_ids
                ),
                "unresolved_finding_ids": list(result.unresolved_finding_ids),
                "acceptance_ref": reference,
            },
            stable_key=f"acceptance.evaluated:{result.acceptance_id}",
        )
        return result

    def require_acceptance(self, acceptance_id: str) -> AcceptanceRecord:
        try:
            record = self.acceptance_records[acceptance_id]
        except KeyError as exc:
            raise PromotionError(
                f"required acceptance record does not exist: {acceptance_id}"
            ) from exc
        if not record.accepted:
            raise PromotionError(
                f"required acceptance record is not green: {acceptance_id}"
            )
        if (
            self.specification is None
            or record.specification_digest != self.specification.digest
        ):
            raise PromotionError("acceptance record has the wrong specification binding")
        return record

    def current_snapshot(self) -> str:
        return self.workspaces.current_snapshot()

    def materialize_current(self, destination: Path) -> None:
        self.snapshots.materialize(self.current_snapshot(), Path(destination))

    def status(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_status": self.run_status,
            "current_snapshot": self.current_snapshot(),
            "usage_totals": self.usage_ledger.totals().to_dict(),
            "cells": {
                cell_id: {
                    "phase": cell.phase,
                    "phase_kind": self.graph.phase_kind(cell_id),
                    "revision": cell.revision,
                    "pending_verified_claims": sorted(
                        claim.claim_id
                        for claim in cell.claims.values()
                        if claim.blocking
                    ),
                }
                for cell_id, cell in self.graph.cells.items()
            },
        }
