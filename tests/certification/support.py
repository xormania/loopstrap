from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MOCK_HARNESS = ROOT / "tests" / "acceptance" / "mock_harness.py"
CONTRACT_PATH = ROOT / "config" / "harness-certification.v1.json"
WORKFLOW_PATH = ROOT / "config" / "workflow.v1.json"
PROJECT_FIXTURE = ROOT / "tests" / "readiness" / "fixtures" / "project"
CUE_BINARY = ROOT / "tools" / "cue" / "v0.17.0" / "cue"
CUE_PIN = ROOT / "config" / "cue-tool.v1.json"
CUE_SCHEMA = ROOT / "spec" / "cue"


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    return digest_bytes(value.encode("utf-8"))


def treatment(
    role_treatment_id: str = "mock-certified",
    *,
    role: str = "implementer",
    enabled: bool = True,
    behavior: str = "write",
    reasoning: str = "fixed",
) -> dict[str, Any]:
    return {
        "id": role_treatment_id,
        "role": role,
        "harness": "mock",
        "model_route": {
            "provider": "mock",
            "selector": "deterministic",
            "allowed_resolved_models": ["deterministic"],
            "fallback_policy": "deny",
        },
        "reasoning": {
            "control": "fixed",
            "requested": reasoning,
            "expected_wire": reasoning,
            "orchestration": "single-agent",
            "proof_sources": ["runtime_event"],
        },
        "wrapper": {
            "id": sys.executable,
            "version": "1",
            "vendor_executable": "mock",
        },
        "configuration": {
            "behavior": behavior,
        },
        "capabilities": ["json", "workspace_write"],
        "enabled": enabled,
        "command": [sys.executable, str(MOCK_HARNESS), "--behavior", behavior],
    }


def load_contract():
    from loopstrap_core.certification import CertificationContract

    return CertificationContract.from_dict(
        json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    )


def workflow() -> dict[str, Any]:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def compiled_specification():
    from loopstrap_core.specification import (
        CUECompiler,
        SpecificationCompiler,
        ToolPin,
    )

    pin = json.loads(CUE_PIN.read_text(encoding="utf-8"))
    return SpecificationCompiler(
        CUECompiler(
            binary=CUE_BINARY,
            pin=ToolPin(
                version=pin["version"],
                sha256=pin["binary_sha256"],
            ),
            schema_root=CUE_SCHEMA,
        )
    ).compile(PROJECT_FIXTURE)


def issue_receipt(
    row: dict[str, Any],
    artifacts,
    *,
    statuses: dict[str, str] | None = None,
):
    from loopstrap_core.certification import (
        CertificationReceipt,
        ExecutableIdentity,
    )
    from loopstrap_core.harness import RoleTreatment

    value = RoleTreatment.from_dict(row)
    executable = ExecutableIdentity.observe(
        Path(value.command[0]), version="test-runtime"
    )
    evidence_refs = tuple(
        artifacts.put_bytes(
            f"{layer}:{status}".encode("utf-8"),
            media_type="text/plain",
        )
        for layer, status in sorted(
            (
                statuses
                or {
                    "mechanical": "PASS",
                    "inference": "PASS",
                    "loopstrap": "PASS",
                }
            ).items()
        )
    )
    return CertificationReceipt.issue(
        role_treatment=value,
        executables=(executable,),
        contract_digest=load_contract().digest,
        run_id="cert-run-test",
        layer_results=(
            statuses
            or {
                "mechanical": "PASS",
                "inference": "PASS",
                "loopstrap": "PASS",
            }
        ),
        evidence_refs=evidence_refs,
        report_ref=None,
        issued_at="2026-07-23T00:00:00Z",
    )


def authority(row: dict[str, Any], artifacts, *, statuses=None):
    from loopstrap_core.certification import CertificationAuthority

    receipt = issue_receipt(row, artifacts, statuses=statuses)
    return CertificationAuthority(
        contract_digest=load_contract().digest,
        artifacts=artifacts,
        receipts=(receipt,),
    )
