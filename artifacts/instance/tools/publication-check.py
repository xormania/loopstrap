#!/usr/bin/env python3
"""Check text or files for references the operator has not chosen to publish.

Anything an agent pushes, opens, comments or publishes on an operator's behalf is
public and usually permanent. This is the mechanical floor: a scan against a
denylist of terms that must not appear outside the machine.

The denylist cannot live in the repository being checked, because the list IS the
disclosure. It is supplied by the operator, found in this order:

    --denylist PATH
    $PUBLICATION_DENYLIST
    ./proj/private-terms.txt          (untracked working notes)
    ./.private-terms                  (untracked)
    ~/.config/publication-denylist    (per-operator, all repositories)

The per-operator location is usually the right one: the same names must not leak
from any repository, so the list should outlive any single project.

Because the denylist is private, hosted CI generally cannot run this. It is a
local preflight by design.

    publication-check.py --stdin
    publication-check.py --file MESSAGE
    publication-check.py --paths src/ docs/
    git diff --cached | publication-check.py --stdin

Exit 0 clean, 1 on a match, 2 when no denylist is available.

A missing denylist is exit 2, never exit 0. "I could not check" and "I checked
and it was clean" are different answers, and conflating them is how a check
becomes decorative.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


import os

DENYLIST_CANDIDATES = (
    Path("proj") / "private-terms.txt",
    Path(".private-terms"),
)
SKIP_DIRS = {".git", "__pycache__", "proj", "node_modules", ".venv", "vendor"}
SKIP_SUFFIXES = {".png", ".jpg", ".gif", ".pdf", ".zip", ".gz", ".tar", ".ico"}


def find_denylist(root: Path, explicit: Path | None) -> Path | None:
    if explicit:
        return explicit if explicit.is_file() else None
    from_env = os.environ.get("PUBLICATION_DENYLIST")
    if from_env and Path(from_env).is_file():
        return Path(from_env)
    for candidate in DENYLIST_CANDIDATES:
        if (root / candidate).is_file():
            return root / candidate
    shared = Path.home() / ".config" / "publication-denylist"
    return shared if shared.is_file() else None


def load_terms(root: Path, explicit: Path | None = None) -> list[str]:
    path = find_denylist(root, explicit)
    if path is None:
        print(
            "PUBLICATION CHECK UNAVAILABLE — no denylist found\n"
            "  Looked at: --denylist, $PUBLICATION_DENYLIST, ./proj/private-terms.txt,\n"
            "             ./.private-terms, ~/.config/publication-denylist\n"
            "  One term per line. Keep it untracked — the list is itself the disclosure.\n"
            "  Not checking is not the same as checking clean.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    terms = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not terms:
        print(f"PUBLICATION CHECK UNAVAILABLE — {path} declares no terms", file=sys.stderr)
        raise SystemExit(2)
    return terms


def looks_like_diff(text: str) -> bool:
    return any(
        line.startswith(("diff --git ", "@@ ", "--- a/", "+++ b/"))
        for line in text.splitlines()[:40]
    )


def added_lines_only(text: str) -> str:
    """Keep only what a diff ADDS.

    Removing a reference puts that reference in the diff as a deleted line, so
    scanning a raw diff flags the very act of fixing the problem. Only additions
    can leak; deletions are the cure.
    """
    kept: list[str] = []
    for line in text.splitlines():
        if line.startswith("+++"):
            kept.append("")
        elif line.startswith("+"):
            kept.append(line[1:])
        else:
            kept.append("")
    return "\n".join(kept)


def scan(text: str, terms: list[str], label: str) -> list[tuple[str, int, str, str]]:
    hits: list[tuple[str, int, str, str]] = []
    patterns = [(term, re.compile(re.escape(term), re.IGNORECASE)) for term in terms]
    for number, line in enumerate(text.splitlines(), 1):
        for term, pattern in patterns:
            if pattern.search(line):
                hits.append((label, number, term, line.strip()[:100]))
    return hits


def walk(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for target in paths:
        if target.is_file():
            found.append(target)
            continue
        for path in sorted(target.rglob("*")):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() not in SKIP_SUFFIXES:
                found.append(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--paths", nargs="*", type=Path, default=[])
    parser.add_argument("--denylist", type=Path)
    args = parser.parse_args()

    terms = load_terms(args.root.resolve(), args.denylist)
    hits: list[tuple[str, int, str, str]] = []

    if args.stdin:
        text = sys.stdin.read()
        if looks_like_diff(text):
            text = added_lines_only(text)
            print("  (input is a diff — scanning added lines only)", file=sys.stderr)
        hits += scan(text, terms, "<stdin>")
    if args.file:
        hits += scan(args.file.read_text(encoding="utf-8", errors="replace"), terms, str(args.file))
    for path in walk(args.paths):
        try:
            hits += scan(path.read_text(encoding="utf-8", errors="replace"), terms, str(path))
        except OSError:
            continue

    if not (args.stdin or args.file or args.paths):
        parser.error("give --stdin, --file, or --paths")

    if hits:
        print(f"PUBLICATION CHECK FAILED — {len(hits)} reference(s)", file=sys.stderr)
        for label, number, term, line in hits:
            print(f"  {label}:{number}  [{term}]  {line}", file=sys.stderr)
        print(
            "\nRemove the reference. If a sentence exists only to say a prior "
            "project did something, delete the sentence — the change should "
            "justify itself on its own terms.\n"
            "This check cannot catch a description that avoids every term. Reread "
            "your own prose for that.",
            file=sys.stderr,
        )
        return 1

    print(f"PUBLICATION CHECK OK — {len(terms)} term(s) checked, no references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
