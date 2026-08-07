from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time
from typing import Any, Protocol, TYPE_CHECKING

from .atomic import canonical_json
from .errors import (
    HarnessExecutionError,
    HarnessInterruptedError,
    HarnessOutputLimitError,
    HarnessProtocolError,
    HarnessTimeoutError,
    IndependenceError,
    LiveHarnessDisabledError,
    SchemaError,
    SensitiveDataError,
    StaleResultError,
    RoleTreatmentUnavailableError,
)

if TYPE_CHECKING:
    from .certification import CertificationAuthority


def _exact_object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        missing = fields - set(value) if isinstance(value, dict) else fields
        unknown = set(value) - fields if isinstance(value, dict) else set()
        raise SchemaError(
            f"{label} fields invalid: missing={sorted(missing)} "
            f"unknown={sorted(unknown)}"
        )
    return value


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaError(f"{label} must be a nonempty string")
    return value


def _unique_strings(
    value: Any, label: str, *, nonempty: bool = False
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise SchemaError(f"{label} must be a valid string list")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise SchemaError(f"{label} must contain unique values")
    return result


def _string_vector(
    value: Any, label: str, *, nonempty: bool = False
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise SchemaError(f"{label} must be a valid string list")
    return tuple(value)


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    selector: str
    allowed_resolved_models: tuple[str, ...]
    fallback_policy: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelRoute":
        row = _exact_object(
            data,
            {
                "provider",
                "selector",
                "allowed_resolved_models",
                "fallback_policy",
            },
            "model route",
        )
        policy = _nonempty_text(row["fallback_policy"], "model fallback policy")
        if policy != "deny":
            raise SchemaError("only deny is supported as a model fallback policy")
        return cls(
            provider=_nonempty_text(row["provider"], "model provider"),
            selector=_nonempty_text(row["selector"], "model selector"),
            allowed_resolved_models=_unique_strings(
                row["allowed_resolved_models"],
                "allowed resolved models",
                nonempty=True,
            ),
            fallback_policy=policy,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "selector": self.selector,
            "allowed_resolved_models": list(self.allowed_resolved_models),
            "fallback_policy": self.fallback_policy,
        }


@dataclass(frozen=True)
class ReasoningControl:
    control: str
    requested: str
    expected_wire: str
    orchestration: str
    proof_sources: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReasoningControl":
        row = _exact_object(
            data,
            {
                "control",
                "requested",
                "expected_wire",
                "orchestration",
                "proof_sources",
            },
            "reasoning control",
        )
        sources = _unique_strings(
            row["proof_sources"], "reasoning proof sources", nonempty=True
        )
        if not set(sources).issubset(
            {"runtime_event", "certified_binary_mapping"}
        ):
            raise SchemaError("reasoning proof source is unsupported")
        return cls(
            control=_nonempty_text(row["control"], "reasoning control"),
            requested=_nonempty_text(row["requested"], "requested reasoning"),
            expected_wire=_nonempty_text(
                row["expected_wire"], "expected wire reasoning"
            ),
            orchestration=_nonempty_text(
                row["orchestration"], "reasoning orchestration"
            ),
            proof_sources=sources,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "control": self.control,
            "requested": self.requested,
            "expected_wire": self.expected_wire,
            "orchestration": self.orchestration,
            "proof_sources": list(self.proof_sources),
        }


@dataclass(frozen=True)
class WrapperIdentity:
    id: str
    version: str
    vendor_executable: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WrapperIdentity":
        row = _exact_object(
            data, {"id", "version", "vendor_executable"}, "wrapper identity"
        )
        return cls(
            id=_nonempty_text(row["id"], "wrapper id"),
            version=_nonempty_text(row["version"], "wrapper version"),
            vendor_executable=_nonempty_text(
                row["vendor_executable"], "vendor executable"
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "version": self.version,
            "vendor_executable": self.vendor_executable,
        }


@dataclass(frozen=True)
class RoleTreatment:
    id: str
    role: str
    harness: str
    model_route: ModelRoute
    reasoning: ReasoningControl
    wrapper: WrapperIdentity
    configuration: dict[str, Any]
    capabilities: tuple[str, ...]
    enabled: bool
    command: tuple[str, ...]

    FIELDS = {
        "id",
        "role",
        "harness",
        "model_route",
        "reasoning",
        "wrapper",
        "configuration",
        "capabilities",
        "enabled",
        "command",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoleTreatment":
        row = _exact_object(data, cls.FIELDS, "Role-Treatment")
        command = _string_vector(
            row["command"], "Role-Treatment command", nonempty=True
        )
        capabilities = _unique_strings(
            row["capabilities"], "Role-Treatment capabilities"
        )
        if not isinstance(row["configuration"], dict):
            raise SchemaError("Role-Treatment configuration must be an object")
        if not isinstance(row["enabled"], bool):
            raise SchemaError("Role-Treatment enablement must be a boolean")
        wrapper = WrapperIdentity.from_dict(row["wrapper"])
        if command[0] != wrapper.id:
            raise SchemaError("Role-Treatment command must start with its wrapper id")
        return cls(
            id=_nonempty_text(row["id"], "Role-Treatment id"),
            role=_nonempty_text(row["role"], "Role"),
            harness=_nonempty_text(row["harness"], "harness"),
            model_route=ModelRoute.from_dict(row["model_route"]),
            reasoning=ReasoningControl.from_dict(row["reasoning"]),
            wrapper=wrapper,
            configuration=dict(row["configuration"]),
            capabilities=capabilities,
            enabled=row["enabled"],
            command=command,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "harness": self.harness,
            "model_route": self.model_route.to_dict(),
            "reasoning": self.reasoning.to_dict(),
            "wrapper": self.wrapper.to_dict(),
            "configuration": self.configuration,
            "capabilities": list(self.capabilities),
            "enabled": self.enabled,
            "command": list(self.command),
        }

    def effective_identity(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.to_dict().items()
            if key not in {"enabled", "command"}
        }

    def static_identity(self) -> dict[str, Any]:
        return {**self.effective_identity(), "command": list(self.command)}

    def static_identity_digest(self) -> str:
        import hashlib

        return "sha256:" + hashlib.sha256(
            canonical_json(self.static_identity())
        ).hexdigest()


class RoleTreatmentRegistry:
    def __init__(
        self, version: int, role_treatments: dict[str, RoleTreatment]
    ) -> None:
        self.version = version
        self.role_treatments = role_treatments

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoleTreatmentRegistry":
        if not isinstance(data, dict):
            raise SchemaError("Role-Treatment registry must be an object")
        if set(data) != {"version", "role_treatments"}:
            raise SchemaError(
                "Role-Treatment registry requires version and role_treatments"
            )
        if (
            isinstance(data["version"], bool)
            or not isinstance(data["version"], int)
            or data["version"] < 1
        ):
            raise SchemaError("Role-Treatment registry version must be positive")
        if not isinstance(data["role_treatments"], list):
            raise SchemaError("Role-Treatment registry entries must be a list")
        rows = [
            RoleTreatment.from_dict(row) for row in data["role_treatments"]
        ]
        if not rows or len({row.id for row in rows}) != len(rows):
            raise SchemaError("Role-Treatment ids must be nonempty and unique")
        return cls(data["version"], {row.id: row for row in rows})

    def get(self, role_treatment_id: str) -> RoleTreatment:
        try:
            return self.role_treatments[role_treatment_id]
        except KeyError as exc:
            raise SchemaError(
                f"unknown Role-Treatment: {role_treatment_id}"
            ) from exc


@dataclass(frozen=True)
class Assignment:
    role: str
    role_treatment_id: str
    context_lineage: str


@dataclass(frozen=True)
class IndependenceRule:
    role: str
    from_role: str
    different_role_treatment: bool
    different_context_lineage: bool


class RoleRouter:
    def __init__(
        self,
        *,
        version: int,
        registry: RoleTreatmentRegistry,
        roles: dict[str, dict[str, Any]],
        independence: tuple[IndependenceRule, ...],
        certification_authority: "CertificationAuthority | None",
    ) -> None:
        self.version = version
        self.registry = registry
        self.roles = roles
        self.independence = independence
        self.certification_authority = certification_authority

    @classmethod
    def from_dict(
        cls,
        registry: RoleTreatmentRegistry,
        data: dict[str, Any],
        *,
        certification_authority: "CertificationAuthority | None" = None,
    ) -> "RoleRouter":
        if not isinstance(data, dict):
            raise SchemaError("role policy must be an object")
        allowed = {"version", "roles", "independence"}
        if set(data) - allowed or not {"version", "roles"}.issubset(data):
            raise SchemaError("role policy fields are invalid")
        if (
            isinstance(data["version"], bool)
            or not isinstance(data["version"], int)
            or data["version"] < 1
        ):
            raise SchemaError("role policy version must be positive")
        if not isinstance(data["roles"], dict):
            raise SchemaError("role assignments must be an object")
        roles: dict[str, dict[str, Any]] = {}
        for role, row in data["roles"].items():
            if not isinstance(role, str) or not role:
                raise SchemaError("role names must be nonempty strings")
            if (
                not isinstance(row, dict)
                or "role_treatment" not in row
                or set(row) - {"role_treatment", "requires"}
            ):
                raise SchemaError(f"role policy invalid for {role}")
            role_treatment_id = row["role_treatment"]
            if not isinstance(role_treatment_id, str) or not role_treatment_id:
                raise SchemaError(
                    f"Role-Treatment must be a nonempty string for {role}"
                )
            role_treatment = registry.get(role_treatment_id)
            if role_treatment.role != role:
                raise SchemaError(
                    f"Role-Treatment {role_treatment_id} belongs to "
                    f"{role_treatment.role}, not {role}"
                )
            raw_requires = row.get("requires", [])
            requires = _unique_strings(
                raw_requires, f"role capabilities for {role}"
            )
            roles[role] = {
                "role_treatment": role_treatment_id,
                "requires": requires,
            }
        raw_rules = data.get("independence", [])
        if not isinstance(raw_rules, list):
            raise SchemaError("independence rules must be a list")
        rules_list: list[IndependenceRule] = []
        rule_fields = {
            "role",
            "from_role",
            "different_role_treatment",
            "different_context_lineage",
        }
        for row in raw_rules:
            if not isinstance(row, dict) or set(row) != rule_fields:
                raise SchemaError("independence rule fields are invalid")
            if (
                not isinstance(row["role"], str)
                or not row["role"]
                or not isinstance(row["from_role"], str)
                or not row["from_role"]
            ):
                raise SchemaError("independence role names must be nonempty strings")
            if not isinstance(
                row["different_role_treatment"], bool
            ) or not isinstance(row["different_context_lineage"], bool):
                raise SchemaError("independence requirements must be booleans")
            if not (
                row["different_role_treatment"]
                or row["different_context_lineage"]
            ):
                raise SchemaError(
                    "independence rule must require an independent dimension"
                )
            rules_list.append(
                IndependenceRule(
                    role=row["role"],
                    from_role=row["from_role"],
                    different_role_treatment=row[
                        "different_role_treatment"
                    ],
                    different_context_lineage=row[
                        "different_context_lineage"
                    ],
                )
            )
        rule_keys = [(rule.role, rule.from_role) for rule in rules_list]
        if len(set(rule_keys)) != len(rule_keys):
            raise SchemaError("independence role pairs must be unique")
        return cls(
            version=data["version"],
            registry=registry,
            roles=roles,
            independence=tuple(rules_list),
            certification_authority=certification_authority,
        )

    def resolve(
        self,
        role: str,
        *,
        assignments: list[Assignment],
        context_lineage: str | None = None,
    ) -> RoleTreatment:
        try:
            policy = self.roles[role]
        except KeyError as exc:
            raise SchemaError(
                f"role has no configured Role-Treatment: {role}"
            ) from exc
        role_treatment = self.registry.get(policy["role_treatment"])
        if not role_treatment.enabled:
            raise RoleTreatmentUnavailableError(role_treatment.id)
        if (
            self.certification_authority is None
            or not self.certification_authority.is_certified(role_treatment)
        ):
            raise RoleTreatmentUnavailableError(role_treatment.id)
        missing_capabilities = set(policy["requires"]) - set(
            role_treatment.capabilities
        )
        if missing_capabilities:
            raise RoleTreatmentUnavailableError(role_treatment.id)
        for rule in self.independence:
            if rule.role != role:
                continue
            prior = [item for item in assignments if item.role == rule.from_role]
            for assignment in prior:
                if (
                    rule.different_role_treatment
                    and assignment.role_treatment_id == role_treatment.id
                ):
                    raise IndependenceError(
                        f"{role} must use a different Role-Treatment "
                        f"from {rule.from_role}"
                    )
                if (
                    rule.different_context_lineage
                    and context_lineage is not None
                    and assignment.context_lineage == context_lineage
                ):
                    raise IndependenceError(
                        f"{role} must use a different context lineage "
                        f"from {rule.from_role}"
                    )
        return role_treatment


@dataclass
class Invocation:
    invocation_id: str
    run_id: str
    cell_id: str
    cell_revision: int
    role: str
    prompt_ref: str
    context_manifest_ref: str
    context_lineage: str
    cache_lineage: str | None
    workspace: Path
    timeout_seconds: float
    max_output_bytes: int
    environment: dict[str, str]


@dataclass(frozen=True)
class ProcessTrace:
    argv: tuple[str, ...]
    cwd: str
    environment_keys: tuple[str, ...]
    environment_value_digests: dict[str, str]
    pid: int | None
    started_at: str
    ended_at: str
    started_monotonic_ns: int
    ended_monotonic_ns: int
    duration_ns: int
    timeout_seconds: float
    max_output_bytes: int
    return_code: int | None
    termination: str
    stdout_bytes: int
    stderr_bytes: int
    stdout_sha256: str
    stderr_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "argv": list(self.argv),
            "cwd": self.cwd,
            "environment_keys": list(self.environment_keys),
            "environment_value_digests": dict(self.environment_value_digests),
            "pid": self.pid,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "started_monotonic_ns": self.started_monotonic_ns,
            "ended_monotonic_ns": self.ended_monotonic_ns,
            "duration_ns": self.duration_ns,
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
            "return_code": self.return_code,
            "termination": self.termination,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
        }


class ExecutionCustodian(Protocol):
    def retain(self, *, stdout: bytes, stderr: bytes) -> Any:
        ...


@dataclass(frozen=True)
class InvocationResult:
    invocation_id: str
    cell_revision: int
    status: str
    requested_role_treatment: dict[str, Any]
    launch_attestation: dict[str, Any]
    artifacts: tuple[dict[str, Any], ...]
    claims: tuple[dict[str, Any], ...]
    usage: dict[str, Any]
    cache_lineage: str | None
    prompt_ref: str
    context_manifest_ref: str
    context_lineage: str
    latency_ms: int
    execution_ref: str | None
    raw_redaction_count: int
    process_trace: dict[str, Any]

    def evidence(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "cell_revision": self.cell_revision,
            "status": self.status,
            "requested_role_treatment": self.requested_role_treatment,
            "launch_attestation": self.launch_attestation,
            "artifacts": list(self.artifacts),
            "claims": list(self.claims),
            "usage": self.usage,
            "cache_lineage": self.cache_lineage,
            "prompt_ref": self.prompt_ref,
            "context_manifest_ref": self.context_manifest_ref,
            "context_lineage": self.context_lineage,
            "latency_ms": self.latency_ms,
            "execution_ref": self.execution_ref,
            "raw_redaction_count": self.raw_redaction_count,
            "process_trace": self.process_trace,
        }


class HarnessDispatcher:
    def __init__(
        self,
        *,
        allow_live: bool = False,
        execution_custodian: ExecutionCustodian | None = None,
    ) -> None:
        self.allow_live = allow_live
        self.execution_custodian = execution_custodian

    @staticmethod
    def _environment(requested: dict[str, str]) -> dict[str, str]:
        result = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LC_ALL": "C",
            "TZ": "UTC",
        }
        forbidden = {
            "GH_TOKEN",
            "GITHUB_TOKEN",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "XAI_API_KEY",
        }
        for key, value in requested.items():
            if key in forbidden or any(part in key.upper() for part in ("SECRET", "TOKEN", "PASSWORD")):
                raise SensitiveDataError(f"credential environment field rejected: {key}")
            if not key or "=" in key or "\x00" in key or "\x00" in value:
                raise HarnessProtocolError(f"invalid environment entry: {key!r}")
            result[key] = value
        return result

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()

    @staticmethod
    def _process_trace(
        command: tuple[str, ...],
        *,
        workspace: Path,
        environment: dict[str, str],
        pid: int | None,
        started_at: str,
        started_monotonic_ns: int,
        return_code: int | None,
        termination: str,
        stdout: bytes,
        stderr: bytes,
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> ProcessTrace:
        ended_monotonic_ns = time.monotonic_ns()
        return ProcessTrace(
            argv=command,
            cwd=str(Path(workspace)),
            environment_keys=tuple(sorted(environment)),
            environment_value_digests={
                key: hashlib.sha256(value.encode("utf-8")).hexdigest()
                for key, value in sorted(environment.items())
            },
            pid=pid,
            started_at=started_at,
            ended_at=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            started_monotonic_ns=started_monotonic_ns,
            ended_monotonic_ns=ended_monotonic_ns,
            duration_ns=ended_monotonic_ns - started_monotonic_ns,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            return_code=return_code,
            termination=termination,
            stdout_bytes=len(stdout),
            stderr_bytes=len(stderr),
            stdout_sha256=hashlib.sha256(stdout).hexdigest(),
            stderr_sha256=hashlib.sha256(stderr).hexdigest(),
        )

    @classmethod
    def _run_bounded(
        cls,
        command: tuple[str, ...],
        request: bytes,
        *,
        workspace: Path,
        environment: dict[str, str],
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> tuple[int, bytes, bytes, ProcessTrace]:
        started_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        started_monotonic_ns = time.monotonic_ns()
        try:
            process = subprocess.Popen(
                list(command),
                cwd=workspace,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except BaseException as exc:
            error = HarnessInterruptedError("harness process could not start")
            error.process_trace = cls._process_trace(
                command,
                workspace=workspace,
                environment=environment,
                pid=None,
                started_at=started_at,
                started_monotonic_ns=started_monotonic_ns,
                return_code=None,
                termination="spawn_error",
                stdout=b"",
                stderr=b"",
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            ).to_dict()
            raise error from exc
        assert process.stdin is not None and process.stdout is not None and process.stderr is not None
        output = bytearray()
        errors = bytearray()
        try:
            process.stdin.write(request)
            process.stdin.close()
        except BaseException as exc:
            cls._terminate(process)
            process.stdout.close()
            process.stderr.close()
            error = HarnessInterruptedError(
                "harness input stream was interrupted",
                stdout=bytes(output),
                stderr=bytes(errors),
            )
            error.process_trace = cls._process_trace(
                command,
                workspace=workspace,
                environment=environment,
                pid=process.pid,
                started_at=started_at,
                started_monotonic_ns=started_monotonic_ns,
                return_code=process.returncode,
                termination="input_interrupted",
                stdout=bytes(output),
                stderr=bytes(errors),
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            ).to_dict()
            raise error from exc
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        deadline = time.monotonic() + timeout_seconds
        trace: ProcessTrace | None = None
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    cls._terminate(process)
                    raise HarnessTimeoutError(
                        f"harness exceeded {timeout_seconds} seconds",
                        stdout=bytes(output),
                        stderr=bytes(errors),
                    )
                for key, _ in selector.select(min(remaining, 0.05)):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    target = output if key.data == "stdout" else errors
                    target.extend(chunk)
                    if (
                        len(output) > max_output_bytes
                        or len(errors) > max_output_bytes
                    ):
                        cls._terminate(process)
                        raise HarnessOutputLimitError(
                            f"harness output exceeded {max_output_bytes} bytes",
                            stdout=bytes(output),
                            stderr=bytes(errors),
                        )
            remaining = deadline - time.monotonic()
            try:
                return_code = process.wait(timeout=max(remaining, 0.001))
            except subprocess.TimeoutExpired as exc:
                cls._terminate(process)
                raise HarnessTimeoutError(
                    f"harness exceeded {timeout_seconds} seconds",
                    stdout=bytes(output),
                    stderr=bytes(errors),
                ) from exc
        except HarnessExecutionError as exc:
            exc.process_trace = cls._process_trace(
                command,
                workspace=workspace,
                environment=environment,
                pid=process.pid,
                started_at=started_at,
                started_monotonic_ns=started_monotonic_ns,
                return_code=process.returncode,
                termination=type(exc).__name__,
                stdout=bytes(output),
                stderr=bytes(errors),
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            ).to_dict()
            raise
        except BaseException as exc:
            cls._terminate(process)
            error = HarnessInterruptedError(
                "harness execution was interrupted",
                stdout=bytes(output),
                stderr=bytes(errors),
            )
            error.process_trace = cls._process_trace(
                command,
                workspace=workspace,
                environment=environment,
                pid=process.pid,
                started_at=started_at,
                started_monotonic_ns=started_monotonic_ns,
                return_code=process.returncode,
                termination="interrupted",
                stdout=bytes(output),
                stderr=bytes(errors),
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            ).to_dict()
            raise error from exc
        finally:
            selector.close()
            process.stdout.close()
            process.stderr.close()
        trace = cls._process_trace(
            command,
            workspace=workspace,
            environment=environment,
            pid=process.pid,
            started_at=started_at,
            started_monotonic_ns=started_monotonic_ns,
            return_code=return_code,
            termination="completed",
            stdout=bytes(output),
            stderr=bytes(errors),
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        )
        return return_code, bytes(output), bytes(errors), trace

    def dispatch(
        self,
        role_treatment: RoleTreatment,
        invocation: Invocation,
        *,
        live: bool = False,
        require_live: bool = False,
    ) -> InvocationResult:
        if live and not self.allow_live:
            raise LiveHarnessDisabledError("live harness execution is not enabled")
        if require_live and not live:
            raise LiveHarnessDisabledError("this check requires explicit live execution")
        if not role_treatment.enabled:
            raise RoleTreatmentUnavailableError(role_treatment.id)
        workspace = Path(invocation.workspace)
        if not workspace.is_dir() or workspace.is_symlink():
            raise HarnessProtocolError("invocation workspace is unavailable")
        if invocation.timeout_seconds <= 0 or invocation.max_output_bytes <= 0:
            raise HarnessProtocolError("invocation bounds must be positive")
        requested_role_treatment = role_treatment.effective_identity()
        request_value = {
            "invocation_id": invocation.invocation_id,
            "run_id": invocation.run_id,
            "cell_id": invocation.cell_id,
            "cell_revision": invocation.cell_revision,
            "role": invocation.role,
            "prompt_ref": invocation.prompt_ref,
            "context_manifest_ref": invocation.context_manifest_ref,
            "context_lineage": invocation.context_lineage,
            "cache_lineage": invocation.cache_lineage,
            "requested_role_treatment": requested_role_treatment,
            "role_treatment_command": list(role_treatment.command),
        }
        started = time.monotonic()
        try:
            return_code, stdout, stderr, process_trace = self._run_bounded(
                role_treatment.command,
                canonical_json(request_value),
                workspace=workspace,
                environment=self._environment(invocation.environment),
                timeout_seconds=invocation.timeout_seconds,
                max_output_bytes=invocation.max_output_bytes,
            )
        except HarnessExecutionError as exc:
            if self.execution_custodian is not None:
                raw_record = self.execution_custodian.retain(
                    stdout=exc.stdout,
                    stderr=exc.stderr,
                )
                exc.execution_ref = str(raw_record.artifact_ref)
                exc.raw_redaction_count = int(raw_record.redaction_count)
            raise
        latency_ms = int((time.monotonic() - started) * 1000)
        raw_record = (
            self.execution_custodian.retain(stdout=stdout, stderr=stderr)
            if self.execution_custodian is not None
            else None
        )

        def protocol_error(message: str) -> HarnessProtocolError:
            error = HarnessProtocolError(
                message,
                stdout=stdout,
                stderr=stderr,
            )
            error.process_trace = process_trace.to_dict()
            if raw_record is not None:
                error.execution_ref = str(raw_record.artifact_ref)
                error.raw_redaction_count = int(raw_record.redaction_count)
            return error

        if return_code != 0:
            raise protocol_error(
                f"harness exited {return_code}; stderr_bytes={len(stderr)}"
            )
        if not stdout.strip():
            raise protocol_error("harness returned empty output")
        try:
            response = json.loads(stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise protocol_error("harness output is not one JSON value") from exc
        required_fields = {
            "invocation_id",
            "cell_revision",
            "status",
            "launch_attestation",
            "artifacts",
            "claims",
            "usage",
            "cache_lineage",
        }
        if not isinstance(response, dict) or set(response) != required_fields:
            raise protocol_error("harness response fields are invalid")
        if response["invocation_id"] != invocation.invocation_id:
            raise protocol_error(
                "harness response invocation id mismatches request"
            )
        if response["cell_revision"] != invocation.cell_revision:
            error = StaleResultError(
                "harness response is for a stale cell revision"
            )
            error.process_trace = process_trace.to_dict()
            error.execution_ref = (
                str(raw_record.artifact_ref) if raw_record is not None else None
            )
            error.raw_redaction_count = (
                int(raw_record.redaction_count) if raw_record is not None else 0
            )
            raise error
        if response["status"] != "completed":
            raise protocol_error(
                f"harness did not complete: {response['status']}"
            )
        from .wrappers import LaunchAttestation

        try:
            launch_attestation = LaunchAttestation.validate_for_dispatch(
                response["launch_attestation"],
                role_treatment=role_treatment,
                invocation_id=invocation.invocation_id,
            )
        except HarnessProtocolError as exc:
            raise protocol_error(str(exc)) from exc
        if response["cache_lineage"] != invocation.cache_lineage:
            raise protocol_error("cache lineage differs from request")
        if (
            not isinstance(response["artifacts"], list)
            or any(not isinstance(item, dict) for item in response["artifacts"])
            or not isinstance(response["claims"], list)
            or any(not isinstance(item, dict) for item in response["claims"])
        ):
            raise protocol_error("harness artifacts and claims must be lists")
        if not isinstance(response["usage"], dict):
            raise protocol_error("harness usage must be an object")
        return InvocationResult(
            invocation_id=invocation.invocation_id,
            cell_revision=invocation.cell_revision,
            status=response["status"],
            requested_role_treatment=requested_role_treatment,
            launch_attestation=launch_attestation.to_dict(),
            artifacts=tuple(response["artifacts"]),
            claims=tuple(response["claims"]),
            usage=response["usage"],
            cache_lineage=response["cache_lineage"],
            prompt_ref=invocation.prompt_ref,
            context_manifest_ref=invocation.context_manifest_ref,
            context_lineage=invocation.context_lineage,
            latency_ms=latency_ms,
            execution_ref=(
                str(raw_record.artifact_ref) if raw_record is not None else None
            ),
            raw_redaction_count=(
                int(raw_record.redaction_count) if raw_record is not None else 0
            ),
            process_trace=process_trace.to_dict(),
        )
