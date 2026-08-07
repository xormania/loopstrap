from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Iterable

from .atomic import canonical_json
from .errors import SchemaError
from .bounded import run_bounded, sanitized_environment


VISIBILITIES = {"visible", "holdout"}


@dataclass(frozen=True)
class TestCommand:
    name: str
    visibility: str
    argv: tuple[str, ...]
    timeout_seconds: float = 30.0
    max_output_bytes: int = 1_000_000

    def validate(self) -> None:
        if not self.name:
            raise SchemaError("test command name must be nonempty")
        if self.visibility not in VISIBILITIES:
            raise SchemaError(f"invalid test visibility: {self.visibility}")
        if not self.argv or any(not isinstance(item, str) or not item for item in self.argv):
            raise SchemaError("test command must be a nonempty argument vector")
        if self.timeout_seconds <= 0 or self.max_output_bytes <= 0:
            raise SchemaError("test command bounds must be positive")

    def basis(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "visibility": self.visibility,
            "argv": list(self.argv),
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
        }


@dataclass(frozen=True)
class VerificationPlan:
    commands: tuple[TestCommand, ...]
    visible_digest: str
    holdout_digest: str

    @classmethod
    def create(cls, commands: Iterable[TestCommand]) -> "VerificationPlan":
        rows = tuple(commands)
        if not rows:
            raise SchemaError("verification plan must contain tests")
        for command in rows:
            if not isinstance(command, TestCommand):
                raise SchemaError("verification plan entries must be test commands")
            command.validate()
        names = [command.name for command in rows]
        if len(set(names)) != len(names):
            raise SchemaError("verification test names must be unique")
        grouped = {
            visibility: [
                command.basis()
                for command in rows
                if command.visibility == visibility
            ]
            for visibility in sorted(VISIBILITIES)
        }
        if any(not grouped[visibility] for visibility in VISIBILITIES):
            raise SchemaError("verification plan requires visible and holdout tests")
        return cls(
            commands=rows,
            visible_digest=hashlib.sha256(
                canonical_json(grouped["visible"])
            ).hexdigest(),
            holdout_digest=hashlib.sha256(
                canonical_json(grouped["holdout"])
            ).hexdigest(),
        )


@dataclass(frozen=True)
class VerificationReceipt:
    name: str
    visibility: str
    argv_digest: str
    return_code: int
    passed: bool
    stdout_sha256: str
    stderr_sha256: str
    stdout_bytes: int
    stderr_bytes: int
    latency_ms: int
    started_at: str
    ended_at: str
    duration_ns: int
    process_trace: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "visibility": self.visibility,
            "argv_digest": self.argv_digest,
            "return_code": self.return_code,
            "passed": self.passed,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
            "latency_ms": self.latency_ms,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ns": self.duration_ns,
            "process_trace": dict(self.process_trace),
        }


@dataclass(frozen=True)
class VerificationReport:
    visible_digest: str
    holdout_digest: str
    passed: bool
    receipts: tuple[VerificationReceipt, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "visible_digest": self.visible_digest,
            "holdout_digest": self.holdout_digest,
            "passed": self.passed,
            "receipts": [receipt.to_dict() for receipt in self.receipts],
        }


class DeterministicVerifier:
    def run(self, workspace: Path, plan: VerificationPlan) -> VerificationReport:
        workspace = Path(workspace)
        if not workspace.is_dir() or workspace.is_symlink():
            raise SchemaError("verification workspace must be a real directory")
        receipts: list[VerificationReceipt] = []
        environment = sanitized_environment({})
        for command in plan.commands:
            return_code, stdout, stderr, process_trace = run_bounded(
                command.argv,
                b"",
                workspace=workspace,
                environment=environment,
                timeout_seconds=command.timeout_seconds,
                max_output_bytes=command.max_output_bytes,
            )
            receipts.append(
                VerificationReceipt(
                    name=command.name,
                    visibility=command.visibility,
                    argv_digest=hashlib.sha256(
                        canonical_json(list(command.argv))
                    ).hexdigest(),
                    return_code=return_code,
                    passed=return_code == 0,
                    stdout_sha256=hashlib.sha256(stdout).hexdigest(),
                    stderr_sha256=hashlib.sha256(stderr).hexdigest(),
                    stdout_bytes=len(stdout),
                    stderr_bytes=len(stderr),
                    latency_ms=int(process_trace.duration_ns / 1_000_000),
                    started_at=process_trace.started_at,
                    ended_at=process_trace.ended_at,
                    duration_ns=process_trace.duration_ns,
                    process_trace=process_trace.to_dict(),
                )
            )
        return VerificationReport(
            visible_digest=plan.visible_digest,
            holdout_digest=plan.holdout_digest,
            passed=all(receipt.passed for receipt in receipts),
            receipts=tuple(receipts),
        )
