from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .errors import LoopstrapError, SchemaError
from .contracts import ContractCompiler
from .evidence import EvidenceCompiler
from .harness import RoleRouter, RoleTreatmentRegistry
from .ledger import EventLedger
from .state import StateReducer
from .specification import CUECompiler, SpecificationCompiler, ToolPin
from .workflow import WorkflowDefinition


def _object_file(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SchemaError(f"{label} is not readable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise SchemaError(f"{label} must be a JSON object: {path}")
    return value


def _validate(args: argparse.Namespace) -> dict[str, Any]:
    workflow = WorkflowDefinition.from_dict(_object_file(args.workflow, "workflow"))
    registry = RoleTreatmentRegistry.from_dict(
        _object_file(args.role_treatments, "Role-Treatments")
    )
    router = RoleRouter.from_dict(registry, _object_file(args.roles, "roles"))

    required_roles = {
        phase.role for phase in workflow.phases.values() if phase.role is not None
    }
    assigned_roles = set(router.roles)
    referenced = {
        policy["role_treatment"] for policy in router.roles.values()
    }
    enabled = all(
        registry.get(role_treatment_id).enabled
        for role_treatment_id in referenced
    )
    certified = False
    armed = (
        required_roles.issubset(assigned_roles)
        and bool(required_roles)
        and enabled
        and certified
    )
    issues: list[str] = []
    if not required_roles.issubset(assigned_roles):
        issues.append(
            "role assignments do not cover every workflow role"
        )
    disabled = sorted(
        role_treatment_id
        for role_treatment_id in referenced
        if not registry.get(role_treatment_id).enabled
    )
    if disabled:
        issues.append(f"owner-disabled Role-Treatments: {', '.join(disabled)}")
    if referenced:
        issues.append("certification receipts were not supplied")

    return {
        "workflow_version": workflow.version,
        "role_treatment_registry_version": registry.version,
        "role_policy_version": router.version,
        "role_treatments": len(registry.role_treatments),
        "required_roles": len(required_roles),
        "assigned_roles": len(assigned_roles),
        "armed": armed,
        "issues": issues,
    }


def _status(args: argparse.Namespace) -> dict[str, Any]:
    if not args.ledger.is_file():
        raise SchemaError(f"ledger does not exist or is not a regular file: {args.ledger}")
    ledger = EventLedger(args.ledger, run_id=args.run_id)
    events = ledger.verify()
    return {
        "run_id": args.run_id,
        "event_count": len(events),
        "head_hash": events[-1]["hash"] if events else None,
        "state": StateReducer.replay(events),
    }


def _cue_from_args(args: argparse.Namespace) -> CUECompiler:
    pin_data = _object_file(args.pin, "CUE tool pin")
    expected = {
        "config_version",
        "tool",
        "version",
        "platform",
        "binary_path",
        "release_url",
        "archive_sha256",
        "binary_sha256",
    }
    if set(pin_data) != expected or pin_data["tool"] != "cue":
        raise SchemaError("CUE tool pin fields are invalid")
    return CUECompiler(
        binary=args.cue,
        pin=ToolPin(
            version=str(pin_data["version"]),
            sha256=str(pin_data["binary_sha256"]),
        ),
        schema_root=args.schema,
    )


def _spec_check(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = SpecificationCompiler(_cue_from_args(args)).compile(args.project)
    return {
        "project": snapshot.document["project"]["id"],
        "format_version": snapshot.document["format_version"],
        "schema_version": snapshot.schema_version,
        "cue_version": snapshot.cue_version,
        "specification_digest": snapshot.digest,
    }


def _plan_check(args: argparse.Namespace) -> dict[str, Any]:
    graph = ContractCompiler(_cue_from_args(args)).compile(
        _object_file(args.contracts, "Cell contract graph")
    )
    return {
        "version": graph.version,
        "root_composite_id": graph.root_composite_id,
        "cells": len(graph.cells),
        "composites": len(graph.composites),
        "contract_graph_digest": graph.digest,
        "specification_digest": graph.specification_digest,
    }


def _acceptance_check(args: argparse.Namespace) -> dict[str, Any]:
    record = EvidenceCompiler(_cue_from_args(args)).evaluate(
        _object_file(args.acceptance, "acceptance request")
    )
    return record.to_dict()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="loopstrap")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser(
        "validate", help="validate versioned configuration without executing a model"
    )
    validate.add_argument("--workflow", type=Path, required=True)
    validate.add_argument("--role-treatments", type=Path, required=True)
    validate.add_argument("--roles", type=Path, required=True)
    validate.set_defaults(handler=_validate)

    status = commands.add_parser(
        "status", help="verify an event ledger and replay only its observed state"
    )
    status.add_argument("--ledger", type=Path, required=True)
    status.add_argument("--run-id", required=True)
    status.set_defaults(handler=_status)

    spec_check = commands.add_parser(
        "spec-check",
        help="compile and validate a CUE-backed project package without starting a run",
    )
    spec_check.add_argument("--project", type=Path, required=True)
    spec_check.add_argument("--cue", type=Path, required=True)
    spec_check.add_argument("--pin", type=Path, required=True)
    spec_check.add_argument("--schema", type=Path, required=True)
    spec_check.set_defaults(handler=_spec_check)

    plan_check = commands.add_parser(
        "plan-check",
        help="validate a Cell and composite Cell contract graph with CUE",
    )
    plan_check.add_argument("--contracts", type=Path, required=True)
    plan_check.add_argument("--cue", type=Path, required=True)
    plan_check.add_argument("--pin", type=Path, required=True)
    plan_check.add_argument("--schema", type=Path, required=True)
    plan_check.set_defaults(handler=_plan_check)

    acceptance_check = commands.add_parser(
        "acceptance-check",
        help="validate evidence and evaluate a CUE-backed acceptance request",
    )
    acceptance_check.add_argument("--acceptance", type=Path, required=True)
    acceptance_check.add_argument("--cue", type=Path, required=True)
    acceptance_check.add_argument("--pin", type=Path, required=True)
    acceptance_check.add_argument("--schema", type=Path, required=True)
    acceptance_check.set_defaults(handler=_acceptance_check)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args)
    except (LoopstrapError, OSError, ValueError, TypeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
