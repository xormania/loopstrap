from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "config" / "workflow.v1.json"
ROLE_TREATMENTS = ROOT / "config" / "role-treatments.v1.json"
ROLES = ROOT / "config" / "roles.v1.json"


class ActiveConfigurationAcceptance(unittest.TestCase):
    def test_workflow_config_is_versioned_data_accepted_by_production_parser(self) -> None:
        from loopstrap_core.workflow import WorkflowDefinition

        data = json.loads(WORKFLOW.read_text(encoding="utf-8"))
        definition = WorkflowDefinition.from_dict(data)
        self.assertEqual(definition.version, 1)
        self.assertEqual(
            {phase.kind for phase in definition.phases.values()},
            {
                "contract",
                "tests",
                "plan",
                "pre_review",
                "children",
                "implementation",
                "integration",
                "post_review",
                "closed",
                "parked",
            },
        )

    def test_role_treatment_config_is_exact_owner_selection_and_uncertified(self) -> None:
        from loopstrap_core.harness import RoleTreatmentRegistry

        data = json.loads(ROLE_TREATMENTS.read_text(encoding="utf-8"))
        registry = RoleTreatmentRegistry.from_dict(data)
        observed = {
            (
                row.role,
                row.harness,
                row.model_route.provider,
                row.model_route.selector,
                row.reasoning.requested,
                row.enabled,
            )
            for row in registry.role_treatments.values()
        }
        self.assertEqual(
            observed,
            {
                ("planner", "claude-code", "anthropic", "Fable", "ultracode", False),
                (
                    "planning-subagent",
                    "claude-code",
                    "anthropic",
                    "Fable",
                    "ultracode",
                    False,
                ),
                ("implementer", "codex", "openai", "GPT56Sol", "ultra", False),
                (
                    "builder-adversary",
                    "codex",
                    "openai",
                    "GPT56Sol",
                    "ultra",
                    False,
                ),
                (
                    "independent-adversary",
                    "grok-build",
                    "xai",
                    "Grok4.5",
                    "high",
                    False,
                ),
                (
                    "independent-reviewer",
                    "grok-build",
                    "xai",
                    "Grok4.5",
                    "high",
                    False,
                ),
            },
        )

    def test_role_policy_uses_owner_assignments_and_keeps_independence_rules(self) -> None:
        from loopstrap_core.harness import RoleRouter, RoleTreatmentRegistry

        registry = RoleTreatmentRegistry.from_dict(
            json.loads(ROLE_TREATMENTS.read_text(encoding="utf-8"))
        )
        data = json.loads(ROLES.read_text(encoding="utf-8"))
        router = RoleRouter.from_dict(registry, data)
        self.assertEqual(
            set(router.roles),
            {
                "planner",
                "planning-subagent",
                "implementer",
                "builder-adversary",
                "independent-adversary",
                "independent-reviewer",
            },
        )
        self.assertGreaterEqual(len(router.independence), 3)
        self.assertTrue(
            all(rule.different_role_treatment for rule in router.independence)
        )
        self.assertTrue(all(rule.different_context_lineage for rule in router.independence))

    def test_cli_validates_all_configs_without_model_execution(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "loopstrap_core.cli",
                "validate",
                "--workflow",
                str(WORKFLOW),
                "--role-treatments",
                str(ROLE_TREATMENTS),
                "--roles",
                str(ROLES),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["workflow_version"], 1)
        self.assertEqual(payload["role_treatments"], 6)
        self.assertEqual(payload["assigned_roles"], 6)
        self.assertFalse(payload["armed"])

    def test_cli_status_verifies_ledger_and_replays_observed_state(self) -> None:
        from loopstrap_core.ledger import EventLedger

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            ledger = EventLedger(root / "events.jsonl", run_id="run-status")
            ledger.append(
                "e1",
                "cell.created",
                "executor",
                {"cell_id": "root", "phase": "tests", "revision": 1},
            )
            ledger.append(
                "e2",
                "cell.transitioned",
                "executor",
                {"cell_id": "root", "from": "tests", "to": "plan", "revision": 2},
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "loopstrap_core.cli",
                    "status",
                    "--ledger",
                    str(ledger.path),
                    "--run-id",
                    "run-status",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["event_count"], 2)
            self.assertEqual(payload["state"]["cells"]["root"]["phase"], "plan")
            with ledger.path.open("ab") as stream:
                stream.write(b"{partial")
            broken = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "loopstrap_core.cli",
                    "status",
                    "--ledger",
                    str(ledger.path),
                    "--run-id",
                    "run-status",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(broken.returncode, 0)
            self.assertNotIn('"healthy":true', broken.stdout.replace(" ", "").lower())


class ActiveControlSurfaceAcceptance(unittest.TestCase):
    def test_root_instructions_activate_new_kernel_without_legacy_doctrine(self) -> None:
        texts = {
            path.name: path.read_text(encoding="utf-8")
            for path in (ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / "README.md")
        }
        combined = "\n".join(texts.values())
        self.assertIn("loopstrap_core", combined)
        self.assertIn("tests/acceptance", combined)
        self.assertIn("legacy", combined.lower())
        for forbidden in (
            "wrong place (Loopstrap dev lane)",
            "units_per_session",
            "generator_retry_cap",
            "lsp_math",
            "Fable operating contract",
        ):
            self.assertNotIn(forbidden, combined)

    def test_old_launcher_fails_closed_as_unarmed_before_any_vendor_call(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            mock_bin = Path(raw)
            marker = mock_bin / "vendor-called"
            for name in ("codex", "claude", "grok"):
                script = mock_bin / name
                script.write_text(
                    f"#!/usr/bin/env bash\nprintf called > {marker!s}\nexit 0\n",
                    encoding="utf-8",
                )
                script.chmod(0o755)
            result = subprocess.run(
                [str(ROOT / "launch-loop.sh")],
                cwd=ROOT,
                env={"PATH": f"{mock_bin}:/usr/bin:/bin"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("NOT ARMED", result.stderr)
            self.assertIn("governing", result.stderr.lower())
            self.assertFalse(marker.exists())

    def test_consistency_audit_checks_active_kernel_not_legacy_doctrine(self) -> None:
        result = subprocess.run(
            ["bash", "artifacts/instance/tools/audit-consistency.sh"],
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("acceptance freeze", result.stdout.lower())
        self.assertIn("active configuration", result.stdout.lower())
        self.assertIn("kernel source", result.stdout.lower())
        self.assertNotIn("CLAUDE.md = Conductor doctrine", result.stdout)

    def test_battery_has_distinct_core_and_active_acceptance_receipts(self) -> None:
        text = (ROOT / "tests" / "battery.sh").read_text(encoding="utf-8")
        self.assertIn("run_leg acceptance ", text)
        self.assertIn("run_leg active ", text)
        self.assertIn("run_leg certification ", text)
        self.assertIn("acceptance", text.split("REQUIRED=(", 1)[1].split(")", 1)[0])
        self.assertIn("active", text.split("REQUIRED=(", 1)[1].split(")", 1)[0])
        self.assertIn(
            "certification",
            text.split("REQUIRED=(", 1)[1].split(")", 1)[0],
        )

    def test_kernel_has_no_selected_model_member_or_fixed_recursion_literals(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "loopstrap_core").glob("*.py"))
        )
        for forbidden in (
            "lsp_math",
            "GPT56Sol",
            "Fable",
            "Grok4.5",
            "depth cap",
            "depth_cap",
            "child_count",
            "invocation_cap",
            "generator_retry_cap",
        ):
            self.assertNotIn(forbidden, text)
