#!/usr/bin/env python3
"""Compile config/seal.v1.json into seal-tree.py and verify-tree.py.

seal-tree.py and verify-tree.py must agree on what the seal covers, and neither
may import a module or read a config file at run time: land.sh ships
verify-tree.py alone inside a courier and runs it against a tree that carries
neither. Self-containment is a courier requirement — and it also means a courier
can never supply its own permissive exclusion policy.

So the rules are authored once as data and compiled into both tools. The compiled
block is committed. C-SEAL-001 in contract/ fails if it is stale, which is the
same check a compiled-container framework runs against its own cache.

    python3 artifacts/instance/tools/gen-seal-rules.py [--check] [--root DIR]

--check writes nothing and exits 1 if either tool is stale.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


TOOLS = ("seal-tree.py", "verify-tree.py")
BEGIN = "# --- BEGIN GENERATED seal exclusions"
END = "# --- END GENERATED seal exclusions"
BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)


def render(config: dict) -> str:
    def literal(values) -> str:
        return ", ".join(json.dumps(v) for v in values)

    names = sorted(config.get("excluded_names", ()))
    suffixes = sorted(config.get("excluded_suffixes", ()))
    root_names = sorted(config.get("excluded_root_names", ()))
    return f'''{BEGIN}
# Generated from config/seal.v1.json by gen-seal-rules.py. Do not edit by hand;
# edit the config and regenerate. C-SEAL-001 fails if this block is stale.
#
# Matched at ANY depth.
EXCLUDED_NAMES = frozenset({{{literal(names)}}})
EXCLUDED_SUFFIXES = ({literal(suffixes)},)
# Matched ONLY at the tree root. A name matched at any depth is a bypass, not an
# exclusion: a file can be hidden from the manifest by placing it in a directory
# of that name inside loopstrap_core.
EXCLUDED_ROOT_NAMES = frozenset({{{literal(root_names)}}})


def is_excluded(name: str, *, at_root: bool) -> bool:
    if name in EXCLUDED_NAMES or name.endswith(EXCLUDED_SUFFIXES):
        return True
    return at_root and name in EXCLUDED_ROOT_NAMES
{END}'''


def load_config(root: Path) -> dict:
    path = root / "config" / "seal.v1.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"seal config unreadable: {path}: {exc}") from exc
    if config.get("config_version") != 1:
        raise SystemExit(f"seal config version unsupported: {path}")
    excluded = set(config.get("excluded_names", ())) | set(
        config.get("excluded_root_names", ())
    )
    breach = sorted(excluded & set(config.get("never_excludable", ())))
    if breach:
        raise SystemExit(
            f"refusing to generate: config would exclude protected paths {breach} "
            f"(never_excludable in {path})"
        )
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    block = render(load_config(root))
    stale: list[str] = []
    for name in TOOLS:
        path = root / "artifacts" / "instance" / "tools" / name
        text = path.read_text(encoding="utf-8")
        if not BLOCK_RE.search(text):
            raise SystemExit(f"{name}: no generated block markers found")
        updated = BLOCK_RE.sub(lambda _: block, text, count=1)
        if updated == text:
            continue
        if args.check:
            stale.append(name)
        else:
            path.write_text(updated, encoding="utf-8")
            print(f"  regenerated {name}")

    if args.check:
        if stale:
            print(f"SEAL RULES STALE — {', '.join(stale)}", file=sys.stderr)
            return 1
        print("seal rules current in both tools")
        return 0
    print("seal rules compiled into both tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
