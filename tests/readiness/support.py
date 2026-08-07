from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROJECT_FIXTURE = ROOT / "tests" / "readiness" / "fixtures" / "project"
CUE_BINARY = ROOT / "tools" / "cue" / "v0.17.0" / "cue"
CUE_PIN = ROOT / "config" / "cue-tool.v1.json"
CUE_SCHEMA = ROOT / "spec" / "cue"
MOCK_HARNESS = ROOT / "tests" / "acceptance" / "mock_harness.py"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def workflow() -> dict[str, Any]:
    return json.loads((ROOT / "config" / "workflow.v1.json").read_text(encoding="utf-8"))


def treatment(
    role_treatment_id: str,
    *,
    role: str = "implementer",
    behavior: str = "clean",
    capabilities: tuple[str, ...] = ("json", "workspace_write"),
) -> dict[str, Any]:
    return {
        "id": role_treatment_id,
        "role": role,
        "harness": "mock",
        "model_route": {
            "provider": "mock",
            "selector": f"deterministic-{role_treatment_id}",
            "allowed_resolved_models": [f"deterministic-{role_treatment_id}"],
            "fallback_policy": "deny",
        },
        "reasoning": {
            "control": "fixed",
            "requested": "fixed",
            "expected_wire": "fixed",
            "orchestration": "single-agent",
            "proof_sources": ["runtime_event"],
        },
        "wrapper": {
            "id": sys.executable,
            "version": "1",
            "vendor_executable": "mock",
        },
        "configuration": {"behavior": behavior},
        "capabilities": list(capabilities),
        "enabled": True,
        "command": [sys.executable, str(MOCK_HARNESS), "--behavior", behavior],
    }


def all_roles(role_treatment_id: str = "mock") -> dict[str, dict[str, Any]]:
    phases = workflow()["phases"]
    roles = {
        phase["role"]
        for phase in phases.values()
        if phase["role"] is not None
    }
    return {
        role: {"role_treatment": role_treatment_id, "requires": []}
        for role in sorted(roles)
    }


def minimal_cell(
    cell_id: str,
    *,
    input_schema: str = "schema.document",
    output_schema: str = "schema.analysis",
    guarantee_id: str | None = None,
    responsibility: str = "exclusive",
    contract_ref: str = "contract.root",
) -> dict[str, Any]:
    guarantee = guarantee_id or f"guarantee.{cell_id}"
    return {
        "id": cell_id,
        "contract_refs": [contract_ref],
        "inputs": [{"id": "in", "schema_ref": input_schema}],
        "outputs": [{"id": "out", "schema_ref": output_schema}],
        "guarantees": [
            {
                "id": guarantee,
                "responsibility": responsibility,
                "contract_refs": [contract_ref],
                "verification_obligation_ids": [f"verify.{cell_id}"],
            }
        ],
        "failures": ["declared failure"],
        "owned_effects": ["workspace"],
        "dependencies": [],
        "invariants": ["specification binding remains stable"],
        "verification_obligations": [
            {
                "id": f"verify.{cell_id}",
                "scope_kind": "cell",
                "eligible_producer_classes": ["test_harness"],
                "minimum_evidence": 1,
            }
        ],
    }


def contract_graph_data() -> dict[str, Any]:
    first = minimal_cell("cell.first")
    second = minimal_cell(
        "cell.second",
        input_schema="schema.analysis",
        output_schema="schema.result",
        contract_ref="contract.second",
    )
    return {
        "version": 1,
        "specification_digest": "sha256:" + digest("spec"),
        "root_composite_id": "composite.root",
        "cells": [first, second],
        "composites": [
            {
                "id": "composite.root",
                "members": ["cell.first", "cell.second"],
                "connections": [
                    {
                        "source": {"cell_id": "cell.first", "port_id": "out"},
                        "target": {"cell_id": "cell.second", "port_id": "in"},
                    }
                ],
                "external_inputs": [
                    {"cell_id": "cell.first", "port_id": "in"}
                ],
                "external_outputs": [
                    {"cell_id": "cell.second", "port_id": "out"}
                ],
                "guarantees": [
                    {
                        "id": "guarantee.root",
                        "responsibility": "composite",
                        "contract_refs": ["contract.root"],
                        "verification_obligation_ids": ["verify.root"],
                        "supported_by": [
                            "guarantee.cell.first",
                            "guarantee.cell.second",
                        ],
                    }
                ],
                "failures": ["member or connection failure"],
                "invariants": ["member specification bindings agree"],
                "verification_obligations": [
                    {
                        "id": "verify.root",
                        "scope_kind": "composite",
                        "eligible_producer_classes": ["integration_harness"],
                        "minimum_evidence": 1,
                    }
                ],
            }
        ],
    }


def evidence_data(
    *,
    evidence_id: str = "evidence.1",
    scope_kind: str = "cell",
    scope_id: str = "cell.first",
    producer_id: str = "test-runner",
    producer_class: str = "test_harness",
) -> dict[str, Any]:
    return {
        "id": evidence_id,
        "specification_digest": "sha256:" + digest("spec"),
        "cell_id": scope_id,
        "cell_revision": 7,
        "scope_kind": scope_kind,
        "scope_id": scope_id,
        "role_treatment_id": "mock-treatment",
        "producer_id": producer_id,
        "producer_class": producer_class,
        "subject_producer_ids": ["implementer"],
        "obligation_ids": [f"verify.{scope_id}"],
        "execution_ref": "sha256:" + digest("execution"),
        "artifact_refs": ["sha256:" + digest("candidate")],
        "observation": {"passed": True},
        "finding_ids": [],
    }


def compiler():
    from loopstrap_core.specification import CUECompiler, SpecificationCompiler, ToolPin

    pin_data = json.loads(CUE_PIN.read_text(encoding="utf-8"))
    return SpecificationCompiler(
        CUECompiler(
            binary=CUE_BINARY,
            pin=ToolPin(
                version=pin_data["version"],
                sha256=pin_data["binary_sha256"],
            ),
            schema_root=CUE_SCHEMA,
        )
    )


def compiled_specification():
    return compiler().compile(PROJECT_FIXTURE)


def certification_authority(rows: list[dict[str, Any]], base: Path):
    from loopstrap_core.artifacts import ArtifactStore
    from loopstrap_core.certification import (
        CertificationAuthority,
        CertificationContract,
        CertificationReceipt,
        ExecutableIdentity,
    )
    from loopstrap_core.harness import RoleTreatment

    contract = CertificationContract.from_dict(
        json.loads(
            (ROOT / "config" / "harness-certification.v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    cert_artifacts = ArtifactStore(base / "certification-artifacts")
    receipts = []
    for row in rows:
        parsed = RoleTreatment.from_dict(row)
        refs = tuple(
            cert_artifacts.put_bytes(
                f"{parsed.id}:{layer}".encode("utf-8"), media_type="text/plain"
            )
            for layer in contract.required_layers
        )
        receipts.append(
            CertificationReceipt.issue(
                role_treatment=parsed,
                executables=(
                    ExecutableIdentity.observe(
                        Path(parsed.command[0]), version="deterministic-test"
                    ),
                ),
                contract_digest=contract.digest,
                run_id="readiness-certification",
                layer_results={layer: "PASS" for layer in contract.required_layers},
                evidence_refs=refs,
                report_ref=None,
                issued_at="2026-07-23T00:00:00Z",
            )
        )
    return CertificationAuthority(
        contract_digest=contract.digest,
        artifacts=cert_artifacts,
        receipts=receipts,
    )


def make_system(
    raw: str,
    *,
    roles: dict[str, dict[str, Any]] | None = None,
    treatments: list[dict[str, Any]] | None = None,
    specification=None,
):
    from loopstrap_core.system import LoopstrapSystem

    base = Path(raw)
    source = base / "source"
    source.mkdir()
    (source / "base.txt").write_text("base\n", encoding="utf-8")
    rows = treatments or [treatment("mock", behavior="write")]
    certs = certification_authority(rows, base)
    return LoopstrapSystem.create(
        root_dir=base / "run",
        workflow=workflow(),
        role_treatments={"version": 1, "role_treatments": rows},
        role_policy={"version": 1, "roles": roles or {}},
        source_dir=source,
        specification=specification,
        certification_authority=certs,
    )


def prepare_leaf(system, cell_id: str) -> None:
    system.accept_contract(cell_id)
    cell = system.graph.cell(cell_id)
    system.freeze_tests(
        cell_id,
        visible_digest=digest(f"{cell_id}.visible"),
        holdout_digest=digest(f"{cell_id}.holdout"),
        obligation_map={
            obligation: [f"test::{cell_id}::{obligation}"]
            for obligation in cell.obligations
        },
        executable=True,
    )
    system.record_plan(
        cell_id,
        plan_digest=digest(f"{cell_id}.plan"),
        responsibilities={
            obligation: "implementation"
            for obligation in cell.obligations
        },
    )
    system.record_pre_review(
        cell_id,
        accepted=True,
        leaf=True,
        unresolved_seams=[],
    )


def authorization(system, cell_id: str, role: str, role_treatment_id: str):
    from loopstrap_core.authority import Authorization

    view = system.control_view(cell_id)
    return Authorization.from_dict(
        {
            "authorization_id": f"auth-{cell_id}-{role}-{view.revision}",
            "run_id": system.run_id,
            "cell_id": cell_id,
            "revision": view.revision,
            "role": role,
            "role_treatment_id": role_treatment_id,
            "act": "dispatch",
        }
    )


def dispatch(system, cell_id: str, role: str, role_treatment_id: str, lineage: str):
    return system.dispatch(
        authorization(system, cell_id, role, role_treatment_id),
        prompt_ref="sha256:" + digest(f"{cell_id}.{role}.prompt"),
        context_manifest_ref="sha256:" + digest(f"{cell_id}.{role}.context"),
        context_lineage=lineage,
        cache_lineage=None,
    )
