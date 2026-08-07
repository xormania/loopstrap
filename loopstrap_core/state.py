from __future__ import annotations

from copy import deepcopy
from typing import Any


class StateReducer:
    @staticmethod
    def replay(events: list[dict[str, Any]]) -> dict[str, Any]:
        state: dict[str, Any] = {
            "run_id": events[0]["run_id"] if events else None,
            "run_status": "active",
            "cells": {},
            "jobs": {},
            "interventions": [],
            "promotion_conflicts": [],
        }
        for event in events:
            payload = event["payload"]
            event_type = event["type"]
            if event_type == "cell.created":
                state["cells"][payload["cell_id"]] = {
                    "phase": payload.get("phase"),
                    "revision": payload.get("revision", 1),
                }
            elif event_type == "cell.transitioned":
                cell = state["cells"].setdefault(payload["cell_id"], {})
                cell["phase"] = payload["to"]
                cell["revision"] = payload.get("revision", cell.get("revision", 0) + 1)
            elif event_type == "cell.closed":
                cell = state["cells"].setdefault(payload["cell_id"], {})
                cell["phase"] = "closed"
                cell["revision"] = payload.get("revision", cell.get("revision"))
            elif event_type == "job.reserved":
                state["jobs"][payload["job_id"]] = deepcopy(payload)
            elif event_type == "job.result_accepted":
                state["jobs"].setdefault(payload["job_id"], {})["status"] = "accepted"
            elif event_type == "job.result_rejected_stale":
                state["jobs"].setdefault(payload["job_id"], {})["status"] = "rejected_stale"
            elif event_type == "candidate.promoted":
                state["current_snapshot"] = payload["snapshot"]
            elif event_type == "run.paused":
                state["run_status"] = "paused"
            elif event_type == "run.parked":
                state["run_status"] = "parked"
            elif event_type == "run.halted":
                state["run_status"] = "halted"
            elif event_type == "run.resumed":
                state["run_status"] = "active"
            elif event_type == "owner.intervention":
                state["interventions"].append(deepcopy(payload))
            elif event_type == "promotion.conflict":
                state["promotion_conflicts"].append(deepcopy(payload))
        return state
