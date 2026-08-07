#!/usr/bin/env python3
"""Rank invariants by whether they have done anything, and name the candidates.

A budget stops the gate growing. It does nothing to ensure the invariants it
holds are the right ones. This supplies the one input to that decision which is
not judgement: has this check ever done anything?

Two kinds, two signals, because firing count is the wrong measure for half:

  detective   earns by firing on a real defect. Counted from gate-firings.jsonl,
              which contract-check.sh appends to whenever a diagnostic is emitted.
              Zero firings after long exposure is evidence against it.

  preventive  earns by being tied to a defect that actually occurred and is now
              unwritable. Recorded once, at creation. Zero firings is the
              INTENDED outcome and says nothing — a preventive invariant that
              works perfectly never fires, and ranking it on firings would delete
              exactly the ones succeeding.

What this cannot do: rank two invariants that both earned their place, or price
contributor friction. Those stay judgement. It removes judgement from the single
question that kept being answered wrong — does this check do anything at all.

    gate-review.py [--root DIR] [--stale-days N]
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys


BUDGET = Path("config") / "gate-budget.v1.json"
FIRINGS = Path("proj") / "gate-firings.jsonl"


def load_firings(root: Path) -> Counter:
    counts: Counter = Counter()
    path = root / FIRINGS
    if not path.is_file():
        return counts
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            counts[json.loads(line)["invariant"]] += 1
        except (ValueError, KeyError):
            continue
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--stale-days", type=int, default=90)
    args = parser.parse_args()
    root = args.root.resolve()

    budget = json.loads((root / BUDGET).read_text(encoding="utf-8"))
    declared = budget.get("invariants", {})
    cap = budget.get("max_invariants", 0)
    firings = load_firings(root)
    today = datetime.now(timezone.utc).date()

    print(f"  {'invariant':16} {'kind':11} {'fired':>5}  {'age':>5}  verdict")
    print(f"  {'-'*16} {'-'*11} {'-'*5}  {'-'*5}  {'-'*40}")

    candidates: list[str] = []
    for name, meta in sorted(declared.items()):
        kind = meta.get("kind", "?")
        fired = firings.get(name, 0)
        try:
            age = (today - date.fromisoformat(meta.get("first_seen", ""))).days
        except ValueError:
            age = -1

        if not meta.get("incident"):
            verdict, mark = "no incident recorded — a guess", True
        elif kind == "preventive":
            verdict, mark = "tied to a real defect; zero firings is intended", False
        elif fired > 0:
            verdict, mark = f"has fired {fired}x on real input", False
        elif age >= args.stale_days:
            verdict, mark = f"detective, {age}d, never fired — review", True
        else:
            verdict, mark = f"detective, {age}d, too young to judge", False

        if mark:
            candidates.append(name)
        print(f"  {name:16} {kind:11} {fired:5}  {age:4}d  {'* ' if mark else '  '}{verdict}")

    live = len(declared)
    print()
    print(f"  {live}/{cap} invariants against the budget")
    if candidates:
        print(f"  {len(candidates)} deletion candidate(s): {', '.join(candidates)}")
        print("  Deleting one is how the next invariant gets added without raising the cap.")
    else:
        print("  No deletion candidates. Adding one means raising the cap deliberately,")
        print("  which is a sealed change and shows in the seal delta.")

    if not (root / FIRINGS).is_file():
        print()
        print(f"  note: no firing record yet at {FIRINGS} — detective invariants")
        print("        cannot be judged until the gate has run against real breakage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
