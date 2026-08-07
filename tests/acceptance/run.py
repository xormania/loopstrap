#!/usr/bin/env python3
"""Strict runner for the preimplementation Loopstrap acceptance claims."""

from __future__ import annotations

from collections import Counter
import argparse
import io
from pathlib import Path
import sys
import tomllib
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAP = HERE / "map.tsv"
CLAIMS = HERE / "claims.toml"


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.outcomes: dict[str, str] = {}

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        self.outcomes[test.id()] = "PASS"
        super().addSuccess(test)

    def addFailure(
        self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, object]
    ) -> None:
        self.outcomes[test.id()] = "FAIL"
        super().addFailure(test, err)

    def addError(
        self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, object]
    ) -> None:
        self.outcomes[test.id()] = "ERROR"
        super().addError(test, err)

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
        self.outcomes[test.id()] = "SKIP"
        super().addSkip(test, reason)

    def addExpectedFailure(
        self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, object]
    ) -> None:
        self.outcomes[test.id()] = "XFAIL"
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test: unittest.case.TestCase) -> None:
        self.outcomes[test.id()] = "XPASS"
        super().addUnexpectedSuccess(test)


def flatten(suite: unittest.TestSuite) -> list[unittest.case.TestCase]:
    tests: list[unittest.case.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            tests.extend(flatten(item))
        else:
            tests.append(item)
    return tests


def load_claim_ids() -> set[str]:
    data = tomllib.loads(CLAIMS.read_text(encoding="utf-8"))
    rows = data.get("claim", [])
    ids = [row.get("id") for row in rows]
    if not ids or any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("claims.toml contains an empty or malformed claim id")
    duplicates = [item for item, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate claim ids: {duplicates}")
    return set(ids)


def load_map() -> dict[str, tuple[str, ...]]:
    mapping: dict[str, tuple[str, ...]] = {}
    for line_number, line in enumerate(MAP.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise ValueError(f"map.tsv line {line_number} is malformed")
        test_id, raw_claims = parts
        if test_id in mapping:
            raise ValueError(f"duplicate mapped test: {test_id}")
        claims = tuple(raw_claims.split())
        if not claims:
            raise ValueError(f"test has no claims: {test_id}")
        mapping[test_id] = claims
    return mapping


def validate_inventory(test_ids: set[str], mapping: dict[str, tuple[str, ...]], claims: set[str]) -> None:
    if not test_ids:
        raise ValueError("ZERO acceptance tests discovered")
    missing_tests = sorted(test_ids - set(mapping))
    stale_tests = sorted(set(mapping) - test_ids)
    if missing_tests:
        raise ValueError(f"unmapped acceptance tests: {missing_tests}")
    if stale_tests:
        raise ValueError(f"map rows for missing tests: {stale_tests}")
    cited = {claim for row in mapping.values() for claim in row}
    unknown = sorted(cited - claims)
    uncovered = sorted(claims - cited)
    if unknown:
        raise ValueError(f"unknown claim ids in map: {unknown}")
    if uncovered:
        raise ValueError(f"acceptance claims without tests: {uncovered}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    tests = flatten(suite)
    test_ids = {test.id() for test in tests}
    try:
        mapping = load_map()
        claims = load_claim_ids()
        validate_inventory(test_ids, mapping, claims)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"ACCEPTANCE INVENTORY FAILURE: {exc}", file=sys.stderr)
        return 2
    if args.list:
        for test_id in sorted(test_ids):
            print(f"{test_id}\t{' '.join(mapping[test_id])}")
        return 0
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult)
    result = runner.run(suite)
    print(stream.getvalue(), end="")
    if set(result.outcomes) != test_ids:
        missing = sorted(test_ids - set(result.outcomes))
        duplicate_or_unknown = sorted(set(result.outcomes) - test_ids)
        print(
            "ACCEPTANCE RESULT CHANNEL FAILURE: "
            f"missing={missing} unexpected={duplicate_or_unknown}",
            file=sys.stderr,
        )
        return 2
    forbidden = {test_id: state for test_id, state in result.outcomes.items() if state != "PASS"}
    print(
        f"ACCEPTANCE: {len(test_ids)} tests · {len(claims)} claims · "
        f"{len(test_ids) - len(forbidden)} passed · {len(forbidden)} non-pass"
    )
    return 0 if not forbidden else 1


if __name__ == "__main__":
    raise SystemExit(main())
