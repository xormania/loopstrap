#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> int:
    errors: list[str] = []
    expected: set[str] = set()
    for line in (HERE / "FROZEN.sha256").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, relative = line.split("  ", 1)
        expected.add(relative)
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"drift: {relative}")
    actual = {
        "tests/active/claims.toml",
        "tests/active/map.tsv",
        "tests/active/run.py",
        "tests/active/test_active_surface.py",
        "tests/active/verify_freeze.py",
    }
    if actual != expected:
        errors.append(f"inventory mismatch: missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
    if errors:
        for error in errors:
            print(f"ACTIVE FREEZE FAILURE: {error}", file=sys.stderr)
        return 1
    print(f"ACTIVE ACCEPTANCE FREEZE VERIFIED — {len(expected)} inputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
