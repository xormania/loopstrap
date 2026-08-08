#!/usr/bin/env python3
"""Regenerate a frozen suite's FROZEN.sha256, whichever shape that suite uses.

Six suites are pinned by hash, and they do not agree on how the file list is
declared:

    acceptance, active                  no INVENTORY — the manifest IS the list
    certification, integration,
    readiness, telemetry                INVENTORY in verify_freeze.py

So regenerating one has been a hand-rolled Python one-liner, written afresh per
revision, with a different shape depending on the suite. That is a recurring
chance to get it wrong for no benefit, and it has been taken.

For an INVENTORY suite the file list is authored and the manifest is derived, so
adding a frozen input means editing INVENTORY. For the others the manifest is
itself the authored list, which means a NEW file in the suite is silent — nothing
declares it and nothing misses it. This reports that case loudly rather than
quietly rehashing what happens to be listed.

    freeze-suite.py <suite> [--check]

Exit 0 written or already current, 1 drift found under --check, 2 the suite could
not be read.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import sys


SUITES = Path("tests")
SKIP_NAMES = frozenset({"__pycache__", "FROZEN.sha256"})


def declared_inventory(verifier: Path) -> set[str] | None:
    """INVENTORY from a suite's verify_freeze.py, or None when it declares none.

    Parsed rather than imported: importing runs module-level code, and a verifier
    whose import has a side effect would make regeneration depend on the state it
    is about to rewrite.
    """
    tree = ast.parse(verifier.read_text(encoding="utf-8"), filename=str(verifier))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "INVENTORY" not in names:
            continue
        try:
            return {str(item) for item in ast.literal_eval(node.value)}
        except ValueError:
            return None
    return None


def manifest_paths(manifest: Path) -> list[str]:
    return [
        line.split(None, 1)[1].strip()
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def present_files(root: Path, suite: Path) -> set[str]:
    found: set[str] = set()
    for path in sorted(suite.rglob("*")):
        if any(part in SKIP_NAMES for part in path.parts) or path.name in SKIP_NAMES:
            continue
        if path.is_file() and not path.name.startswith("REVISION-"):
            found.add(str(path.relative_to(root)))
    return found


def render(root: Path, paths: list[str]) -> str:
    lines = []
    for relative in sorted(paths):
        target = root / relative
        if not target.is_file():
            raise FileNotFoundError(relative)
        lines.append(f"{hashlib.sha256(target.read_bytes()).hexdigest()}  {relative}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", help="suite name under tests/, e.g. readiness")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true", help="report drift, write nothing")
    args = parser.parse_args()

    root = args.root.resolve()
    suite = root / SUITES / args.suite
    manifest = suite / "FROZEN.sha256"
    verifier = suite / "verify_freeze.py"
    if not manifest.is_file() or not verifier.is_file():
        print(f"  {args.suite}: not a frozen suite (need FROZEN.sha256 and verify_freeze.py)",
              file=sys.stderr)
        return 2

    inventory = declared_inventory(verifier)
    listed = manifest_paths(manifest)

    if inventory is not None:
        paths, source = sorted(inventory), "INVENTORY in verify_freeze.py"
        missing = sorted(set(listed) - inventory)
        extra = sorted(inventory - set(listed))
        for relative in missing:
            print(f"  manifest lists a path INVENTORY does not declare: {relative}")
        for relative in extra:
            print(f"  INVENTORY declares a path the manifest omits: {relative}")
    else:
        paths, source = sorted(listed), "the manifest itself (no INVENTORY)"
        # Nothing declares the list, so a new file is invisible. Say so, and
        # fail: both suites of this shape currently list every non-revision file
        # they contain, so this cannot fire on a tree that is already correct,
        # and the remedy is one of two obvious edits (L48).
        unlisted = sorted(present_files(root, suite) - set(listed))
        for relative in unlisted:
            print(f"  PRESENT BUT NOT FROZEN: {relative}")
        if unlisted:
            print("  This suite declares no INVENTORY, so nothing else would catch that.")
            print("  Either freeze it — add the path to FROZEN.sha256 and regenerate —")
            print("  or remove it from the suite. Both reach green; leaving it does not.")
            return 1

    try:
        rendered = render(root, paths)
    except FileNotFoundError as exc:
        print(f"  declared path does not exist: {exc}", file=sys.stderr)
        return 2

    current = manifest.read_text(encoding="utf-8")
    if rendered == current:
        print(f"  {args.suite}: already current — {len(paths)} inputs, from {source}")
        return 0
    if args.check:
        print(f"  {args.suite}: DRIFTED — {len(paths)} inputs, from {source}")
        print("  Run without --check to regenerate, then reseal.")
        return 1

    manifest.write_text(rendered, encoding="utf-8")
    print(f"  {args.suite}: regenerated — {len(paths)} inputs, from {source}")
    print("  Reseal: the manifest is a sealed file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
