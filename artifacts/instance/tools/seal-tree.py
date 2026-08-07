#!/usr/bin/env python3
"""Regenerate loopstrap.modes and loopstrap.manifest for a clean source tree."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys

# Version-control metadata and build artifacts are not project content. Sealing
# them makes the manifest churn on every commit and every import. These rules
# must match verify-tree.py exactly, or sealing and verification disagree.
EXCLUDED_NAMES = frozenset({".git", "__pycache__"})
EXCLUDED_SUFFIXES = (".egg-info",)


def is_excluded(name: str) -> bool:
    return name in EXCLUDED_NAMES or name.endswith(EXCLUDED_SUFFIXES)


def regular_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for base, dirs, names in os.walk(root, followlinks=False):
        base_path = Path(base)
        dirs[:] = sorted(
            name
            for name in dirs
            if not is_excluded(name) and not (base_path / name).is_symlink()
        )
        for name in sorted(names):
            path = base_path / name
            if is_excluded(path.name):
                continue
            if path.name == "loopstrap.manifest" or path.is_symlink():
                continue
            if path.is_file():
                result.append(path)
    return sorted(result, key=lambda path: path.relative_to(root).as_posix())


def read_manifest(path: Path) -> dict[str, str]:
    """Previous seal as {relative path: digest}. Absent or malformed reads empty."""
    rows: dict[str, str] = {}
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, separator, rel = line.partition("  ")
        if separator and len(digest) == 64:
            rows[rel] = digest
    return rows


def report(previous: dict[str, str], current: dict[str, str]) -> None:
    """A seal that changes silently is not tamper-evident. Say what moved."""
    if not previous:
        print("  first seal — no prior manifest to compare")
        return
    added = sorted(set(current) - set(previous))
    removed = sorted(set(previous) - set(current))
    changed = sorted(
        rel for rel in set(current) & set(previous) if current[rel] != previous[rel]
    )
    if not (added or removed or changed):
        print("  UNCHANGED — every path and digest matches the previous seal")
        return
    for rel in added:
        print(f"  + added    {rel}")
    for rel in removed:
        print(f"  - removed  {rel}")
    for rel in changed:
        print(f"  ~ changed  {rel}")
    print(
        f"  SEAL CHANGED — {len(added)} added, {len(removed)} removed, "
        f"{len(changed)} content change(s)"
    )


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    modes_path = root / "loopstrap.modes"
    modes_path.touch(mode=0o644, exist_ok=True)
    os.chmod(modes_path, 0o644)

    files = regular_files(root)
    mode_text = "".join(
        f"{stat.S_IMODE(path.stat().st_mode):04o}\t{path.relative_to(root).as_posix()}\n"
        for path in files
    )
    modes_path.write_text(mode_text, encoding="utf-8")

    files = regular_files(root)
    manifest_path = root / "loopstrap.manifest"
    previous = read_manifest(manifest_path)
    current = {
        f"./{path.relative_to(root).as_posix()}": hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in files
    }
    manifest_text = "".join(f"{digest}  {rel}\n" for rel, digest in current.items())
    manifest_path.write_text(manifest_text, encoding="utf-8")
    print(f"SEALED — {len(files)} files with hashes and modes")
    report(previous, current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
