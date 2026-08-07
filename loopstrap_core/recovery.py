from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .errors import IdempotencyError, SchemaError, StaleResultError
from .ledger import EventLedger


@dataclass(frozen=True)
class JobReservation:
    job_id: str
    dispatch_key: str
    cell_id: str
    cell_revision: int
    role: str
    role_treatment_id: str


class DispatchJournal:
    def __init__(self, ledger: EventLedger) -> None:
        self.ledger = ledger

    @staticmethod
    def _job_id(dispatch_key: str) -> str:
        return "job-" + hashlib.sha256(dispatch_key.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _reservation(payload: dict[str, object]) -> JobReservation:
        return JobReservation(
            job_id=str(payload["job_id"]),
            dispatch_key=str(payload["dispatch_key"]),
            cell_id=str(payload["cell_id"]),
            cell_revision=int(payload["cell_revision"]),
            role=str(payload["role"]),
            role_treatment_id=str(payload["role_treatment_id"]),
        )

    def reserve(
        self,
        *,
        dispatch_key: str,
        cell_id: str,
        cell_revision: int,
        role: str,
        role_treatment_id: str,
    ) -> JobReservation:
        requested = JobReservation(
            job_id=self._job_id(dispatch_key),
            dispatch_key=dispatch_key,
            cell_id=cell_id,
            cell_revision=cell_revision,
            role=role,
            role_treatment_id=role_treatment_id,
        )
        for event in self.ledger.verify():
            if event["type"] != "job.reserved":
                continue
            existing = self._reservation(event["payload"])
            if existing.dispatch_key == dispatch_key:
                if existing != requested:
                    raise IdempotencyError(
                        f"dispatch key reused with different reservation: {dispatch_key}"
                    )
                return existing
        payload = {
            "job_id": requested.job_id,
            "dispatch_key": dispatch_key,
            "cell_id": cell_id,
            "cell_revision": cell_revision,
            "role": role,
            "role_treatment_id": role_treatment_id,
            "status": "reserved",
        }
        self.ledger.append(
            f"dispatch:{hashlib.sha256(dispatch_key.encode('utf-8')).hexdigest()}",
            "job.reserved",
            "executor",
            payload,
        )
        return requested

    def _find(self, job_id: str) -> JobReservation:
        for event in self.ledger.verify():
            if event["type"] == "job.reserved" and event["payload"]["job_id"] == job_id:
                return self._reservation(event["payload"])
        raise SchemaError(f"unknown job reservation: {job_id}")

    def accept_response(
        self,
        job_id: str,
        *,
        response_revision: int,
        current_cell_revision: int,
        response_ref: str,
    ) -> None:
        reservation = self._find(job_id)
        if (
            response_revision != reservation.cell_revision
            or response_revision != current_cell_revision
        ):
            self.ledger.append(
                f"result:{job_id}:stale:{current_cell_revision}",
                "job.result_rejected_stale",
                "executor",
                {
                    "job_id": job_id,
                    "response_revision": response_revision,
                    "current_cell_revision": current_cell_revision,
                    "response_ref": response_ref,
                },
            )
            raise StaleResultError(f"job response is stale: {job_id}")
        self.ledger.append(
            f"result:{job_id}:accepted",
            "job.result_accepted",
            "executor",
            {
                "job_id": job_id,
                "cell_revision": response_revision,
                "response_ref": response_ref,
            },
        )
