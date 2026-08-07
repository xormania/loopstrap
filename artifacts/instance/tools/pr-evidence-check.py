#!/usr/bin/env python3
"""Check that a pull request body carries artifacts of work, not claims about it.

The filter is deliberately narrow. CI runs three commands on the branch and this
compares their real output against what the author pasted. A contributor who ran
the tools has the output in their terminal; one who did not cannot invent it,
because the seal delta and the counts are specific to the diff.

Nothing here judges quality. It only distinguishes "ran the tools" from "wrote a
paragraph that sounds like it".

    pr-evidence-check.py --body-file BODY --seal LINE --contract LINE
                         --battery LINE [--changed FILE ...]

Exit 0 clean, 1 on any missing or mismatched artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


PLACEHOLDERS = ("PASTE THE", "BEFORE (failing):", "AFTER (passing):")
REQUIRED_HEADINGS = (
    "## What this changes, and why",
    "## What breaks if this is wrong",
    "## Evidence",
)
# A change under any of these must show the check failing before it passes.
RED_REQUIRED_PREFIXES = ("loopstrap_core/", "spec/", "contract/", "tests/")


def normalize(text: str) -> str:
    """Collapse whitespace so reflowing a paste is not a failure, but editing is."""
    return re.sub(r"\s+", " ", text).strip()


def contains(body: str, line: str) -> bool:
    return normalize(line) in normalize(body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--seal", required=True, help="the real SEALED/SEAL CHANGED line")
    parser.add_argument("--contract", required=True, help="the real CONTRACT CLEAN line")
    parser.add_argument("--battery", required=True, help="the real N PASS / N FAIL line")
    parser.add_argument("--changed", nargs="*", default=[], help="changed file paths")
    args = parser.parse_args()

    body = args.body_file.read_text(encoding="utf-8")
    problems: list[str] = []

    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            problems.append(f"missing section: {heading}")

    for token in PLACEHOLDERS:
        if token in body:
            problems.append(
                f"template placeholder left in the body: {token!r} — "
                "replace it with real output"
            )

    for label, expected in (
        ("seal delta", args.seal),
        ("contract gate", args.contract),
        ("battery result", args.battery),
    ):
        if not contains(body, expected):
            problems.append(
                f"{label} does not match this branch.\n"
                f"      CI observed: {expected.strip()}\n"
                f"      Paste that line verbatim. If it surprises you, run the "
                f"command locally and read the difference — that difference is "
                f"the review."
            )

    needs_red = any(
        path.startswith(RED_REQUIRED_PREFIXES) for path in args.changed
    )
    if needs_red and "## Red before green" not in body:
        touched = sorted(p for p in args.changed if p.startswith(RED_REQUIRED_PREFIXES))
        problems.append(
            "changes touch "
            + ", ".join(touched[:4])
            + (" and others" if len(touched) > 4 else "")
            + " but the body has no 'Red before green' section. "
            "Show the check failing before it passes: a test never observed to "
            "fail has not been shown to test anything."
        )

    unticked = [
        line.strip()
        for line in body.splitlines()
        if line.strip().startswith("- [ ]")
    ]
    if unticked:
        problems.append(
            f"{len(unticked)} checklist item(s) not ticked: " + unticked[0][6:]
        )

    if problems:
        print("PR EVIDENCE FAILED", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nThis check compares pasted output against CI's own run. It cannot "
            "be satisfied without running the commands.",
            file=sys.stderr,
        )
        return 1

    print("PR EVIDENCE OK — seal, contract and battery output match this branch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
