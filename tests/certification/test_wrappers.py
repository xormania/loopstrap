from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from test_role_treatments import role_treatment


class HarnessWrapperAcceptance(unittest.TestCase):
    def request(self, workspace: Path):
        from loopstrap_core.wrappers import WrapperRequest

        prompt = workspace / "prompt.md"
        schema = workspace / "output.schema.json"
        prompt.write_text("Perform the bounded role task.\n", encoding="utf-8")
        schema.write_text('{"type":"object"}\n', encoding="utf-8")
        return WrapperRequest(
            invocation_id="inv-wrapper-1",
            workspace=workspace,
            prompt_file=prompt,
            output_schema_file=schema,
            invocation_overrides={},
        )

    def test_one_contract_compiles_three_harness_native_interfaces(self) -> None:
        from loopstrap_core.harness import RoleTreatment
        from loopstrap_core.wrappers import HarnessWrapperRegistry

        fixtures = {
            "codex": role_treatment(
                role="implementer",
                harness="codex",
                provider="openai",
                selector="gpt-5.6-sol",
                resolved_model="gpt-5.6-sol",
                reasoning_control="model_reasoning_effort",
                reasoning_requested="ultra",
                expected_wire="ultra",
                orchestration="single-agent",
            ),
            "claude-code": role_treatment(),
            "grok-build": role_treatment(
                role="independent-reviewer",
                harness="grok-build",
                provider="xai",
                selector="grok-4.5",
                resolved_model="grok-4.5",
                reasoning_control="effort",
                reasoning_requested="high",
                expected_wire="high",
                orchestration="single-agent",
            ),
        }
        registry = HarnessWrapperRegistry.default()
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            request = self.request(workspace)
            plans = {
                harness: registry.get(harness).compile(
                    RoleTreatment.from_dict(row), request
                )
                for harness, row in fixtures.items()
            }
        self.assertEqual({plan.harness for plan in plans.values()}, set(fixtures))
        self.assertIn("exec", plans["codex"].argv)
        self.assertIn("--json", plans["codex"].argv)
        self.assertIn("--output-schema", plans["codex"].argv)
        self.assertIn("--ignore-user-config", plans["codex"].argv)
        self.assertIn("--strict-config", plans["codex"].argv)
        self.assertIn("model_reasoning_effort=\"ultra\"", plans["codex"].argv)
        self.assertEqual(plans["codex"].environment, {})

        self.assertIn("-p", plans["claude-code"].argv)
        self.assertIn("stream-json", plans["claude-code"].argv)
        self.assertIn("--include-partial-messages", plans["claude-code"].argv)
        self.assertIn("--forward-subagent-text", plans["claude-code"].argv)
        self.assertIn("--strict-mcp-config", plans["claude-code"].argv)

        self.assertIn("--prompt-file", plans["grok-build"].argv)
        self.assertIn("--verbatim", plans["grok-build"].argv)
        self.assertIn("streaming-json", plans["grok-build"].argv)
        self.assertIn("--no-auto-update", plans["grok-build"].argv)
        self.assertIn("--no-memory", plans["grok-build"].argv)
        self.assertEqual(len({plan.argv for plan in plans.values()}), 3)

    def test_wrapper_refuses_hidden_config_and_unapproved_invocation_override(
        self,
    ) -> None:
        from loopstrap_core.errors import HarnessProtocolError
        from loopstrap_core.harness import RoleTreatment
        from loopstrap_core.wrappers import HarnessWrapperRegistry, WrapperRequest

        row = role_treatment(
            role="implementer",
            harness="codex",
            provider="openai",
            selector="gpt-5.6-sol",
            resolved_model="gpt-5.6-sol",
            reasoning_control="model_reasoning_effort",
            reasoning_requested="ultra",
            expected_wire="ultra",
            orchestration="single-agent",
        )
        registry = HarnessWrapperRegistry.default()
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            request = self.request(workspace)
            hidden = deepcopy(row)
            hidden["configuration"]["user_config_policy"] = "inherit"
            with self.assertRaises(HarnessProtocolError):
                registry.get("codex").compile(
                    RoleTreatment.from_dict(hidden), request
                )
            overridden = WrapperRequest(
                invocation_id=request.invocation_id,
                workspace=request.workspace,
                prompt_file=request.prompt_file,
                output_schema_file=request.output_schema_file,
                invocation_overrides={"reasoning": "low"},
            )
            with self.assertRaises(HarnessProtocolError):
                registry.get("codex").compile(
                    RoleTreatment.from_dict(row), overridden
                )

    def test_launch_attestation_separates_requested_sent_and_observed(self) -> None:
        from loopstrap_core.errors import HarnessProtocolError
        from loopstrap_core.harness import RoleTreatment
        from loopstrap_core.wrappers import (
            HarnessWrapperRegistry,
            LaunchAttestation,
        )

        treatment = RoleTreatment.from_dict(
            role_treatment(
                role="implementer",
                harness="codex",
                provider="openai",
                selector="gpt-5.6-sol",
                resolved_model="gpt-5.6-sol",
                reasoning_control="model_reasoning_effort",
                reasoning_requested="ultra",
                expected_wire="ultra",
                orchestration="single-agent",
            )
        )
        with tempfile.TemporaryDirectory() as raw:
            request = self.request(Path(raw))
            plan = HarnessWrapperRegistry.default().get("codex").compile(
                treatment, request
            )
            valid = {
                "schema_version": 1,
                "issuer": "loopstrap-harness-wrapper-v1",
                "invocation_id": request.invocation_id,
                "role_treatment_id": treatment.id,
                "role": treatment.role,
                "harness": treatment.harness,
                "requested_identity_digest": treatment.static_identity_digest(),
                "sent": plan.sent,
                "observed": {
                    "models": ["gpt-5.6-sol"],
                    "reasoning": "ultra",
                    "orchestration": "single-agent",
                    "fallback_detected": False,
                    "hidden_config_detected": False,
                },
                "proof": {
                    "model": "runtime_event",
                    "reasoning": "runtime_event",
                    "configuration": "sanitized_argv_and_digests",
                    "mapping_evidence_ref": None,
                },
                "sanitized_argv": list(plan.argv),
                "configuration_digest": plan.configuration_digest,
                "environment_names": sorted(plan.environment),
            }
            attestation = LaunchAttestation.validate(
                valid, role_treatment=treatment, plan=plan
            )
            self.assertEqual(attestation.sent["reasoning_value"], "ultra")
            self.assertEqual(attestation.observed["models"], ["gpt-5.6-sol"])

            for field in ("fallback_detected", "hidden_config_detected"):
                broken = deepcopy(valid)
                broken["observed"][field] = True
                with self.assertRaises(HarnessProtocolError, msg=field):
                    LaunchAttestation.validate(
                        broken, role_treatment=treatment, plan=plan
                    )
            substituted = deepcopy(valid)
            substituted["observed"]["models"] = ["fallback-model"]
            with self.assertRaises(HarnessProtocolError):
                LaunchAttestation.validate(
                    substituted, role_treatment=treatment, plan=plan
                )
            unproved_reasoning = deepcopy(valid)
            unproved_reasoning["observed"]["reasoning"] = None
            unproved_reasoning["proof"]["reasoning"] = "self_report"
            unproved_reasoning["proof"]["mapping_evidence_ref"] = (
                "sha256:" + ("0" * 64)
            )
            with self.assertRaises(HarnessProtocolError):
                LaunchAttestation.validate(
                    unproved_reasoning,
                    role_treatment=treatment,
                    plan=plan,
                )
            missing_reasoning = deepcopy(valid)
            missing_reasoning["observed"]["reasoning"] = None
            missing_reasoning["proof"]["reasoning"] = "certified_binary_mapping"
            with self.assertRaises(HarnessProtocolError):
                LaunchAttestation.validate(
                    missing_reasoning,
                    role_treatment=treatment,
                    plan=plan,
                )
