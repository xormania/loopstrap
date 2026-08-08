#!/usr/bin/env python3
"""Refuse a lane detector whose vocabulary names something that no longer exists.

C-LANE-002 refuses a production file that names development machinery. It knows
what "development machinery" means from DEV_PATHS in schema-facts.py — a list of
strings — and that list went stale exactly once: it held "skills/dev/" after the
skills moved to .claude/skills/, so the entry could never match again.

Nothing failed. The check went on passing while covering less than it claimed,
which is the failure mode this repository exists to prevent and the one that
makes a check worse than no check: it reports safety it is no longer providing.

So every entry must still match at least one tracked path. When a development
directory moves, this fails until DEV_PATHS moves with it.

    lane-vocabulary-live.py [root]

Exit 0 every entry live, 1 one or more dead.
"""

import ast, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1])
src = (root / "artifacts/instance/tools/schema-facts.py").read_text(encoding="utf-8")
entries = next(
    ast.literal_eval(n.value)
    for n in ast.parse(src).body
    if isinstance(n, ast.Assign)
    and any(getattr(t, "id", "") == "DEV_PATHS" for t in n.targets)
)
paths = subprocess.run(["git", "-C", str(root), "ls-files"],
                       capture_output=True, text=True).stdout
dead = [e for e in entries if e not in paths]
for e in dead:
    print(f"DEAD ENTRY: {e}")
sys.exit(1 if dead else 0)
