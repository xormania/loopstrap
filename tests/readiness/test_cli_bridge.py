"""The operator CLI is the kernel's entire external surface, and three of its
five subcommands cross the CUE-to-Python bridge. Nothing exercised that bridge
before this suite: spec-check, plan-check and acceptance-check had no witness,
and a divergence between a closed CUE definition and a Python exact-field set
left acceptance-check unable to accept any input at all while the battery
stayed green.

Every assertion here is POSITIVE. A refusal-shaped test cannot detect a command
that refuses everything, which is precisely the state that went unnoticed.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import unittest

from support import CUE_BINARY, CUE_PIN, CUE_SCHEMA, PROJECT_FIXTURE


FIXTURES = Path(__file__).resolve().parent / "fixtures"
DIGEST_PREFIX = "sha256:"


def run_cli(*argv: str) -> tuple[int, str]:
    """Drive the real entry point in-process. No subprocess, so no PATH,
    interpreter-discovery or scheduling variability enters the verdict."""
    from loopstrap_core.cli import main

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = main(list(argv))
    return code, stream.getvalue()


def cue_arguments() -> list[str]:
    return [
        "--cue",
        str(CUE_BINARY),
        "--pin",
        str(CUE_PIN),
        "--schema",
        str(CUE_SCHEMA),
    ]


class CLIBridgeReadiness(unittest.TestCase):
    def test_spec_check_compiles_the_project_package_through_the_cli(self) -> None:
        code, output = run_cli(
            "spec-check", "--project", str(PROJECT_FIXTURE), *cue_arguments()
        )
        self.assertEqual(code, 0, output)
        payload = json.loads(output)
        self.assertTrue(payload["specification_digest"].startswith(DIGEST_PREFIX))
        self.assertEqual(len(payload["specification_digest"]), len(DIGEST_PREFIX) + 64)

    def test_plan_check_validates_a_contract_graph_through_the_cli(self) -> None:
        code, output = run_cli(
            "plan-check",
            "--contracts",
            str(FIXTURES / "contract-graph.json"),
            *cue_arguments(),
        )
        self.assertEqual(code, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["cells"], 2)
        self.assertEqual(payload["composites"], 1)
        self.assertEqual(payload["root_composite_id"], "composite.root")
        self.assertTrue(payload["contract_graph_digest"].startswith(DIGEST_PREFIX))

    def test_acceptance_check_accepts_evidence_that_satisfies_its_obligation(
        self,
    ) -> None:
        code, output = run_cli(
            "acceptance-check",
            "--acceptance",
            str(FIXTURES / "acceptance-request.json"),
            *cue_arguments(),
        )
        self.assertEqual(code, 0, output)
        payload = json.loads(output)

        # The positive witness. rc == 0 alone would have caught the schema
        # divergence, which refused with rc == 1; asserting accepted is stronger
        # and catches the next failure too — a command that returns cleanly and
        # still never accepts anything. The suites held 115 refusal-shaped
        # assertions and none of them could observe universal refusal.
        self.assertIs(payload["accepted"], True)
        self.assertEqual(payload["satisfied_obligation_ids"], ["verify.producer"])
        self.assertEqual(payload["qualifying_evidence_ids"], ["evidence.producer.1"])
        self.assertEqual(payload["unsatisfied_obligation_ids"], [])

        # Wire representation, which CUE unification cannot check: an absent
        # list field and an empty list are the same value under the schema, but
        # they are different bytes and therefore different ledger digests.
        self.assertEqual(
            set(payload),
            {
                "id",
                "specification_digest",
                "accepted",
                "satisfied_obligation_ids",
                "unsatisfied_obligation_ids",
                "qualifying_evidence_ids",
                "unresolved_finding_ids",
            },
        )

    def test_acceptance_record_conforms_to_the_shipped_cue_definition(self) -> None:
        code, output = run_cli(
            "acceptance-check",
            "--acceptance",
            str(FIXTURES / "acceptance-request.json"),
            *cue_arguments(),
        )
        self.assertEqual(code, 0, output)

        # Checked against spec/cue/evidence.cue itself — the shipped production
        # schema, not a copy. A test-owned restatement of the same fields could
        # drift from the contract and agree with a wrong implementation.
        with contextlib.ExitStack() as stack:
            import tempfile

            directory = stack.enter_context(tempfile.TemporaryDirectory())
            record = Path(directory) / "record.json"
            record.write_text(output, encoding="utf-8")
            completed = subprocess.run(
                [
                    str(CUE_BINARY),
                    "vet",
                    str(CUE_SCHEMA / "evidence.cue"),
                    str(record),
                    "-d",
                    "#AcceptanceRecord",
                    "-c",
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC"},
            )
        self.assertEqual(
            completed.returncode, 0, completed.stderr or completed.stdout
        )


if __name__ == "__main__":
    unittest.main()
