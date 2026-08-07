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
import hashlib
import os
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


def _tree_key(root: Path, salt: str) -> str:
    """sha256 over every source file's name and bytes, in sorted order."""
    digest = hashlib.sha256()
    digest.update(salt.encode("utf-8"))
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def python_facts(root: Path) -> tuple[list[dict], list[dict]]:
    """(resolved field sets, call sites whose set could not be resolved).

    Parsing 26 modules with ast costs ~104ms and is the gate's largest single
    expense. Cached on the sha256 of the sources themselves, so an edit to any of
    them always misses.
    """
    key = _tree_key(root, "python_facts/v1")
    cached = _cache_load(key)
    if cached is not None:
        return cached["facts"], cached["unresolved"]
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
    _cache_store(key, {"facts": facts, "unresolved": unresolved})
    return facts, unresolved



# Content-addressed cache for definition enumeration.
#
# CUE process startup is ~50ms and dominates: three files cost 150ms of a 307ms
# gate. The answer depends on exactly two things — the bytes of the .cue file and
# which compiler read them — so the key is both, and a changed file always misses.
#
# Deliberately NOT keyed on mtime. A timestamp heuristic is fine for a build
# system and wrong for anything whose job is noticing a change; the seal and the
# binary digest are not cached for the same reason.
#
# Lives outside the tree, so it is never sealed and never needs cleaning.
def _cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "loopstrap" / "cue-definitions"


def _cache_key(binary: Path, path: Path) -> str | None:
    """sha256 of the pinned compiler identity plus the file's bytes.

    The compiler digest is read from the pin rather than hashed: the binary is
    24MB and hashing it every run would cost more than the cache saves.
    """
    pin = binary.parent.parent.parent.parent / "config" / "cue-tool.v1.json"
    try:
        compiler = json.loads(pin.read_text(encoding="utf-8"))["binary_sha256"]
    except (OSError, ValueError, KeyError):
        return None
    digest = hashlib.sha256()
    digest.update(compiler.encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
    return digest.hexdigest()



def _cache_load(key: str) -> dict | None:
    if os.environ.get("LOOPSTRAP_NO_CACHE"):
        return None
    try:
        return json.loads((_cache_dir() / f"{key}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _cache_store(key: str, value: dict) -> None:
    if os.environ.get("LOOPSTRAP_NO_CACHE"):
        return
    try:
        directory = _cache_dir()
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{key}.json"
        scratch = target.with_suffix(".tmp")
        scratch.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        scratch.replace(target)
    except OSError:
        pass


def _cache_read(binary: Path, path: Path) -> dict | None:
    if os.environ.get("LOOPSTRAP_NO_CACHE"):
        return None
    key = _cache_key(binary, path)
    if key is None:
        return None
    try:
        return json.loads((_cache_dir() / f"{key}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _cache_write(binary: Path, path: Path, answer: dict) -> None:
    if os.environ.get("LOOPSTRAP_NO_CACHE"):
        return
    key = _cache_key(binary, path)
    if key is None:
        return
    try:
        directory = _cache_dir()
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{key}.json"
        scratch = target.with_suffix(".tmp")
        scratch.write_text(json.dumps(answer, sort_keys=True), encoding="utf-8")
        scratch.replace(target)
    except OSError:
        pass


def cue_facts(binary: Path, schema_root: Path) -> list[dict]:
    """Field names per closed definition, straight from the compiler.

    One evaluation per FILE, not per definition. The first version spawned a
    subprocess for each of the 20 definitions and cost 217ms of a 316ms gate; a
    batched expression asks the same questions in three. The fastest cache is not
    needing one — there is nothing here to warm, invalidate, or get wrong.
    """
    facts: list[dict] = []
    for path in sorted(schema_root.glob("*.cue")):
        names = DEFINITION.findall(path.read_text(encoding="utf-8"))
        if not names:
            continue
        cached = _cache_read(binary, path)
        if cached is not None:
            for name, fields in cached.items():
                facts.append(
                    {"definition": name, "file": path.name, "fields": sorted(fields)}
                )
            continue
        expression = "{" + ",".join(
            f'"{name}": [for k, _ in {name} {{k}}]' for name in names
        ) + "}"
        completed = subprocess.run(
            [str(binary), "eval", str(path), "-e", expression, "--out", "json"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC"},
        )
        if completed.returncode != 0:
            print(
                f"schema-facts: {path.name}: {completed.stderr.strip()}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        answer = json.loads(completed.stdout)
        _cache_write(binary, path, answer)
        for name, fields in answer.items():
            facts.append(
                {"definition": name, "file": path.name, "fields": sorted(fields)}
            )
    return sorted(facts, key=lambda row: (row["file"], row["definition"]))


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
