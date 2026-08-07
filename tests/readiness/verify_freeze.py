#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = HERE / "FROZEN.sha256"
INVENTORY = {
    "tests/readiness/claims.toml",
    "tests/readiness/fixtures/project/contracts.cue",
    "tests/readiness/fixtures/project/cue.mod/module.cue",
    "tests/readiness/fixtures/project/lexicon.cue",
    "tests/readiness/fixtures/project/package.cue",
    "tests/readiness/fixtures/project/realization.cue",
    "tests/readiness/map.tsv",
    "tests/readiness/run.py",
    "tests/readiness/support.py",
    "tests/readiness/test_contracts.py",
    "tests/readiness/test_driver.py",
    "tests/readiness/test_evidence.py",
    "tests/readiness/test_recovery.py",
    "tests/readiness/test_specification.py",
    "tests/readiness/verify_freeze.py",
}


def main() -> int:
    errors: list[str] = []
    expected: set[str] = set()
    for number, line in enumerate(FROZEN.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        try:
            digest, relative = line.split("  ", 1)
        except ValueError:
            errors.append(f"malformed manifest line {number}")
            continue
        expected.add(relative)
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"drift: {relative}")
    if expected != INVENTORY:
        errors.append(
            f"inventory mismatch: missing={sorted(expected-INVENTORY)} "
            f"extra={sorted(INVENTORY-expected)}"
        )
    if errors:
        for error in errors:
            print(f"READINESS FREEZE FAILURE: {error}", file=sys.stderr)
        return 1
    print(f"READINESS FREEZE VERIFIED — {len(expected)} inputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
