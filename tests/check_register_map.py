#!/usr/bin/env python3
"""Reconcile declared assertion mappings with protected runtime evidence."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "tests" / "REGISTER-MAP.tsv"
REGISTER = ROOT / "artifacts" / "registers" / "design-decision-register.md"
CALL_RE = re.compile(r"\b(?:ok|assert_eq|assert_contains)\s+\"([^\"]+)\"")


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)
    print(f"  {message}")


def read_map(errors: list[str]) -> list[tuple[str, str, tuple[str, ...]]]:
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    seen: set[tuple[str, str]] = set()
    for number, line in enumerate(MAP.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            fail(f"MAP MALFORMED line {number}", errors)
            continue
        case, label, raw_ids = parts
        key = (case, label)
        if key in seen:
            fail(f"DUPLICATE MAP ROW: {case}/[{label}]", errors)
        seen.add(key)
        ids = tuple(raw_ids.split())
        if not ids:
            fail(f"NO REGISTER IDS: {case}/[{label}]", errors)
        rows.append((case, label, ids))
    return rows


def read_summary(path: Path, errors: list[str]) -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            key, raw = line.split("\t", 1)
            values[key] = int(raw)
    except (OSError, ValueError):
        fail("SUITE SUMMARY malformed or missing", errors)
        return {}
    required = {"cases", "assertions", "pass", "fail"}
    if set(values) != required:
        fail(f"SUITE SUMMARY keys invalid: {sorted(values)}", errors)
    if values.get("pass", 0) + values.get("fail", 0) != values.get("assertions", -1):
        fail("SUITE SUMMARY pass+fail does not equal assertions", errors)
    return values


def read_record(path: Path, errors: list[str]) -> list[tuple[int, str, str, str]]:
    rows: list[tuple[int, str, str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        fail("RUNTIME RECORD missing", errors)
        return rows
    for number, line in enumerate(lines, 1):
        parts = line.split("\t")
        if len(parts) != 4:
            fail(f"RUNTIME RECORD malformed line {number}", errors)
            continue
        raw_sequence, case, label, status = parts
        try:
            sequence = int(raw_sequence)
        except ValueError:
            fail(f"RUNTIME RECORD invalid sequence line {number}", errors)
            continue
        if sequence != number:
            fail(f"RUNTIME RECORD sequence gap: row {number} says {sequence}", errors)
        if status not in {"PASS", "FAIL"}:
            fail(f"RUNTIME RECORD invalid status line {number}: {status}", errors)
        rows.append((sequence, case, label, status))
    return rows


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check-register-map.sh <record.tsv> <summary.tsv>", file=sys.stderr)
        return 2
    errors: list[str] = []
    if not MAP.is_file():
        print("REGISTER MAP MISSING")
        return 1
    rows = read_map(errors)
    register_text = REGISTER.read_text(encoding="utf-8")
    map_keys = {(case, label) for case, label, _ in rows}
    mapped_cases = {case for case, _, _ in rows}

    case_files = sorted((ROOT / "tests" / "cases").glob("[a-z]*.sh"))
    actual_cases = {path.stem for path in case_files}
    for case in sorted(actual_cases - mapped_cases):
        fail(f"UNMAPPED case: {case}", errors)
    for case in sorted(mapped_cases - actual_cases):
        fail(f"MAP ROW for missing case: {case}", errors)

    for case, label, ids in rows:
        case_path = ROOT / "tests" / "cases" / f"{case}.sh"
        if case_path.is_file() and f'"{label}"' not in case_path.read_text(encoding="utf-8"):
            fail(f"LABEL not verbatim in {case}.sh: [{label}]", errors)
        for ruling in ids:
            if re.search(rf"^- \*\*{re.escape(ruling)}\*\*", register_text, re.MULTILINE) is None:
                fail(f"REGISTER id absent: {ruling} (cited by {case}/[{label}])", errors)

    for case_path in case_files:
        for source_line in case_path.read_text(encoding="utf-8").splitlines():
            if source_line.lstrip().startswith("#"):
                continue
            for label in CALL_RE.findall(source_line):
                if (case_path.stem, label) not in map_keys:
                    fail(f"UNMAPPED assertion in {case_path.stem}: [{label}]", errors)

    record = read_record(Path(sys.argv[1]), errors)
    summary = read_summary(Path(sys.argv[2]), errors)
    runtime_keys = [(case, label) for _, case, label, _ in record if not label.startswith("HARNESS:")]
    runtime_counter = Counter(runtime_keys)
    for key in sorted(map_keys):
        count = runtime_counter[key]
        if count == 0:
            fail(f"DECLARED BUT NEVER RAN: {key[0]}/[{key[1]}]", errors)
        elif count != 1:
            fail(f"DECLARED RAN {count} TIMES: {key[0]}/[{key[1]}]", errors)
    for key in sorted(set(runtime_counter) - map_keys):
        fail(f"RAN BUT UNMAPPED: {key[0]}/[{key[1]}]", errors)

    if len(record) != summary.get("assertions", -1):
        fail(
            f"COUNT MISMATCH: record has {len(record)}, suite summary has {summary.get('assertions', 'missing')}",
            errors,
        )
    status_counts = Counter(status for _, _, _, status in record)
    if status_counts["PASS"] != summary.get("pass", -1) or status_counts["FAIL"] != summary.get("fail", -1):
        fail("STATUS MISMATCH: record PASS/FAIL totals differ from protected suite summary", errors)
    if len(rows) != summary.get("assertions", -1):
        fail(
            f"MAP/SUITE MISMATCH: map declares {len(rows)}, protected suite ran {summary.get('assertions', 'missing')}",
            errors,
        )
    if summary.get("cases") != len(actual_cases):
        fail(
            f"CASE COUNT MISMATCH: discovered {len(actual_cases)}, suite reports {summary.get('cases', 'missing')}",
            errors,
        )

    if errors:
        print(f"REGISTER MAP: {len(errors)} violation(s).")
        return 1
    print(
        f"REGISTER MAP CHECKED — {len(rows)} declared, {len(record)} protected events, "
        f"{len(actual_cases)} cases; counts and statuses agree; cited entries exist."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
