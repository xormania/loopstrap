#!/usr/bin/env python3
"""Verify that preimplementation acceptance inputs have not drifted."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "FROZEN.sha256"


def main() -> int:
    errors: list[str] = []
    expected_paths: set[str] = set()
    for line_number, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        try:
            expected, relative = line.split("  ", 1)
        except ValueError:
            errors.append(f"malformed manifest line {line_number}")
            continue
        expected_paths.add(relative)
        path = HERE.parents[1] / relative
        if not path.is_file():
            errors.append(f"missing frozen input: {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"drift: {relative}")
    actual_paths = {
        str(path.relative_to(HERE.parents[1]))
        for path in HERE.glob("test_*.py")
    }
    actual_paths.update(
        {
            "tests/acceptance/claims.toml",
            "tests/acceptance/map.tsv",
            "tests/acceptance/mock_harness.py",
            "tests/acceptance/run.py",
            "tests/acceptance/support.py",
            "tests/acceptance/verify_freeze.py",
        }
    )
    extras = sorted(actual_paths - expected_paths)
    if extras:
        errors.append(f"unfrozen acceptance inputs: {extras}")
    if errors:
        for error in errors:
            print(f"FREEZE FAILURE: {error}", file=sys.stderr)
        return 1
    print(f"ACCEPTANCE FREEZE VERIFIED — {len(expected_paths)} inputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
