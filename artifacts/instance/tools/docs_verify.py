#!/usr/bin/env python3
"""Schema-complete validator for a Loopstrap member document set."""

from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "artifacts" / "contracts"
MEMBER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
CLAUSE_RE = re.compile(r"^\[([A-Z][A-Z0-9-]*)\]", re.MULTILINE)
KINDS = {"MUST", "MUSTNOT", "INV", "GUAR", "DEF"}
TIERS = {"BANNED", "REVIEW", "QUALIFY", "CANON"}


class Results:
    def __init__(self) -> None:
        self.passes = 0
        self.failures = 0

    def ok(self, message: str) -> None:
        self.passes += 1
        print(f"  \033[32mPASS\033[0m  {message}")

    def no(self, message: str) -> None:
        self.failures += 1
        print(f"  \033[31mFAIL\033[0m  {message}")


def safe_file_name(name: object) -> str | None:
    if not isinstance(name, str):
        return None
    path = Path(name)
    if path.is_absolute() or len(path.parts) != 1 or name in {"", ".", ".."}:
        return None
    return name


def load_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def validate(argument: str) -> int:
    result = Results()
    candidate = Path(argument)
    directory = candidate.resolve() if candidate.is_dir() else (CONTRACTS / argument).resolve()
    manifest_path = directory / "docs-manifest.toml"
    if not manifest_path.is_file():
        result.no("docs-manifest.toml missing — the member is unlicensed")
        return finish(result)

    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        member = manifest["member"]
        if not isinstance(member, str) or MEMBER_RE.fullmatch(member) is None:
            raise ValueError("member must match [A-Za-z0-9][A-Za-z0-9_.-]*")
    except (OSError, KeyError, tomllib.TOMLDecodeError, ValueError) as exc:
        result.no(f"manifest unparseable: {exc}")
        return finish(result)
    result.ok(f"manifest parses (member={member})")

    required = {
        f"{member}-lexicon.md",
        f"{member}-contracts.md",
        f"{member}-experience.md",
        "clause-index.txt",
        "term-export.txt",
        "parties.txt",
    }
    raw_files = manifest.get("files")
    if not isinstance(raw_files, dict):
        result.no("manifest [files] table missing")
        files: dict[str, object] = {}
    else:
        files = raw_files
        names = {name for name in files if safe_file_name(name) is not None}
        unsafe = sorted(str(name) for name in files if safe_file_name(name) is None)
        missing = sorted(required - names)
        extra = sorted(names - required)
        if unsafe or missing or extra or len(files) != len(names):
            detail = []
            if unsafe:
                detail.append(f"unsafe={unsafe}")
            if missing:
                detail.append(f"missing={missing}")
            if extra:
                detail.append(f"extra={extra}")
            result.no("manifest [files] must enumerate exactly the six required files: " + " ".join(detail))
        else:
            result.ok("manifest [files] is schema-complete and path-safe")

    hash_failures: list[str] = []
    for name in sorted(required):
        expected = files.get(name)
        path = directory / name
        if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            hash_failures.append(f"HASH-SCHEMA {name}")
            continue
        if not path.is_file() or path.is_symlink():
            hash_failures.append(f"MISS {name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            hash_failures.append(f"HASH {name}")
    if hash_failures:
        for failure in hash_failures:
            print(f"  {failure}")
        result.no("manifest hash failures above")
    else:
        result.ok("every required manifest file present + hash-true")

    lexicon = directory / f"{member}-lexicon.md"
    contracts = directory / f"{member}-contracts.md"
    experience = directory / f"{member}-experience.md"
    index_path = directory / "clause-index.txt"
    parties_path = directory / "parties.txt"
    export_path = directory / "term-export.txt"

    if contracts.is_file() and index_path.is_file():
        document_ids = CLAUSE_RE.findall(contracts.read_text(encoding="utf-8"))
        duplicate_document_ids = sorted(
            clause for clause, count in Counter(document_ids).items() if count > 1
        )
        index_rows: list[tuple[str, str, str]] = []
        malformed_index: list[str] = []
        for line in load_lines(index_path):
            parts = line.split()
            if len(parts) != 3:
                malformed_index.append(line)
            else:
                index_rows.append((parts[0], parts[1], parts[2]))
        index_ids = [row[0] for row in index_rows]
        duplicate_index_ids = sorted(
            clause for clause, count in Counter(index_ids).items() if count > 1
        )
        if malformed_index:
            result.no(f"clause-index malformed rows: {malformed_index}")
        elif duplicate_document_ids or duplicate_index_ids:
            result.no(
                "duplicate clause ids: "
                f"contracts={duplicate_document_ids} index={duplicate_index_ids}"
            )
        elif Counter(document_ids) != Counter(index_ids):
            missing = sorted(set(document_ids) - set(index_ids))
            extra = sorted(set(index_ids) - set(document_ids))
            result.no(f"clause-index ↔ contracts mismatch: document-only={missing} index-only={extra}")
        else:
            result.ok(f"clause-index ↔ contracts: exact bijection ({len(index_ids)} clauses)")
        invalid_kinds = sorted({kind for _, _, kind in index_rows if kind not in KINDS})
        if invalid_kinds:
            result.no(f"index kind column invalid: {invalid_kinds}")
        else:
            result.ok("index kinds valid")

        parties = load_lines(parties_path) if parties_path.is_file() else []
        duplicate_parties = sorted(
            party for party, count in Counter(parties).items() if count > 1
        )
        index_parties = {party for _, party, _ in index_rows}
        unknown = sorted(index_parties - set(parties))
        unowned = sorted(set(parties) - index_parties)
        if not parties or duplicate_parties or unknown or unowned:
            result.no(
                "party coverage invalid: "
                f"empty={not parties} duplicates={duplicate_parties} "
                f"unknown={unknown} without-clause={unowned}"
            )
        else:
            result.ok("party coverage exact: every index party declared and every party owns a clause")
    else:
        result.no("contracts or clause-index missing")

    if export_path.is_file() and lexicon.is_file():
        export_rows: list[tuple[str, str]] = []
        malformed_exports: list[str] = []
        for line in load_lines(export_path):
            parts = line.split(maxsplit=1)
            if len(parts) != 2 or parts[0] not in TIERS:
                malformed_exports.append(line)
            else:
                export_rows.append((parts[0], parts[1]))
        duplicate_terms = sorted(
            term for term, count in Counter(term for _, term in export_rows).items() if count > 1
        )
        if malformed_exports or duplicate_terms:
            result.no(
                f"term-export invalid: malformed={malformed_exports} duplicate-terms={duplicate_terms}"
            )
        else:
            result.ok("term-export tiers and uniqueness valid")
        lexicon_text = lexicon.read_text(encoding="utf-8")
        missing_terms = sorted(term for _, term in export_rows if term not in lexicon_text)
        if missing_terms:
            result.no(f"exported terms absent from lexicon: {missing_terms}")
        else:
            result.ok("every exported term appears in the lexicon")
    else:
        result.no("term-export or lexicon missing")

    if experience.is_file():
        experience_text = experience.read_text(encoding="utf-8")
        if re.search(r"^\[X-[0-9]+\]", experience_text, re.MULTILINE) or re.search(
            r"no experience surface", experience_text, re.IGNORECASE
        ):
            result.ok("experience: anchored entries or declared absence")
        else:
            result.no("experience spec has neither [X-n] entries nor declared absence")
    else:
        result.no("experience spec missing")

    judges = manifest.get("judges")
    if not isinstance(judges, dict):
        judges = {}
    profile = judges.get("profile", "rust")
    if not isinstance(profile, str) or MEMBER_RE.fullmatch(profile) is None:
        result.no(f"judge profile path is invalid: {profile!r}")
    elif profile == "custom":
        local = judges.get("local")
        if isinstance(local, list) and local and all(isinstance(item, str) and item for item in local):
            result.ok("custom judge profile carries a nonempty local command list")
        else:
            result.no("custom judge profile requires a nonempty [judges].local command list")
    else:
        profile_path = ROOT / "artifacts" / "ci" / "profiles" / f"{profile}.md"
        if profile_path.is_file() and profile_path.parent == ROOT / "artifacts" / "ci" / "profiles":
            result.ok(f"judge profile '{profile}' resolves")
        else:
            result.no(
                f"judge profile '{profile}' named but artifacts/ci/profiles/{profile}.md missing — broken binding"
            )

    triad = [lexicon, contracts, experience]
    marker_files = [
        path.name
        for path in triad
        if path.is_file() and "drafting decision — confirm" in path.read_text(encoding="utf-8")
    ]
    if marker_files:
        result.no(f"unresolved [drafting decision] markers survive: {marker_files}")
    else:
        result.ok("no unresolved markers")

    if all(path.is_file() for path in triad):
        wall = subprocess.run(
            [str(ROOT / "wall.sh"), "--lane", "runtime", *(str(path) for path in triad)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if wall.returncode == 0:
            result.ok("R6 wall holds over the triad")
        else:
            result.no("R6 wall breach in the triad — dev-lane vocabulary present")
    else:
        result.no("R6 wall could not inspect the complete triad")
    return finish(result)


def finish(result: Results) -> int:
    print(f"  ════ {result.passes} PASS · {result.failures} FAIL ════")
    if result.failures == 0:
        print("  DOC SET VERIFIES — ratifiable (the owner's hand completes the plug act).")
    return 1 if result.failures else 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: docs-verify.sh <member>|<path>", file=sys.stderr)
        return 2
    return validate(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
