#!/usr/bin/env python3
"""Fold a probe result into config/harness-cli.v1.json.

probe/run.sh writes two files. The markdown is for a human and is never read by
anything here. The JSON enters the system only by satisfying #HarnessSurface in
contract/schema_harness_surface.cue, checked with the pinned CUE binary — the
prompt's example shape is a hint, the CUE definition is the authority.

This records what was probed. It does not decide whether the result is
acceptable: if the probed version disagrees with the profile's pin, that is
C-CLI-003's finding at gate time, not a reason to refuse the evidence. Recording
truth and judging truth are different jobs.

    probe-ingest.py --surface reports/claude-surface.json [--root DIR] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


SCHEMA = Path("contract") / "schema_harness_surface.cue"
TARGET = Path("config") / "harness-cli.v1.json"
DEFINITION = "#HarnessSurface"


def validate(root: Path, surface: Path) -> dict:
    binary = root / "tools" / "cue" / "v0.17.0" / "cue"
    if not binary.is_file():
        raise SystemExit(f"pinned CUE binary absent: {binary}")
    completed = subprocess.run(
        [
            str(binary), "vet",
            str(root / SCHEMA), str(surface),
            "-d", DEFINITION, "-c",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC"},
    )
    if completed.returncode != 0:
        print(f"PROBE REJECTED — {surface} does not satisfy {DEFINITION}", file=sys.stderr)
        print(completed.stderr.strip() or completed.stdout.strip(), file=sys.stderr)
        raise SystemExit(1)
    return json.loads(surface.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    surface = validate(root, args.surface.resolve())
    harness = surface["harness"]

    target = root / TARGET
    document = json.loads(target.read_text(encoding="utf-8"))
    known = document["harnesses"]
    if harness not in known:
        raise SystemExit(
            f"probe reports harness {harness!r}, which has no entry in {TARGET}. "
            "Add the profile first; this tool records surfaces, it does not "
            "invent harnesses."
        )

    before = known[harness]
    probed = any(flag["status"] == "probed" for flag in surface["flags"])
    after = {
        "version": surface["version"],
        # Only a run that actually observed the binary earns "probed". A surface
        # assembled entirely from docs stays declared, and C-CLI-005 keeps
        # deferring, which is the honest outcome.
        "provenance": "probed" if probed else "declared",
        "probed_at": surface["probed_at"],
        "binary_sha256": surface["binary_sha256"],
        "basis": f"probe/run.sh; binary {surface['binary_path'] or 'unknown'}",
        "flags": [
            {"name": flag["name"], "takes_value": flag["takes_value"]}
            for flag in sorted(surface["flags"], key=lambda f: f["name"])
        ],
    }

    print(f"PROBE ACCEPTED — {harness}")
    for field in ("version", "provenance", "probed_at", "binary_sha256"):
        old, new = before.get(field), after[field]
        marker = "  " if old == new else "~ "
        print(f"  {marker}{field:14} {old!r} -> {new!r}")
    old_flags = {flag["name"] for flag in before.get("flags", [])}
    new_flags = {flag["name"] for flag in after["flags"]}
    for name in sorted(new_flags - old_flags):
        print(f"  + flag          {name}")
    for name in sorted(old_flags - new_flags):
        print(f"  - flag          {name}  (no longer declared by the vendor)")
    if not (new_flags ^ old_flags):
        print(f"    flags          unchanged ({len(new_flags)})")

    if args.dry_run:
        print("  dry run — nothing written")
        return 0

    known[harness] = after
    target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {TARGET}")
    print("  next: re-seal, then run the contract gate — a flag the vendor "
          "dropped becomes C-CLI-001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
