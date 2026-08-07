from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Iterable
import uuid

from .artifacts import ArtifactStore
from .atomic import canonical_json
from .bounded import run_bounded
from .errors import (
    CertificationError,
    HarnessOutputLimitError,
    HarnessTimeoutError,
    IdempotencyError,
    IntegrityError,
    SensitiveDataError,
)
from .budget import BudgetLedger, ResourceUsage


DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ISSUER = "loopstrap-certifier-v1"
REQUIRED_LAYERS = ("mechanical", "inference", "loopstrap")
STATUSES = ("PASS", "FAIL", "BLOCKED", "WARN", "INFO", "SKIP")


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        missing = fields - set(value) if isinstance(value, dict) else fields
        unknown = set(value) - fields if isinstance(value, dict) else set()
        raise CertificationError(
            f"{label} fields invalid: missing={sorted(missing)} "
            f"unknown={sorted(unknown)}"
        )
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CertificationError(f"{label} must be a nonempty string")
    return value


def _digest_ref(value: Any, label: str) -> str:
    result = _text(value, label)
    if not DIGEST_RE.fullmatch(result):
        raise CertificationError(f"{label} must be a SHA-256 reference")
    return result


def _string_list(value: Any, label: str, *, nonempty: bool = True) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise CertificationError(f"{label} must be a valid string list")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise CertificationError(f"{label} must be unique")
    return result


@dataclass(frozen=True)
class CertificationContract:
    version: int
    issuer: str
    required_layers: tuple[str, ...]
    statuses: tuple[str, ...]
    mechanical_obligations: tuple[dict[str, Any], ...]
    inference_tasks: tuple[dict[str, Any], ...]
    conformance_obligations: tuple[str, ...]

    FIELDS = {
        "version",
        "issuer",
        "required_layers",
        "statuses",
        "mechanical_obligations",
        "inference_tasks",
        "conformance_obligations",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CertificationContract":
        row = _exact(data, cls.FIELDS, "certification contract")
        version = row["version"]
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise CertificationError("certification contract version must be positive")
        issuer = _text(row["issuer"], "certification issuer")
        if issuer != ISSUER:
            raise CertificationError("unsupported certification issuer")
        layers = _string_list(row["required_layers"], "required certification layers")
        if layers != REQUIRED_LAYERS:
            raise CertificationError("certification layers or order are unsupported")
        statuses = _string_list(row["statuses"], "certification statuses")
        if statuses != STATUSES:
            raise CertificationError("certification statuses or order are unsupported")

        mechanical = row["mechanical_obligations"]
        if not isinstance(mechanical, list) or not mechanical:
            raise CertificationError("mechanical obligations must be a nonempty list")
        mechanical_rows: list[dict[str, Any]] = []
        for item in mechanical:
            value = _exact(item, {"id", "description"}, "mechanical obligation")
            mechanical_rows.append(
                {
                    "id": _text(value["id"], "mechanical obligation id"),
                    "description": _text(
                        value["description"], "mechanical obligation description"
                    ),
                }
            )
        if len({item["id"] for item in mechanical_rows}) != len(mechanical_rows):
            raise CertificationError("mechanical obligation ids must be unique")

        tasks = row["inference_tasks"]
        if not isinstance(tasks, list) or not tasks:
            raise CertificationError("inference tasks must be a nonempty list")
        task_rows: list[dict[str, Any]] = []
        for item in tasks:
            value = _exact(item, {"id", "objective", "mutation"}, "inference task")
            if not isinstance(value["mutation"], bool):
                raise CertificationError("inference task mutation flag must be boolean")
            task_rows.append(
                {
                    "id": _text(value["id"], "inference task id"),
                    "objective": _text(value["objective"], "inference task objective"),
                    "mutation": value["mutation"],
                }
            )
        expected_tasks = tuple(f"T{index}" for index in range(9))
        if tuple(item["id"] for item in task_rows) != expected_tasks:
            raise CertificationError("inference tasks must be the ordered T0 through T8 set")

        conformance = _string_list(
            row["conformance_obligations"], "conformance obligations"
        )
        return cls(
            version=version,
            issuer=issuer,
            required_layers=layers,
            statuses=statuses,
            mechanical_obligations=tuple(mechanical_rows),
            inference_tasks=tuple(task_rows),
            conformance_obligations=conformance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "issuer": self.issuer,
            "required_layers": list(self.required_layers),
            "statuses": list(self.statuses),
            "mechanical_obligations": [dict(item) for item in self.mechanical_obligations],
            "inference_tasks": [dict(item) for item in self.inference_tasks],
            "conformance_obligations": list(self.conformance_obligations),
        }

    @property
    def digest(self) -> str:
        return _digest(canonical_json(self.to_dict()))

    @property
    def mechanical_obligation_ids(self) -> tuple[str, ...]:
        return tuple(item["id"] for item in self.mechanical_obligations)

    @property
    def inference_task_ids(self) -> tuple[str, ...]:
        return tuple(item["id"] for item in self.inference_tasks)


@dataclass(frozen=True)
class ExecutableIdentity:
    path: str
    sha256: str
    version: str

    @classmethod
    def observe(cls, path: Path, *, version: str) -> "ExecutableIdentity":
        source = Path(path)
        try:
            resolved = source.resolve(strict=True)
        except OSError as exc:
            raise CertificationError(f"certification executable is unavailable: {path}") from exc
        if not resolved.is_file():
            raise CertificationError(f"certification executable is not a file: {resolved}")
        return cls(
            path=str(resolved),
            sha256=_digest(resolved.read_bytes()),
            version=_text(version, "executable version"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutableIdentity":
        row = _exact(data, {"path", "sha256", "version"}, "executable identity")
        path = _text(row["path"], "executable path")
        if not Path(path).is_absolute():
            raise CertificationError("executable path must be absolute")
        return cls(
            path=path,
            sha256=_digest_ref(row["sha256"], "executable digest"),
            version=_text(row["version"], "executable version"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256, "version": self.version}

    def matches_current_bytes(self) -> bool:
        path = Path(self.path)
        try:
            return path.is_file() and _digest(path.read_bytes()) == self.sha256
        except OSError:
            return False


@dataclass(frozen=True)
class CertificationReceipt:
    schema_version: int
    issuer: str
    run_id: str
    role_treatment_id: str
    role_treatment_identity_digest: str
    contract_digest: str
    executables: tuple[ExecutableIdentity, ...]
    layer_results: dict[str, str]
    evidence_refs: tuple[str, ...]
    report_ref: str | None
    issued_at: str

    FIELDS = {
        "schema_version",
        "issuer",
        "run_id",
        "role_treatment_id",
        "role_treatment_identity_digest",
        "contract_digest",
        "executables",
        "layer_results",
        "evidence_refs",
        "report_ref",
        "issued_at",
    }

    @classmethod
    def issue(
        cls,
        *,
        role_treatment: Any,
        executables: Iterable[ExecutableIdentity],
        contract_digest: str,
        run_id: str,
        layer_results: dict[str, str],
        evidence_refs: Iterable[str],
        report_ref: str | None,
        issued_at: str,
    ) -> "CertificationReceipt":
        if not hasattr(role_treatment, "static_identity_digest"):
            raise CertificationError(
                "receipt Role-Treatment lacks a static identity"
            )
        return cls.from_dict(
            {
                "schema_version": 1,
                "issuer": ISSUER,
                "run_id": run_id,
                "role_treatment_id": role_treatment.id,
                "role_treatment_identity_digest": (
                    role_treatment.static_identity_digest()
                ),
                "contract_digest": contract_digest,
                "executables": [item.to_dict() for item in executables],
                "layer_results": dict(layer_results),
                "evidence_refs": list(evidence_refs),
                "report_ref": report_ref,
                "issued_at": issued_at,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CertificationReceipt":
        row = _exact(data, cls.FIELDS, "certification receipt")
        schema_version = row["schema_version"]
        if schema_version != 1 or isinstance(schema_version, bool):
            raise CertificationError("unsupported certification receipt schema")
        issuer = _text(row["issuer"], "receipt issuer")
        if issuer != ISSUER:
            raise CertificationError("receipt issuer is not machine-owned")
        executables = row["executables"]
        if not isinstance(executables, list) or not executables:
            raise CertificationError("receipt requires executable identities")
        executable_rows = tuple(ExecutableIdentity.from_dict(item) for item in executables)
        if len({item.path for item in executable_rows}) != len(executable_rows):
            raise CertificationError("receipt executable paths must be unique")
        layer_results = row["layer_results"]
        if (
            not isinstance(layer_results, dict)
            or any(
                not isinstance(key, str)
                or not key
                or not isinstance(value, str)
                or value not in STATUSES
                for key, value in layer_results.items()
            )
        ):
            raise CertificationError("receipt layer results are invalid")
        evidence_refs = tuple(
            _digest_ref(item, "certification evidence reference")
            for item in _string_list(row["evidence_refs"], "certification evidence")
        )
        report_ref = row["report_ref"]
        if report_ref is not None:
            report_ref = _digest_ref(report_ref, "certification report reference")
        return cls(
            schema_version=1,
            issuer=issuer,
            run_id=_text(row["run_id"], "certification run id"),
            role_treatment_id=_text(
                row["role_treatment_id"], "certification Role-Treatment id"
            ),
            role_treatment_identity_digest=_digest_ref(
                row["role_treatment_identity_digest"],
                "Role-Treatment identity digest",
            ),
            contract_digest=_digest_ref(
                row["contract_digest"], "certification contract digest"
            ),
            executables=executable_rows,
            layer_results=dict(layer_results),
            evidence_refs=evidence_refs,
            report_ref=report_ref,
            issued_at=_text(row["issued_at"], "certification issue time"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "issuer": self.issuer,
            "run_id": self.run_id,
            "role_treatment_id": self.role_treatment_id,
            "role_treatment_identity_digest": (
                self.role_treatment_identity_digest
            ),
            "contract_digest": self.contract_digest,
            "executables": [item.to_dict() for item in self.executables],
            "layer_results": dict(self.layer_results),
            "evidence_refs": list(self.evidence_refs),
            "report_ref": self.report_ref,
            "issued_at": self.issued_at,
        }

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @classmethod
    def reference_for(cls, data: dict[str, Any]) -> str:
        return _digest(canonical_json(data))

    @property
    def reference(self) -> str:
        return self.reference_for(self.to_dict())


class CertificationAuthority:
    def __init__(
        self,
        *,
        contract_digest: str,
        artifacts: ArtifactStore,
        receipts: Iterable[CertificationReceipt],
    ) -> None:
        self.contract_digest = _digest_ref(
            contract_digest, "certification authority contract digest"
        )
        self.artifacts = artifacts
        self.receipts = tuple(receipts)
        if len({receipt.reference for receipt in self.receipts}) != len(self.receipts):
            raise CertificationError("certification receipt references must be unique")
        for receipt in self.receipts:
            reference = artifacts.put_bytes(
                receipt.to_bytes(), media_type="application/json"
            )
            if reference != receipt.reference:
                raise IntegrityError("certification receipt artifact digest differs")

    def is_certified(self, role_treatment: Any) -> bool:
        if not getattr(role_treatment, "enabled", False):
            return False
        candidates = [
            receipt
            for receipt in self.receipts
            if receipt.role_treatment_id == role_treatment.id
        ]
        for receipt in candidates:
            if receipt.contract_digest != self.contract_digest:
                continue
            if (
                receipt.role_treatment_identity_digest
                != role_treatment.static_identity_digest()
            ):
                continue
            if set(receipt.layer_results) != set(REQUIRED_LAYERS):
                continue
            if any(receipt.layer_results[layer] != "PASS" for layer in REQUIRED_LAYERS):
                continue
            if not all(item.matches_current_bytes() for item in receipt.executables):
                continue
            try:
                for reference in receipt.evidence_refs:
                    self.artifacts.get_bytes(reference)
                self.artifacts.get_bytes(receipt.reference)
            except IntegrityError:
                continue
            return True
        return False


@dataclass(frozen=True)
class VendorAdapter:
    harness: str
    obligation_ids: tuple[str, ...]
    command_tails: tuple[tuple[str, ...], ...]
    doctrine_files: tuple[str, ...]

    def discovery_commands(self, executable: str) -> tuple[tuple[str, ...], ...]:
        binary = _text(executable, "vendor executable")
        return tuple((binary, *tail) for tail in self.command_tails)


class VendorAdapterRegistry:
    def __init__(self, adapters: Iterable[VendorAdapter]) -> None:
        rows = tuple(adapters)
        if not rows or len({item.harness for item in rows}) != len(rows):
            raise CertificationError("vendor adapter harnesses must be nonempty and unique")
        self.adapters = {item.harness: item for item in rows}

    @classmethod
    def default(cls) -> "VendorAdapterRegistry":
        obligations = (
            "binary_identity",
            "headless_launch",
            "structured_protocol",
            "permission_boundary",
            "timeout",
            "malformed_output",
            "usage_reporting",
            "state_preservation",
            "cleanup",
            "idempotency_negative_paths",
        )
        return cls(
            (
                VendorAdapter(
                    harness="codex",
                    obligation_ids=obligations,
                    command_tails=(
                        ("--version",),
                        ("--help",),
                        ("exec", "--help"),
                    ),
                    doctrine_files=("AGENTS.md",),
                ),
                VendorAdapter(
                    harness="claude-code",
                    obligation_ids=obligations,
                    command_tails=(
                        ("--version",),
                        ("--help",),
                        ("mcp", "--help"),
                    ),
                    doctrine_files=("CLAUDE.md", "CLAUDE.local.md"),
                ),
                VendorAdapter(
                    harness="grok-build",
                    obligation_ids=obligations,
                    command_tails=(
                        ("--version",),
                        ("--help",),
                        ("inspect", "--help"),
                        ("mcp", "list"),
                    ),
                    doctrine_files=(".grok/",),
                ),
            )
        )

    def get(self, harness: str) -> VendorAdapter:
        try:
            return self.adapters[harness]
        except KeyError as exc:
            raise CertificationError(
                f"no certification adapter for harness: {harness}"
            ) from exc


@dataclass(frozen=True)
class CertificationWorkspace:
    run_id: str
    root: Path
    probe_repo: Path


@dataclass(frozen=True)
class ProbeSpec:
    check_id: str
    argv: tuple[str, ...]
    timeout_seconds: float
    max_output_bytes: int

    def __post_init__(self) -> None:
        _text(self.check_id, "probe check id")
        if any(not isinstance(item, str) or not item for item in self.argv):
            raise CertificationError("probe argv must contain nonempty strings")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise CertificationError("probe timeout must be positive")
        if (
            isinstance(self.max_output_bytes, bool)
            or not isinstance(self.max_output_bytes, int)
            or self.max_output_bytes <= 0
        ):
            raise CertificationError("probe output bound must be a positive integer")


@dataclass(frozen=True)
class ProbeResult:
    check_id: str
    status: str
    issuer: str
    argv: tuple[str, ...]
    executable: ExecutableIdentity
    timeout_seconds: float
    max_output_bytes: int
    return_code: int | None
    timed_out: bool
    stdout_ref: str
    stderr_ref: str
    latency_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "issuer": self.issuer,
            "argv": list(self.argv),
            "executable": self.executable.to_dict(),
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "stdout_ref": self.stdout_ref,
            "stderr_ref": self.stderr_ref,
            "latency_ms": self.latency_ms,
        }


class CertificationRunner:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if self.base_dir.is_symlink() or not self.base_dir.is_dir():
            raise CertificationError("certification base must be a real directory")

    @staticmethod
    def _inside_existing_repository(path: Path) -> bool:
        completed = subprocess.run(
            ["git", "-C", str(path.resolve()), "rev-parse", "--is-inside-work-tree"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return completed.returncode == 0 and completed.stdout.strip() == b"true"

    def prepare_workspace(self, harness: str) -> CertificationWorkspace:
        _text(harness, "certification harness")
        if self._inside_existing_repository(self.base_dir):
            raise CertificationError(
                "certification workspace base is inside an existing repository"
            )
        run_id = "cert-" + uuid.uuid4().hex
        root = self.base_dir / f"{run_id}-{harness}"
        root.mkdir(mode=0o700)
        os.chmod(root, 0o700)
        probe_repo = root / "probe-repo"
        probe_repo.mkdir(mode=0o700)
        git = shutil.which("git")
        if git is None:
            raise CertificationError("git is required for the disposable probe repository")
        completed = subprocess.run(
            [git, "init", "-q"],
            cwd=probe_repo,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "LC_ALL": "C",
                "TZ": "UTC",
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise CertificationError("could not initialize disposable probe repository")
        return CertificationWorkspace(run_id=run_id, root=root, probe_repo=probe_repo)

    @staticmethod
    def environment(
        requested: dict[str, str],
        *,
        allowed_names: set[str],
        secret_names: set[str],
    ) -> tuple[dict[str, str], dict[str, Any]]:
        if not isinstance(requested, dict):
            raise SensitiveDataError("certification environment must be an object")
        if allowed_names & secret_names:
            raise SensitiveDataError("public and secret environment names overlap")
        permitted = allowed_names | secret_names
        unknown = set(requested) - permitted
        if unknown:
            raise SensitiveDataError(
                f"undeclared certification environment fields: {sorted(unknown)}"
            )
        if any(
            not isinstance(name, str)
            or not name
            or "=" in name
            or "\x00" in name
            or not isinstance(value, str)
            or "\x00" in value
            for name, value in requested.items()
        ):
            raise SensitiveDataError("certification environment contains invalid data")
        result = dict(requested)
        evidence = {
            "names": sorted(requested),
            "secret_names": sorted(set(requested) & secret_names),
            "value_digests": {
                name: _digest(value.encode("utf-8"))
                for name, value in sorted(requested.items())
                if name not in secret_names
            },
        }
        return result, evidence

    @staticmethod
    def _safe_stream(value: bytes) -> bytes:
        from .evidence import RawExecutionCustodian

        safe, _ = RawExecutionCustodian._redact(value)
        return safe.encode("utf-8")

    def run_probe(
        self,
        *,
        workspace: CertificationWorkspace,
        artifacts: ArtifactStore,
        executable: Path,
        spec: ProbeSpec,
        environment: dict[str, str],
    ) -> ProbeResult:
        resolved = ExecutableIdentity.observe(
            Path(executable), version="unreported"
        )
        command = (resolved.path, *spec.argv)
        effective_environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LC_ALL": "C",
            "TZ": "UTC",
            **environment,
        }
        started = time.monotonic()
        return_code: int | None
        timed_out = False
        try:
            return_code, stdout, stderr, _ = run_bounded(
                command,
                b"",
                workspace=workspace.probe_repo,
                environment=effective_environment,
                timeout_seconds=spec.timeout_seconds,
                max_output_bytes=spec.max_output_bytes,
            )
            status = "PASS" if return_code == 0 else "FAIL"
        except HarnessTimeoutError as exc:
            return_code = None
            stdout = exc.stdout
            stderr = exc.stderr
            timed_out = True
            status = "FAIL"
        except HarnessOutputLimitError as exc:
            return_code = None
            stdout = exc.stdout
            stderr = exc.stderr
            status = "FAIL"
        latency_ms = int((time.monotonic() - started) * 1000)
        stdout_ref = artifacts.put_bytes(
            self._safe_stream(stdout), media_type="text/plain"
        )
        stderr_ref = artifacts.put_bytes(
            self._safe_stream(stderr), media_type="text/plain"
        )
        version_line = (
            stdout.decode("utf-8", errors="replace").splitlines()[0]
            if stdout.strip()
            else "unreported"
        )
        observed = ExecutableIdentity(
            path=resolved.path,
            sha256=resolved.sha256,
            version=version_line,
        )
        return ProbeResult(
            check_id=spec.check_id,
            status=status,
            issuer=ISSUER,
            argv=command,
            executable=observed,
            timeout_seconds=spec.timeout_seconds,
            max_output_bytes=spec.max_output_bytes,
            return_code=return_code,
            timed_out=timed_out,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            latency_ms=latency_ms,
        )


class ExternalStateGuard:
    def __init__(self, targets: Iterable[Path]) -> None:
        rows = tuple(Path(item) for item in targets)
        if not rows or len({item.resolve() for item in rows}) != len(rows):
            raise CertificationError("guard targets must be nonempty and unique")
        if any(item.is_symlink() for item in rows):
            raise CertificationError("external state guard refuses symlink targets")
        self.targets = rows
        self._baseline: dict[Path, tuple[bool, bytes, int]] = {}
        self.restoration_verified = False

    def __enter__(self) -> "ExternalStateGuard":
        for path in self.targets:
            if path.exists() and not path.is_file():
                raise CertificationError(
                    f"external state target is not a regular file: {path}"
                )
            self._baseline[path] = (
                path.exists(),
                path.read_bytes() if path.exists() else b"",
                path.stat().st_mode & 0o777 if path.exists() else 0o600,
            )
        return self

    def restore(self) -> None:
        if not self._baseline:
            raise CertificationError("external state baseline was not captured")
        for path, (existed, content, mode) in self._baseline.items():
            if existed:
                path.parent.mkdir(parents=True, exist_ok=True)
                descriptor = os.open(
                    path,
                    os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                    mode,
                )
                try:
                    os.write(descriptor, content)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                os.chmod(path, mode)
            elif path.exists():
                if not path.is_file() or path.is_symlink():
                    raise CertificationError(
                        f"guard refuses to remove unexpected state type: {path}"
                    )
                path.unlink()
        self.restoration_verified = all(
            (
                path.exists() == existed
                and (
                    not existed
                    or (
                        path.is_file()
                        and not path.is_symlink()
                        and path.read_bytes() == content
                        and path.stat().st_mode & 0o777 == mode
                    )
                )
            )
            for path, (existed, content, mode) in self._baseline.items()
        )
        if not self.restoration_verified:
            raise CertificationError("external state restoration did not match baseline")

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self.restore()
        return False


class CertificationEvaluator:
    def __init__(self, contract: CertificationContract) -> None:
        self.contract = contract

    @staticmethod
    def _observation_status(value: Any, label: str) -> str:
        result = _text(value, label)
        if result not in STATUSES:
            raise CertificationError(f"{label} is not a certification status")
        return result

    @staticmethod
    def _evidence_refs(value: Any, label: str) -> tuple[str, ...]:
        return tuple(
            _digest_ref(item, label)
            for item in _string_list(value, label)
        )

    @staticmethod
    def _aggregate(statuses: Iterable[str]) -> str:
        rows = tuple(statuses)
        if not rows:
            raise CertificationError("certification evaluation has no observations")
        if all(item == "PASS" for item in rows):
            return "PASS"
        for status in ("FAIL", "BLOCKED", "WARN", "INFO", "SKIP"):
            if status in rows:
                return status
        raise CertificationError("certification evaluation contains an unknown status")

    def evaluate_mechanical(self, observations: Iterable[dict[str, Any]]) -> str:
        rows = tuple(observations)
        expected = self.contract.mechanical_obligation_ids
        observed: dict[str, str] = {}
        for raw in rows:
            row = _exact(
                raw,
                {
                    "obligation_id",
                    "status",
                    "probe_result_refs",
                    "finding_ids",
                },
                "mechanical observation",
            )
            obligation_id = _text(
                row["obligation_id"], "mechanical observation obligation"
            )
            if obligation_id in observed:
                raise CertificationError(
                    f"duplicate mechanical observation: {obligation_id}"
                )
            self._evidence_refs(
                row["probe_result_refs"], "mechanical probe result references"
            )
            findings = _string_list(
                row["finding_ids"], "mechanical finding ids", nonempty=False
            )
            status = self._observation_status(
                row["status"], "mechanical observation status"
            )
            if findings and status == "PASS":
                raise CertificationError(
                    "mechanical observation with findings cannot report PASS"
                )
            observed[obligation_id] = status
        if tuple(observed) != expected or set(observed) != set(expected):
            raise CertificationError(
                "mechanical observations must cover the ordered contract obligations"
            )
        return self._aggregate(observed.values())

    def evaluate_inference(self, observations: Iterable[dict[str, Any]]) -> str:
        rows = tuple(observations)
        expected = self.contract.inference_task_ids
        observed: dict[str, str] = {}
        lineages: set[str] = set()
        for raw in rows:
            row = _exact(
                raw,
                {
                    "task_id",
                    "status",
                    "context_lineage",
                    "calls",
                    "retries",
                    "friction",
                    "evidence_refs",
                },
                "inference observation",
            )
            task_id = _text(row["task_id"], "inference task id")
            if task_id in observed:
                raise CertificationError(f"duplicate inference task: {task_id}")
            lineage = _text(row["context_lineage"], "inference context lineage")
            if lineage in lineages:
                raise CertificationError(
                    "inference tasks must use distinct fresh context lineages"
                )
            lineages.add(lineage)
            calls = row["calls"]
            if not isinstance(calls, list) or not calls:
                raise CertificationError(
                    f"inference task {task_id} requires a machine-owned call log"
                )
            for call in calls:
                call_row = _exact(
                    call, {"name", "params", "status"}, "inference call"
                )
                _text(call_row["name"], "inference call name")
                if not isinstance(call_row["params"], dict):
                    raise CertificationError("inference call params must be an object")
                self._observation_status(
                    call_row["status"], "inference call status"
                )
            retries = row["retries"]
            if (
                isinstance(retries, bool)
                or not isinstance(retries, int)
                or retries < 0
            ):
                raise CertificationError("inference retries must be nonnegative")
            friction = _string_list(
                row["friction"], "inference friction", nonempty=False
            )
            del friction
            self._evidence_refs(
                row["evidence_refs"], "inference evidence references"
            )
            observed[task_id] = self._observation_status(
                row["status"], "inference task status"
            )
        if tuple(observed) != expected or set(observed) != set(expected):
            raise CertificationError(
                "inference observations must cover the ordered T0 through T8 contract"
            )
        return self._aggregate(observed.values())

    def evaluate_mutation(self, data: dict[str, Any]) -> str:
        row = _exact(
            data,
            {
                "baseline_digest",
                "final_digest",
                "mutation_observed",
                "verification_ran",
                "restoration_verified",
            },
            "mutation evidence",
        )
        baseline = _digest_ref(row["baseline_digest"], "mutation baseline digest")
        final = _digest_ref(row["final_digest"], "mutation final digest")
        for field in (
            "mutation_observed",
            "verification_ran",
            "restoration_verified",
        ):
            if not isinstance(row[field], bool):
                raise CertificationError(f"{field} must be boolean")
        return (
            "PASS"
            if baseline == final
            and row["mutation_observed"]
            and row["verification_ran"]
            and row["restoration_verified"]
            else "FAIL"
        )


class ConformanceEvaluator:
    def __init__(self, contract: CertificationContract) -> None:
        self.contract = contract

    def evaluate(self, observation: dict[str, Any]) -> str:
        expected = set(self.contract.conformance_obligations)
        row = _exact(observation, expected, "Loopstrap conformance observation")
        for obligation in self.contract.conformance_obligations:
            value = row[obligation]
            if obligation == "execution_ref":
                _digest_ref(value, "conformance execution reference")
            elif not isinstance(value, bool):
                raise CertificationError(
                    f"conformance obligation {obligation} must be boolean"
                )
        return (
            "PASS"
            if all(
                row[obligation]
                for obligation in self.contract.conformance_obligations
                if obligation != "execution_ref"
            )
            else "FAIL"
        )


@dataclass(frozen=True)
class UsageCharge:
    dispatch_id: str
    usage_digest: str
    usage: ResourceUsage
    unavailable_fields: tuple[str, ...]
    latency_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "dispatch_id": self.dispatch_id,
            "usage_digest": self.usage_digest,
            "usage": self.usage.to_dict(),
            "unavailable_fields": list(self.unavailable_fields),
            "latency_ms": self.latency_ms,
        }


class UsageChargeLedger:
    _TOKEN_FIELDS = ("input_tokens", "output_tokens")
    _OPTIONAL_FIELDS = {
        "cost": "money",
        "compute": "compute",
        "retries": "retries",
        "risk": "risk",
        "human_attention": "human_attention",
    }

    def __init__(self) -> None:
        self._budget = BudgetLedger()
        self._charges: dict[str, UsageCharge] = {}

    @staticmethod
    def _nonnegative(
        value: Any,
        *,
        label: str,
        integer: bool,
    ) -> int | float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise CertificationError(f"{label} must be nonnegative or unavailable")
        if integer:
            if not isinstance(value, int) or value < 0:
                raise CertificationError(
                    f"{label} must be a nonnegative integer or unavailable"
                )
            return value
        if not isinstance(value, (int, float)) or value < 0:
            raise CertificationError(f"{label} must be nonnegative or unavailable")
        return float(value)

    def charge(
        self,
        *,
        dispatch_id: str,
        usage: dict[str, Any],
        latency_ms: int,
    ) -> UsageCharge:
        dispatch_id = _text(dispatch_id, "usage dispatch id")
        if not isinstance(usage, dict):
            raise CertificationError("reported usage must be an object")
        if (
            isinstance(latency_ms, bool)
            or not isinstance(latency_ms, int)
            or latency_ms < 0
        ):
            raise CertificationError("usage latency must be a nonnegative integer")
        usage_digest = _digest(
            canonical_json({"usage": usage, "latency_ms": latency_ms})
        )
        existing = self._charges.get(dispatch_id)
        if existing is not None:
            if existing.usage_digest != usage_digest:
                raise IdempotencyError(
                    "dispatch usage was reused with different reported values"
                )
            return existing

        unavailable: list[str] = []
        token_values: list[int] = []
        for field in self._TOKEN_FIELDS:
            value = self._nonnegative(
                usage.get(field), label=field, integer=True
            )
            if value is None:
                unavailable.append(field)
            else:
                token_values.append(int(value))
        values: dict[str, int | float] = {
            "tokens": sum(token_values),
            "latency_seconds": latency_ms / 1000.0,
        }
        for source, target in self._OPTIONAL_FIELDS.items():
            value = self._nonnegative(
                usage.get(source),
                label=source,
                integer=target == "retries",
            )
            if value is None:
                unavailable.append(source)
            else:
                values[target] = value
        charge = UsageCharge(
            dispatch_id=dispatch_id,
            usage_digest=usage_digest,
            usage=ResourceUsage(**values),
            unavailable_fields=tuple(sorted(unavailable)),
            latency_ms=latency_ms,
        )
        charge.usage.validate()
        self._budget.charge(charge.usage)
        self._charges[dispatch_id] = charge
        return charge

    def totals(self) -> ResourceUsage:
        return self._budget.totals()

    def charge_for(self, dispatch_id: str) -> UsageCharge | None:
        return self._charges.get(dispatch_id)
