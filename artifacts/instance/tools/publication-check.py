#!/usr/bin/env python3
"""Check text or files for references to work that is not this project.

Everything pushed here is public and permanent. This is the floor: a mechanical
scan against a denylist of terms that must never appear publicly.

The denylist cannot live in this repository, because the list IS the disclosure.
It lives in proj/private-terms.txt, which is gitignored and excluded from the
seal at root. That also means CI cannot run this — the runner is public and the
denylist is not. It is a local preflight, deliberately.

    publication-check.py --stdin
    publication-check.py --file MESSAGE
    publication-check.py --paths probe/ skills/
    git diff --cached | publication-check.py --stdin

Exit 0 clean, 1 on a match, 2 when the denylist is missing or unreadable.

A missing denylist is exit 2, never exit 0. "I could not check" and "I checked
and it was clean" are different answers, and conflating them is how a check
becomes decorative.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


DENYLIST = Path("proj") / "private-terms.txt"
SKIP_DIRS = {".git", "__pycache__", "proj", "node_modules"}
SKIP_SUFFIXES = {".png", ".jpg", ".gif", ".pdf", ".zip", ".gz", ".tar", ".ico"}


def load_terms(root: Path) -> list[str]:
    path = root / DENYLIST
    if not path.is_file():
        print(
            f"PUBLICATION CHECK UNAVAILABLE — no denylist at {path}\n"
            f"  Create it, one term per line. It is gitignored and unsealed.\n"
            f"  Not checking is not the same as checking clean.",
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
    args = parser.parse_args()

    terms = load_terms(args.root.resolve())
    hits: list[tuple[str, int, str, str]] = []

    if args.stdin:
        hits += scan(sys.stdin.read(), terms, "<stdin>")
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
