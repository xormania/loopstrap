#!/usr/bin/env python3
from __future__ import annotations

import io
from pathlib import Path
import sys
import tomllib
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class Result(unittest.TextTestResult):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.outcomes: dict[str, str] = {}

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        self.outcomes[test.id()] = "PASS"
        super().addSuccess(test)

    def addFailure(self, test: unittest.case.TestCase, err) -> None:
        self.outcomes[test.id()] = "FAIL"
        super().addFailure(test, err)

    def addError(self, test: unittest.case.TestCase, err) -> None:
        self.outcomes[test.id()] = "ERROR"
        super().addError(test, err)

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
        self.outcomes[test.id()] = "SKIP"
        super().addSkip(test, reason)


def flatten(suite: unittest.TestSuite) -> list[unittest.case.TestCase]:
    result: list[unittest.case.TestCase] = []
    for item in suite:
        result.extend(flatten(item) if isinstance(item, unittest.TestSuite) else [item])
    return result


def main() -> int:
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    tests = flatten(suite)
    test_ids = {test.id() for test in tests}
    mapping: dict[str, tuple[str, ...]] = {}
    for line in (HERE / "map.tsv").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        test_id, raw_claims = line.split("\t")
        if test_id in mapping:
            print(f"ACTIVE INVENTORY FAILURE: duplicate test {test_id}", file=sys.stderr)
            return 2
        mapping[test_id] = tuple(raw_claims.split())
    claims_data = tomllib.loads((HERE / "claims.toml").read_text(encoding="utf-8"))
    claim_ids = [row["id"] for row in claims_data["claim"]]
    cited = {claim for row in mapping.values() for claim in row}
    if (
        not test_ids
        or set(mapping) != test_ids
        or set(claim_ids) != cited
        or len(claim_ids) != len(set(claim_ids))
    ):
        print(
            "ACTIVE INVENTORY FAILURE: "
            f"tests={len(test_ids)} mapped={len(mapping)} claims={len(claim_ids)} covered={len(cited)}",
            file=sys.stderr,
        )
        return 2
    stream = io.StringIO()
    result = unittest.TextTestRunner(
        stream=stream, verbosity=2, resultclass=Result
    ).run(suite)
    print(stream.getvalue(), end="")
    nonpass = {key: value for key, value in result.outcomes.items() if value != "PASS"}
    if set(result.outcomes) != test_ids:
        print("ACTIVE RESULT CHANNEL FAILURE", file=sys.stderr)
        return 2
    print(
        f"ACTIVE ACCEPTANCE: {len(test_ids)} tests · {len(claim_ids)} claims · "
        f"{len(test_ids) - len(nonpass)} passed · {len(nonpass)} non-pass"
    )
    return 0 if not nonpass else 1


if __name__ == "__main__":
    raise SystemExit(main())
