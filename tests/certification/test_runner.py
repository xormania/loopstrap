from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from support import treatment


class CertificationRunnerAcceptance(unittest.TestCase):
    def test_three_adapters_share_contract_not_commands(self) -> None:
        from loopstrap_core.certification import VendorAdapterRegistry

        registry = VendorAdapterRegistry.default()
        adapters = [registry.get(name) for name in ("codex", "claude-code", "grok-build")]
        self.assertEqual({item.harness for item in adapters}, {"codex", "claude-code", "grok-build"})
        obligation_sets = {tuple(item.obligation_ids) for item in adapters}
        self.assertEqual(len(obligation_sets), 1)
        commands = {item.discovery_commands("vendor-cli") for item in adapters}
        self.assertEqual(len(commands), 3)

    def test_workspace_is_private_unique_and_neutral(self) -> None:
        from loopstrap_core.certification import CertificationRunner

        with tempfile.TemporaryDirectory() as raw:
            runner = CertificationRunner(Path(raw))
            first = runner.prepare_workspace("codex")
            second = runner.prepare_workspace("codex")
            self.assertNotEqual(first.root, second.root)
            self.assertEqual(first.root.stat().st_mode & 0o777, 0o700)
            self.assertTrue(first.probe_repo.joinpath(".git").is_dir())
            outside = __import__("subprocess").run(
                ["git", "-C", str(first.root), "rev-parse", "--show-toplevel"],
                stdout=__import__("subprocess").PIPE,
                stderr=__import__("subprocess").PIPE,
                check=False,
            )
            self.assertNotEqual(outside.returncode, 0)

    def test_environment_is_allowlisted_and_secret_safe(self) -> None:
        from loopstrap_core.certification import CertificationRunner
        from loopstrap_core.errors import SensitiveDataError

        with tempfile.TemporaryDirectory() as raw:
            runner = CertificationRunner(Path(raw))
            environment, evidence = runner.environment(
                {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_TOKEN": "probe123"},
                allowed_names={"PATH"},
                secret_names={"PROBE_TOKEN"},
            )
            self.assertEqual(environment["PROBE_TOKEN"], "probe123")
            self.assertNotIn("probe123", json.dumps(evidence))
            self.assertEqual(evidence["secret_names"], ["PROBE_TOKEN"])
            with self.assertRaises(SensitiveDataError):
                runner.environment(
                    {"UNDECLARED": "value"},
                    allowed_names=set(),
                    secret_names=set(),
                )

    def test_probe_receipt_is_machine_owned_primary_evidence(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.certification import CertificationRunner, ProbeSpec

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runner = CertificationRunner(root)
            workspace = runner.prepare_workspace("codex")
            artifacts = ArtifactStore(root / "artifacts")
            result = runner.run_probe(
                workspace=workspace,
                artifacts=artifacts,
                executable=Path(os.environ.get("PYTHON", os.sys.executable)),
                spec=ProbeSpec(
                    check_id="version",
                    argv=("-c", "import sys; print('v1'); print('note', file=sys.stderr)"),
                    timeout_seconds=5,
                    max_output_bytes=4096,
                ),
                environment={},
            )
            self.assertEqual(result.status, "PASS")
            self.assertEqual(result.issuer, "loopstrap-certifier-v1")
            self.assertEqual(artifacts.get_bytes(result.stdout_ref), b"v1\n")
            self.assertEqual(artifacts.get_bytes(result.stderr_ref), b"note\n")
            self.assertNotIn("report", result.to_dict())

    def test_external_state_guard_restores_exact_baseline(self) -> None:
        from loopstrap_core.certification import ExternalStateGuard

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "config.json"
            target.write_text('{"baseline":true}\n', encoding="utf-8")
            baseline = target.read_bytes()
            with ExternalStateGuard((target,)) as guard:
                target.write_text('{"changed":true}\n', encoding="utf-8")
                guard.restore()
            self.assertEqual(target.read_bytes(), baseline)
            self.assertTrue(guard.restoration_verified)
