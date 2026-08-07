#!/usr/bin/env python3
"""Extract exact-field-set facts from both schema languages.

Two authority classes, neither of which is asked to describe the other:

- Python is authoritative about Python. Every `FIELDS = {...}` class attribute
  and every `_exact(data, <set>, "<label>")` call site is read with `ast`, never
  by regex, so a rename or a reformat cannot silently change a fact.
- CUE is authoritative about CUE. Field names come from
  `cue eval -e '[for k, _ in #Def {k}]'`, which is the compiler's own answer and
  already excludes hidden fields.

The output is normalized facts only. It declares no pairing and reaches no
verdict; `contract/` owns both.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import sys


DEFINITION = re.compile(r"^(#\w+):\s*close\(\{", re.M)


def _set_literal(node: ast.AST) -> set[str] | None:
    if isinstance(node, ast.Set):
        names = {e.value for e in node.elts if isinstance(e, ast.Constant)}
        return names if len(names) == len(node.elts) else None
    return None


def _local_sets(function: ast.AST) -> dict[str, set[str]]:
    """Simple `name = {...}` assignments inside one function body."""
    found: dict[str, set[str]] = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            literal = _set_literal(node.value)
            if isinstance(target, ast.Name) and literal is not None:
                found[target.id] = literal
    return found


def python_facts(root: Path) -> tuple[list[dict], list[dict]]:
    """(resolved field sets, call sites whose set could not be resolved)."""
    facts: list[dict] = []
    unresolved: list[dict] = []
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        class_fields: dict[str, set[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for stmt in node.body:
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and getattr(stmt.targets[0], "id", None) == "FIELDS"
                    ):
                        literal = _set_literal(stmt.value)
                        if literal is not None:
                            class_fields[node.name] = literal
                            facts.append(
                                {
                                    "kind": "class_fields",
                                    "module": path.name,
                                    "symbol": node.name,
                                    "label": node.name,
                                    "fields": sorted(literal),
                                }
                            )
        # every _exact(data, <set>, "<label>") call site
        for function in [
            n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]:
            locals_here = _local_sets(function)
            for node in ast.walk(function):
                if not (
                    isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "_exact"
                    and len(node.args) >= 3
                ):
                    continue
                label = (
                    node.args[2].value
                    if isinstance(node.args[2], ast.Constant)
                    else None
                )
                argument = node.args[1]
                fields = _set_literal(argument)
                if fields is None and isinstance(argument, ast.Name):
                    fields = locals_here.get(argument.id)
                if fields is None and isinstance(argument, ast.Attribute):
                    if argument.attr == "FIELDS":
                        continue  # already recorded as class_fields
                if fields is None or label is None:
                    unresolved.append(
                        {
                            "module": path.name,
                            "line": node.lineno,
                            "label": label,
                            "reason": "field set is not a resolvable literal",
                        }
                    )
                    continue
                facts.append(
                    {
                        "kind": "exact_call",
                        "module": path.name,
                        "symbol": f"{function.name}:{node.lineno}",
                        "label": label,
                        "fields": sorted(fields),
                    }
                )
    return facts, unresolved


def cue_facts(binary: Path, schema_root: Path) -> list[dict]:
    facts: list[dict] = []
    for path in sorted(schema_root.glob("*.cue")):
        for name in DEFINITION.findall(path.read_text(encoding="utf-8")):
            completed = subprocess.run(
                [
                    str(binary),
                    "eval",
                    str(path),
                    "-e",
                    f"[for k, _ in {name} {{k}}]",
                    "--out",
                    "json",
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC"},
            )
            if completed.returncode != 0:
                print(
                    f"schema-facts: {path.name} {name}: {completed.stderr.strip()}",
                    file=sys.stderr,
                )
                raise SystemExit(2)
            facts.append(
                {
                    "definition": name,
                    "file": path.name,
                    "fields": sorted(json.loads(completed.stdout)),
                }
            )
    return facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    facts, unresolved = python_facts(root / "loopstrap_core")
    document = {
        "python": facts,
        "pythonUnresolved": unresolved,
        "cue": cue_facts(
            root / "tools" / "cue" / "v0.17.0" / "cue", root / "spec" / "cue"
        ),
    }
    text = json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
