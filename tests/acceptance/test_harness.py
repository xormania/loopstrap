from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

from support import certification_authority, digest, treatment


HERE = Path(__file__).resolve().parent
MOCK = HERE / "mock_harness.py"


class RoleTreatmentAcceptance(unittest.TestCase):
    def registry(self, rows=None):
        from loopstrap_core.harness import RoleTreatmentRegistry

        return RoleTreatmentRegistry.from_dict(
            {
                "version": 1,
                "role_treatments": rows
                or [
                    treatment(
                        "codex-sol",
                        role="implementer",
                        harness="codex",
                        model="gpt-5.6-sol",
                        reasoning="ultra",
                        capabilities=("json", "workspace_write"),
                    ),
                    treatment(
                        "claude-fable",
                        role="planner",
                        harness="claude-code",
                        model="fable",
                        reasoning="ultracode",
                        capabilities=("json", "workspace_write"),
                    ),
                    treatment(
                        "grok-build",
                        role="reviewer",
                        harness="grok-build",
                        model="grok-4.5",
                        reasoning="high",
                        capabilities=("json", "workspace_write"),
                    ),
                ],
            }
        )

    def test_role_treatment_identity_contains_complete_effective_unit(self) -> None:
        registry = self.registry()
        row = registry.get("codex-sol").to_dict()
        self.assertEqual(
            {
                "id",
                "role",
                "harness",
                "model_route",
                "reasoning",
                "wrapper",
                "configuration",
                "capabilities",
                "enabled",
                "command",
            },
            set(row),
        )
        self.assertEqual(row["reasoning"]["requested"], "ultra")
        self.assertIn("workspace_write", row["capabilities"])

    def test_role_router_never_silently_falls_back(self) -> None:
        from loopstrap_core.errors import RoleTreatmentUnavailableError
        from loopstrap_core.harness import RoleRouter

        registry = self.registry(
            [
                treatment(
                    "required",
                    role="planner",
                    harness="claude-code",
                    model="fable",
                    reasoning="ultracode",
                    enabled=False,
                ),
                treatment(
                    "tempting-fallback",
                    role="planner",
                    harness="codex",
                    model="gpt-5.6-sol",
                    reasoning="ultra",
                    enabled=True,
                ),
            ]
        )
        router = RoleRouter.from_dict(
            registry,
            {
                "version": 1,
                "roles": {
                    "planner": {"role_treatment": "required"}
                },
            },
        )
        with self.assertRaises(RoleTreatmentUnavailableError) as caught:
            router.resolve("planner", assignments=[])
        self.assertEqual(caught.exception.role_treatment_id, "required")
        self.assertNotIn("tempting-fallback", str(caught.exception))

    def test_independence_requires_different_role_treatment_and_context_lineage(
        self,
    ) -> None:
        from loopstrap_core.errors import IndependenceError, SchemaError
        from loopstrap_core.harness import Assignment, RoleRouter

        registry = self.registry()
        with tempfile.TemporaryDirectory() as raw:
            certs = certification_authority(
                [
                    item.to_dict()
                    for item in registry.role_treatments.values()
                ],
                Path(raw),
            )
            router = RoleRouter.from_dict(
                registry,
                {
                    "version": 1,
                    "roles": {
                        "planner": {
                            "role_treatment": "claude-fable"
                        },
                        "reviewer": {"role_treatment": "grok-build"},
                    },
                    "independence": [
                        {
                            "role": "reviewer",
                            "from_role": "planner",
                            "different_role_treatment": True,
                            "different_context_lineage": True,
                        }
                    ],
                },
                certification_authority=certs,
            )
            prior = [Assignment("planner", "claude-fable", "context-A")]
            selected = router.resolve(
                "reviewer", assignments=prior, context_lineage="context-B"
            )
            self.assertEqual(selected.id, "grok-build")
            with self.assertRaises(IndependenceError):
                router.resolve(
                    "reviewer", assignments=prior, context_lineage="context-A"
                )

            same = self.registry(
                [
                    treatment(
                        "shared",
                        role="planner",
                        harness="claude-code",
                        model="fable",
                        reasoning="ultracode",
                    )
                ]
            )
            with self.assertRaises(SchemaError):
                RoleRouter.from_dict(
                    same,
                    {
                        "version": 1,
                        "roles": {
                            "reviewer": {
                                "role_treatment": "shared"
                            }
                        },
                    },
                )


class HarnessDispatchAcceptance(unittest.TestCase):
    def treatment_for(self, behavior: str):
        from loopstrap_core.harness import RoleTreatment

        return RoleTreatment.from_dict(
            treatment(
                f"mock-{behavior}",
                role="implementer",
                harness="mock",
                model="mock-model",
                reasoning="deterministic",
                command=[sys.executable, str(MOCK), "--behavior", behavior],
                capabilities=("json", "workspace_write"),
            )
        )

    def invocation(self, workspace: Path, *, revision: int = 3):
        from loopstrap_core.harness import Invocation

        return Invocation(
            invocation_id="inv-1",
            run_id="run-1",
            cell_id="root.1",
            cell_revision=revision,
            role="implementer",
            prompt_ref="sha256:" + digest("prompt-v1"),
            context_manifest_ref="sha256:" + digest("context-v1"),
            context_lineage="lineage-A",
            cache_lineage="cache-A",
            workspace=workspace,
            timeout_seconds=2.0,
            max_output_bytes=32_000,
            environment={"SAFE_VALUE": "visible"},
        )

    def test_dispatch_records_exact_role_treatment_attestation_and_unknown_usage(
        self,
    ) -> None:
        from loopstrap_core.harness import HarnessDispatcher

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            os.environ["SUPER_SECRET"] = "must-not-leak"
            try:
                result = HarnessDispatcher().dispatch(
                    self.treatment_for("echo"), self.invocation(workspace)
                )
            finally:
                del os.environ["SUPER_SECRET"]
            self.assertEqual(result.invocation_id, "inv-1")
            self.assertEqual(
                result.requested_role_treatment["model_route"]["selector"],
                "mock-model",
            )
            self.assertEqual(
                result.launch_attestation["observed"]["models"],
                ["mock-model"],
            )
            self.assertEqual(
                result.launch_attestation["sent"]["reasoning_value"],
                "deterministic",
            )
            self.assertEqual(result.cache_lineage, "cache-A")
            self.assertIsNone(result.usage["input_tokens"])
            self.assertIsNone(result.usage["output_tokens"])
            self.assertIsNone(result.usage["cost"])
            self.assertEqual(result.usage["observed_env"], ["SAFE_VALUE"])
            evidence = result.evidence()
            self.assertEqual(evidence["prompt_ref"], "sha256:" + digest("prompt-v1"))
            self.assertEqual(
                evidence["context_manifest_ref"], "sha256:" + digest("context-v1")
            )
            self.assertGreaterEqual(evidence["latency_ms"], 0)

    def test_argument_vector_runs_in_workspace_and_agent_write_stays_there(self) -> None:
        from loopstrap_core.harness import HarnessDispatcher

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workspace = root / "workspace"
            outside = root / "outside"
            workspace.mkdir()
            outside.mkdir()
            HarnessDispatcher().dispatch(self.treatment_for("write"), self.invocation(workspace))
            self.assertEqual(
                (workspace / "agent-output.txt").read_text(encoding="utf-8"),
                "written only in workspace\n",
            )
            self.assertFalse((outside / "agent-output.txt").exists())

    def test_malformed_empty_duplicate_stale_and_config_drift_responses_refuse(self) -> None:
        from loopstrap_core.errors import HarnessProtocolError, StaleResultError
        from loopstrap_core.harness import HarnessDispatcher

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            dispatcher = HarnessDispatcher()
            for behavior in ("malformed", "empty", "duplicate", "mismatch"):
                with self.assertRaises(HarnessProtocolError, msg=behavior):
                    dispatcher.dispatch(
                        self.treatment_for(behavior), self.invocation(workspace)
                    )
            with self.assertRaises(StaleResultError):
                dispatcher.dispatch(self.treatment_for("stale"), self.invocation(workspace))

    def test_timeout_and_output_limit_are_hard_failures(self) -> None:
        from loopstrap_core.errors import HarnessOutputLimitError, HarnessTimeoutError
        from loopstrap_core.harness import HarnessDispatcher

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            slow = self.invocation(workspace)
            slow.timeout_seconds = 0.1
            with self.assertRaises(HarnessTimeoutError):
                HarnessDispatcher().dispatch(self.treatment_for("slow"), slow)
            large = self.invocation(workspace)
            large.max_output_bytes = 1_000
            with self.assertRaises(HarnessOutputLimitError):
                HarnessDispatcher().dispatch(self.treatment_for("large"), large)

    def test_live_execution_requires_explicit_dispatcher_and_call_opt_in(self) -> None:
        from loopstrap_core.errors import LiveHarnessDisabledError
        from loopstrap_core.harness import HarnessDispatcher

        with tempfile.TemporaryDirectory() as raw:
            invocation = self.invocation(Path(raw))
            treatment_row = self.treatment_for("echo")
            with self.assertRaises(LiveHarnessDisabledError):
                HarnessDispatcher(allow_live=False).dispatch(
                    treatment_row, invocation, live=True
                )
            with self.assertRaises(LiveHarnessDisabledError):
                HarnessDispatcher(allow_live=True).dispatch(
                    treatment_row, invocation, live=False, require_live=True
                )
            result = HarnessDispatcher(allow_live=True).dispatch(
                treatment_row, invocation, live=True
            )
            self.assertEqual(result.status, "completed")
