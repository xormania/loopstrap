from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest


def role_treatment(
    *,
    role: str = "planner",
    harness: str = "claude-code",
    provider: str = "anthropic",
    selector: str = "fable",
    resolved_model: str = "claude-fable",
    reasoning_control: str = "effort",
    reasoning_requested: str = "ultracode",
    expected_wire: str = "xhigh",
    orchestration: str = "dynamic-workflows",
) -> dict[str, object]:
    wrapper_id = f"loopstrap-harness-{harness}"
    return {
        "id": f"{role}-{harness}-{selector}-{reasoning_requested}",
        "role": role,
        "harness": harness,
        "model_route": {
            "provider": provider,
            "selector": selector,
            "allowed_resolved_models": [resolved_model],
            "fallback_policy": "deny",
        },
        "reasoning": {
            "control": reasoning_control,
            "requested": reasoning_requested,
            "expected_wire": expected_wire,
            "orchestration": orchestration,
            "proof_sources": ["runtime_event", "certified_binary_mapping"],
        },
        "wrapper": {
            "id": wrapper_id,
            "version": "1",
            "vendor_executable": {
                "codex": "codex",
                "claude-code": "claude",
                "grok-build": "grok",
            }[harness],
        },
        "configuration": {
            "user_config_policy": "exclude",
            "arguments": [],
            "settings": {},
            "tools": {"allow": [], "deny": []},
            "permissions": {"mode": "role-bounded"},
            "doctrine": {"files": []},
            "session": {"fresh": True},
            "subagents": {"mode": "disabled"},
            "invocation_overrides": [],
        },
        "capabilities": ["json"],
        "enabled": True,
        "command": [wrapper_id],
    }


class RoleTreatmentIdentityAcceptance(unittest.TestCase):
    def test_role_treatment_separates_role_harness_model_provider_and_native_controls(
        self,
    ) -> None:
        from loopstrap_core.harness import RoleTreatment

        parsed = RoleTreatment.from_dict(role_treatment())
        self.assertEqual(parsed.role, "planner")
        self.assertEqual(parsed.harness, "claude-code")
        self.assertEqual(parsed.model_route.provider, "anthropic")
        self.assertEqual(parsed.model_route.selector, "fable")
        self.assertEqual(parsed.reasoning.requested, "ultracode")
        self.assertEqual(parsed.reasoning.expected_wire, "xhigh")
        self.assertEqual(parsed.reasoning.orchestration, "dynamic-workflows")
        self.assertNotEqual(parsed.harness, parsed.model_route.provider)

        through_claude = role_treatment(
            role="implementer",
            harness="claude-code",
            provider="openai",
            selector="gpt-5.6-sol",
            resolved_model="gpt-5.6-sol",
            reasoning_control="effort",
            reasoning_requested="max",
            expected_wire="max",
            orchestration="claude-code",
        )
        routed = RoleTreatment.from_dict(through_claude)
        self.assertEqual(routed.harness, "claude-code")
        self.assertEqual(routed.model_route.provider, "openai")

    def test_every_identity_bearing_role_treatment_field_changes_its_digest(self) -> None:
        from loopstrap_core.harness import RoleTreatment

        original = role_treatment()
        baseline = RoleTreatment.from_dict(original).static_identity_digest()
        mutations = (
            ("role", "independent-reviewer"),
            ("harness", "codex"),
        )
        for field, value in mutations:
            changed = deepcopy(original)
            changed[field] = value
            if field == "harness":
                changed["wrapper"] = {
                    "id": "loopstrap-harness-codex",
                    "version": "1",
                    "vendor_executable": "codex",
                }
                changed["command"] = ["loopstrap-harness-codex"]
            self.assertNotEqual(
                RoleTreatment.from_dict(changed).static_identity_digest(),
                baseline,
                field,
            )
        for field, value in (
            ("provider", "openai"),
            ("selector", "other-model"),
            ("allowed_resolved_models", ["other-model"]),
            ("fallback_policy", "allow"),
        ):
            changed = deepcopy(original)
            changed["model_route"][field] = value
            if field == "fallback_policy":
                with self.assertRaises(Exception):
                    RoleTreatment.from_dict(changed)
                continue
            self.assertNotEqual(
                RoleTreatment.from_dict(changed).static_identity_digest(),
                baseline,
                field,
            )
        for field, value in (
            ("control", "other-control"),
            ("requested", "max"),
            ("expected_wire", "max"),
            ("orchestration", "none"),
            ("proof_sources", ["runtime_event"]),
        ):
            changed = deepcopy(original)
            changed["reasoning"][field] = value
            self.assertNotEqual(
                RoleTreatment.from_dict(changed).static_identity_digest(),
                baseline,
                field,
            )

    def test_router_rejects_a_role_treatment_for_a_different_role(self) -> None:
        from loopstrap_core.errors import SchemaError
        from loopstrap_core.harness import RoleRouter, RoleTreatmentRegistry

        row = role_treatment(role="planner")
        registry = RoleTreatmentRegistry.from_dict(
            {"version": 1, "role_treatments": [row]}
        )
        with self.assertRaises(SchemaError):
            RoleRouter.from_dict(
                registry,
                {
                    "version": 1,
                    "roles": {
                        "implementer": {
                            "role_treatment": row["id"],
                            "requires": [],
                        }
                    },
                },
            )

    def test_same_harness_model_with_different_roles_are_distinct_receipt_units(
        self,
    ) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.certification import (
            CertificationReceipt,
            ExecutableIdentity,
        )
        from loopstrap_core.harness import RoleTreatment
        from support import load_contract

        planner = RoleTreatment.from_dict(role_treatment(role="planner"))
        subagent = RoleTreatment.from_dict(
            role_treatment(role="planning-subagent")
        )
        self.assertNotEqual(
            planner.static_identity_digest(), subagent.static_identity_digest()
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            executable = root / "wrapper"
            executable.write_bytes(b"wrapper-v1\n")
            identity = ExecutableIdentity.observe(executable, version="v1")
            artifacts = ArtifactStore(root / "artifacts")
            evidence_ref = artifacts.put_bytes(b"PASS", media_type="text/plain")
            receipts = [
                CertificationReceipt.issue(
                    role_treatment=item,
                    executables=(identity,),
                    contract_digest=load_contract().digest,
                    run_id=f"cert-{item.role}",
                    layer_results={
                        "mechanical": "PASS",
                        "inference": "PASS",
                        "loopstrap": "PASS",
                    },
                    evidence_refs=(evidence_ref,),
                    report_ref=None,
                    issued_at="2026-07-23T00:00:00Z",
                )
                for item in (planner, subagent)
            ]
            self.assertNotEqual(
                receipts[0].role_treatment_identity_digest,
                receipts[1].role_treatment_identity_digest,
            )
