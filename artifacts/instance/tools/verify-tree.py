#!/usr/bin/env python3
"""Verify Loopstrap hashes, completeness, path safety, links, and file modes."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

HASH_LINE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
RUNTIME_PREFIXES = (
    "repos/",
    ".worktrees/",
    "xor/",
    "scratch/",
)


def safe_relative(raw: str) -> str:
    rel = raw[2:] if raw.startswith("./") else raw
    posix = PurePosixPath(rel)
    if not rel or posix.is_absolute() or ".." in posix.parts or "." in posix.parts:
        raise ValueError(f"unsafe path: {raw!r}")
    return posix.as_posix()


def read_manifest(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = HASH_LINE.fullmatch(line)
        if not match:
            raise ValueError(f"{path.name}:{number}: malformed sha256sum row")
        digest, raw = match.groups()
        rel = safe_relative(raw)
        if rel in rows:
            raise ValueError(f"{path.name}:{number}: duplicate path {rel!r}")
        rows[rel] = digest
    if not rows:
        raise ValueError(f"{path.name}: empty manifest")
    return rows


def read_modes(path: Path) -> dict[str, int]:
    rows: dict[str, int] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            raw_mode, raw_path = line.split("\t", 1)
            mode = int(raw_mode, 8)
        except (ValueError, TypeError):
            raise ValueError(f"{path.name}:{number}: malformed mode row") from None
        rel = safe_relative(raw_path)
        if rel in rows:
            raise ValueError(f"{path.name}:{number}: duplicate path {rel!r}")
        if mode < 0 or mode > 0o7777:
            raise ValueError(f"{path.name}:{number}: invalid mode {raw_mode!r}")
        rows[rel] = mode
    return rows


def is_allowed_runtime_extra(rel: str) -> bool:
    if rel.startswith(RUNTIME_PREFIXES):
        return True
    if rel.startswith("artifacts/reports/"):
        return True
    return False


def inventory(root: Path, allow_runtime: bool) -> tuple[set[str], list[str]]:
    files: set[str] = set()
    errors: list[str] = []
    for base, dirs, names in os.walk(root, followlinks=False):
        base_path = Path(base)
        kept_dirs: list[str] = []
        for name in dirs:
            path = base_path / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                if not (allow_runtime and is_allowed_runtime_extra(rel + "/")):
                    errors.append(f"link not allowed: {rel}")
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in names:
            path = base_path / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                if not (allow_runtime and is_allowed_runtime_extra(rel)):
                    errors.append(f"link not allowed: {rel}")
                continue
            if path.is_file():
                files.add(rel)
            elif not (allow_runtime and is_allowed_runtime_extra(rel)):
                errors.append(f"non-regular entry not allowed: {rel}")
    return files, errors


def verify(root: Path, allow_runtime: bool) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "loopstrap.manifest"
    modes_path = root / "loopstrap.modes"
    if not manifest_path.is_file():
        return ["loopstrap.manifest missing"]
    if not modes_path.is_file():
        return ["loopstrap.modes missing"]
    try:
        manifest = read_manifest(manifest_path)
        modes = read_modes(modes_path)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    files, inventory_errors = inventory(root, allow_runtime)
    errors.extend(inventory_errors)
    static_files = {
        rel
        for rel in files
        if rel != "loopstrap.manifest"
        and not (allow_runtime and rel not in manifest and is_allowed_runtime_extra(rel))
    }
    manifest_files = set(manifest)
    for rel in sorted(manifest_files - static_files):
        errors.append(f"manifest path missing or non-regular: {rel}")
    for rel in sorted(static_files - manifest_files):
        errors.append(f"unlisted static file: {rel}")

    if set(modes) != manifest_files:
        for rel in sorted(manifest_files - set(modes)):
            errors.append(f"mode row missing: {rel}")
        for rel in sorted(set(modes) - manifest_files):
            errors.append(f"mode row not manifested: {rel}")

    for rel, expected_hash in sorted(manifest.items()):
        path = root / rel
        if not path.is_file() or path.is_symlink():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected_hash:
            errors.append(f"hash mismatch: {rel}")
        expected_mode = modes.get(rel)
        if expected_mode is not None:
            actual_mode = stat.S_IMODE(path.stat().st_mode)
            if actual_mode != expected_mode:
                errors.append(
                    f"mode mismatch: {rel} expected {expected_mode:04o}, got {actual_mode:04o}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument(
        "--allow-runtime",
        action="store_true",
        help="permit unmanifested mutable runtime paths in an installed tree",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors = verify(root, args.allow_runtime)
    if errors:
        for error in errors:
            print(f"VERIFY FAIL: {error}", file=sys.stderr)
        return 1
    print("TREE VERIFIED — hashes, exhaustive paths, regular-file types, and modes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
