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


def diff_sections(text: str) -> dict[str, tuple[list[str], list[str]]]:
    """Split a unified diff into {path: (added lines, removed lines)}."""
    sections: dict[str, tuple[list[str], list[str]]] = {}
    path = "<stdin>"
    for line in text.splitlines():
        if line.startswith("+++ "):
            named = line[4:].strip().split("\t")[0]
            path = named[2:] if named.startswith(("a/", "b/")) else named
            sections.setdefault(path, ([], []))
            continue
        if line.startswith(("--- ", "diff --git ", "@@", "index ", "similarity ",
                            "rename ", "new file", "deleted file", "old mode",
                            "new mode", "Binary files")):
            continue
        if line.startswith("+"):
            sections.setdefault(path, ([], []))[0].append(line[1:])
        elif line.startswith("-"):
            sections.setdefault(path, ([], []))[1].append(line[1:])
    return sections


def scan_diff(text: str, terms: list[str]) -> list[tuple[str, int, str, str]]:
    """Flag only what a diff genuinely INTRODUCES.

    Scanning added lines alone flags the act of fixing the problem, because
    removing a reference puts it in the diff as a deleted line. Scanning added
    lines alone ALSO flags every edit to a line that already carried the term —
    a path rewrite, a reflow, a rename — which is the common case and the one
    that trains people to reach for --no-verify.

    So the unit is the net count per file per term: if a file removes as many
    occurrences of a term as it adds, it has introduced nothing. Per file, not
    globally, so deleting a mention in one file cannot license a new one
    somewhere else.

    When there IS an excess this reports every added line carrying the term and
    says how many are new, because term matching cannot identify WHICH addition
    is the new one. Naming them all and stating the arithmetic is honest; naming
    one would be a guess.
    """
    hits: list[tuple[str, int, str, str]] = []
    for path, (added, removed) in sorted(diff_sections(text).items()):
        for term in terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            carrying = [line for line in added if pattern.search(line)]
            gained = sum(len(pattern.findall(line)) for line in added)
            lost = sum(len(pattern.findall(line)) for line in removed)
            if gained - lost <= 0:
                continue
            label = f"{path} (+{gained} -{lost}, {gained - lost} new)"
            for number, line in enumerate(carrying, 1):
                hits.append((label, number, term, line.strip()[:100]))
    return hits


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
            print("  (input is a diff — counting net introductions per file)", file=sys.stderr)
            hits += scan_diff(text, terms)
        else:
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
