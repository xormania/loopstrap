#!/usr/bin/env python3
"""Run every gate, then build a pull request body from what they actually said.

The gates are cheap — seal, verify and contract-check together cost about a third
of a second, and the battery about fifty. The expensive part has always been the
clerical work around them: capture three command outputs verbatim, paste each
into the right fence, check the body for disclosure, push, open. Eight manual
steps per change, and in one day of doing it by hand the two failures were both
clerical:

  - a pull request body that was the commit message, so it carried no evidence
    section at all and CI refused it, twice;
  - evidence that went stale when a branch merged another, describing a tree that
    no longer existed.

Neither was a judgement error. Both are impossible here, because the evidence is
transcribed from the run rather than remembered.

WHAT THIS DOES NOT DO: write the argument. `## What this changes, and why` and
`## What breaks if this is wrong` are left exactly as the template has them, for
a person to fill. The evidence check exists to document work and to filter
contributions that describe work rather than do it; a tool that also wrote the
prose would defeat the half of that which matters. It fills evidence. It never
fills argument.

    ship.py                    run the gates, write the body, print the path
    ship.py --gates-only       run the gates and stop
    ship.py --create           also open the pull request (needs a clean tree)

Exit 0 all green, 1 a gate failed or the tree is dirty, 2 something could not be
run at all.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


TEMPLATE = Path(".github") / "pull_request_template.md"
PLACEHOLDER = "<<<REPLACE-WITH-REAL-OUTPUT>>>"

GATES = [
    ("seal delta", ["python3", "artifacts/instance/tools/seal-tree.py", "."], True),
    ("tree verification", ["python3", "artifacts/instance/tools/verify-tree.py"], False),
    ("contract gate", ["bash", "artifacts/instance/tools/contract-check.sh"], True),
    ("battery", ["bash", "tests/battery.sh"], True),
]


def run(command: list[str], root: Path) -> tuple[int, str]:
    done = subprocess.run(command, cwd=root, capture_output=True, text=True)
    return done.returncode, (done.stdout + done.stderr).rstrip()


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--gates-only", action="store_true")
    parser.add_argument("--create", action="store_true", help="open the pull request too")
    parser.add_argument("--base", default="dev")
    parser.add_argument("--out", type=Path, help="where to write the body (default: a temp file)")
    args = parser.parse_args()
    root = args.root.resolve()

    captured: dict[str, str] = {}
    for label, command, keep in GATES:
        code, output = run(command, root)
        first = output.splitlines()[0] if output else "(no output)"
        last = output.splitlines()[-1] if output else ""
        print(f"  {label:20} {'ok ' if code == 0 else 'RED'}  {last or first}")
        if code != 0:
            print(f"\n{output}\n", file=sys.stderr)
            print(f"  STOPPED at {label}. Nothing was written.", file=sys.stderr)
            print("  A gate that refuses correct work is the defect, not the work (L48).",
                  file=sys.stderr)
            return 1
        if keep:
            captured[label] = output

    # Sealing rewrites the manifest, so a delta means there is something to commit.
    dirty = git(root, "status", "--porcelain")
    if dirty:
        print(f"\n  {len(dirty.splitlines())} uncommitted path(s). The gates passed against the")
        print("  working tree, so commit before the evidence describes anything shareable:")
        for line in dirty.splitlines()[:6]:
            print(f"    {line}")
        if args.create:
            print("  Refusing --create with a dirty tree.", file=sys.stderr)
            return 1

    if args.gates_only:
        return 0

    template = (root / TEMPLATE).read_text(encoding="utf-8")
    body = template
    for label, _, keep in GATES:
        if not keep:
            continue
        if PLACEHOLDER not in body:
            print("  template has fewer evidence blocks than gates — not guessing",
                  file=sys.stderr)
            return 2
        body = body.replace(PLACEHOLDER, captured[label], 1)

    remaining = body.count(PLACEHOLDER)
    out = args.out or (root / ".git" / "ship-body.md")
    out.write_text(body, encoding="utf-8")

    code, output = run(
        ["python3", "artifacts/instance/tools/publication-check.py", "--file", str(out)], root
    )
    print(f"  {'publication':20} {'ok ' if code == 0 else 'RED'}  {output.splitlines()[-1]}")
    if code != 0:
        print("  Body written but NOT publishable. Fix it before opening.", file=sys.stderr)
        return 1

    print(f"\n  body: {out}")
    print(f"  Three evidence blocks filled from this run. {remaining} placeholder(s) left —")
    print("  the argument sections and red-before-green are yours; this tool does not")
    print("  write those, deliberately.")

    if args.create:
        branch = git(root, "branch", "--show-current")
        code, output = run(
            ["gh", "pr", "create", "--base", args.base, "--head", branch, "--body-file", str(out)],
            root,
        )
        print(f"\n{output}")
        return 0 if code == 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
