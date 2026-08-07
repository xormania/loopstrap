from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def workflow_definition() -> dict[str, object]:
    return {
        "version": 1,
        "initial": "contract_basis",
        "phases": {
            "contract_basis": {
                "kind": "contract",
                "role": "contract_adversary",
                "on": {"accepted": "tests_before_plan"},
            },
            "tests_before_plan": {
                "kind": "tests",
                "role": "blind_test_author",
                "on": {"frozen": "planning"},
            },
            "planning": {
                "kind": "plan",
                "role": "planner",
                "on": {"planned": "decomposition_attack"},
            },
            "decomposition_attack": {
                "kind": "pre_review",
                "role": "decomposition_adversary",
                "on": {"leaf": "implementation", "composite": "children"},
            },
            "children": {
                "kind": "children",
                "role": None,
                "on": {"integrated": "integration"},
            },
            "implementation": {
                "kind": "implementation",
                "role": "implementer",
                "on": {"verified": "result_attack"},
            },
            "integration": {
                "kind": "integration",
                "role": "integrator",
                "on": {"verified": "result_attack"},
            },
            "result_attack": {
                "kind": "post_review",
                "role": "result_adversary",
                "on": {"accepted": "closed"},
            },
            "closed": {"kind": "closed", "role": None, "on": {}},
            "parked": {"kind": "parked", "role": None, "on": {"reopen": "contract_basis"}},
        },
    }


def treatment(
    role_treatment_id: str,
    *,
    role: str = "implementer",
    harness: str,
    model: str,
    reasoning: str,
    command: list[str] | None = None,
    enabled: bool = True,
    capabilities: tuple[str, ...] = ("json",),
) -> dict[str, object]:
    return {
        "id": role_treatment_id,
        "role": role,
        "harness": harness,
        "model_route": {
            "provider": harness,
            "selector": model,
            "allowed_resolved_models": [model],
            "fallback_policy": "deny",
        },
        "reasoning": {
            "control": "effort",
            "requested": reasoning,
            "expected_wire": reasoning,
            "orchestration": "single-agent",
            "proof_sources": ["runtime_event"],
        },
        "wrapper": {
            "id": (command or [sys.executable])[0],
            "version": "1",
            "vendor_executable": harness,
        },
        "configuration": {"profile": reasoning},
        "capabilities": list(capabilities),
        "enabled": enabled,
        "command": command or [sys.executable, str(Path(__file__).with_name("mock_harness.py"))],
    }


def write_request(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def certification_authority(
    rows: list[dict[str, object]], root: Path
):
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
            (Path(__file__).resolve().parents[2] / "config" / "harness-certification.v1.json")
            .read_text(encoding="utf-8")
        )
    )
    artifacts = ArtifactStore(root / "certification-artifacts")
    receipts = []
    for raw in rows:
        parsed = RoleTreatment.from_dict(raw)
        evidence_refs = tuple(
            artifacts.put_bytes(
                f"{parsed.id}:{layer}:PASS".encode("utf-8"),
                media_type="text/plain",
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
                run_id="deterministic-test-certification",
                layer_results={layer: "PASS" for layer in contract.required_layers},
                evidence_refs=evidence_refs,
                report_ref=None,
                issued_at="2026-07-23T00:00:00Z",
            )
        )
    return CertificationAuthority(
        contract_digest=contract.digest,
        artifacts=artifacts,
        receipts=receipts,
    )
