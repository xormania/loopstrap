#!/usr/bin/env python3
"""Parse every shell/Python source and every executable entry point, read-only."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def pinned_binaries() -> dict[Path, str]:
    path = ROOT / "config" / "cue-tool.v1.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        relative = Path(value["binary_path"])
        digest = value["binary_sha256"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("pinned executable configuration is invalid") from exc
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not isinstance(digest, str)
        or len(digest) != 64
    ):
        raise ValueError("pinned executable path or digest is invalid")
    return {ROOT / relative: digest}


def main() -> int:
    shell: set[Path] = set()
    python: set[Path] = set()
    external = pinned_binaries()
    seen_external: set[Path] = set()
    unknown_executables: list[Path] = []
    for base, dirs, names in os.walk(ROOT, followlinks=False):
        base_path = Path(base)
        dirs[:] = [name for name in dirs if name != ".git" and not (base_path / name).is_symlink()]
        for name in names:
            path = base_path / name
            if path.is_symlink() or not path.is_file():
                continue
            first = path.open("rb").readline(256)
            executable = bool(stat.S_IMODE(path.stat().st_mode) & 0o111)
            if path.suffix == ".sh" or (first.startswith(b"#!") and b"sh" in first):
                shell.add(path)
            elif path.suffix == ".py" or (first.startswith(b"#!") and b"python" in first):
                python.add(path)
            elif executable:
                expected = external.get(path)
                if expected is None:
                    unknown_executables.append(path)
                elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    unknown_executables.append(path)
                else:
                    seen_external.add(path)

    failures = 0
    for path in sorted(shell):
        result = subprocess.run(
            ["bash", "-n", str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode:
            first_error = (result.stderr or result.stdout).splitlines()[0]
            print(f"  ✗ SYNTAX {path.relative_to(ROOT)}\n     {first_error}")
            failures += 1
    for path in sorted(python):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            print(f"  ✗ SYNTAX {path.relative_to(ROOT)}\n     {exc}")
            failures += 1
    for path in sorted(unknown_executables):
        print(f"  ✗ ENTRYPOINT {path.relative_to(ROOT)} has no recognized shell/Python shebang")
        failures += 1
    missing_external = set(external) - seen_external
    for path in sorted(missing_external):
        print(f"  ✗ PINNED EXECUTABLE {path.relative_to(ROOT)} is absent or has the wrong digest")
        failures += 1

    count = len(shell) + len(python) + len(unknown_executables) + len(seen_external)
    if failures:
        print(f"SYNTAX: {failures} failure(s) across {count} inspected entry points/sources.")
        return 1
    print(
        f"SYNTAX CLEAN — {len(shell)} shell + {len(python)} Python sources; "
        f"{len(seen_external)} pinned binary; all executable entry points classified; "
        "source tree untouched."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
