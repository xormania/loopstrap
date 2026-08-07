from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Iterable, Protocol

from .atomic import canonical_json
from .errors import HarnessProtocolError, SchemaError
from .harness import RoleTreatment
from .profiles import load_profiles, profile_for, render


WRAPPER_ISSUER = "loopstrap-harness-wrapper-v1"
CONFIGURATION_FIELDS = {
    "user_config_policy",
    "arguments",
    "settings",
    "tools",
    "permissions",
    "doctrine",
    "session",
    "subagents",
    "invocation_overrides",
}


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _inside(path: Path, root: Path, label: str) -> Path:
    try:
        resolved = Path(path).resolve(strict=True)
        resolved.relative_to(Path(root).resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise HarnessProtocolError(f"{label} must be inside the invocation workspace") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise HarnessProtocolError(f"{label} must be a real regular file")
    return resolved


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise HarnessProtocolError(f"{label} must be a string list")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise HarnessProtocolError(f"{label} must contain unique values")
    return result


@dataclass(frozen=True)
class WrapperRequest:
    invocation_id: str
    workspace: Path
    prompt_file: Path
    output_schema_file: Path
    invocation_overrides: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.invocation_id, str) or not self.invocation_id:
            raise HarnessProtocolError("wrapper invocation id must be nonempty")
        workspace = Path(self.workspace)
        if not workspace.is_dir() or workspace.is_symlink():
            raise HarnessProtocolError("wrapper workspace must be a real directory")
        _inside(self.prompt_file, workspace, "prompt file")
        _inside(self.output_schema_file, workspace, "output schema file")
        if not isinstance(self.invocation_overrides, dict):
            raise HarnessProtocolError("invocation overrides must be an object")


@dataclass(frozen=True)
class LaunchPlan:
    invocation_id: str
    harness: str
    argv: tuple[str, ...]
    stdin_file: Path | None
    environment: dict[str, str]
    configuration_digest: str
    sent: dict[str, Any]


class HarnessWrapper(Protocol):
    harness: str

    def compile(
        self, role_treatment: RoleTreatment, request: WrapperRequest
    ) -> LaunchPlan:
        ...


def _flatten(value: Any, prefix: str = "") -> dict[str, str]:
    """Scalar leaves of a Role-Treatment, as underscore-joined placeholder names.

    The substitution vocabulary used to be eight names hardcoded here, so any new
    command-line knob meant editing Python. Every scalar a Role-Treatment
    declares is now addressable from a harness profile's argv template, which
    makes adding a flag a config change.

    Lists and nested containers are skipped deliberately: a placeholder expands
    to one argv token, and per-role argument lists already have their own seam at
    the native marker.
    """
    flat: dict[str, str] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            flat.update(_flatten(item, f"{prefix}{key}_"))
    elif isinstance(value, bool):
        flat[prefix.rstrip("_")] = "true" if value else "false"
    elif isinstance(value, (str, int, float)):
        flat[prefix.rstrip("_")] = str(value)
    return flat


class _BaseWrapper:
    harness = ""

    def _configuration(
        self, role_treatment: RoleTreatment, request: WrapperRequest
    ) -> tuple[dict[str, Any], tuple[str, ...]]:
        if role_treatment.harness != self.harness:
            raise HarnessProtocolError(
                f"{self.harness} wrapper cannot compile {role_treatment.harness}"
            )
        configuration = role_treatment.configuration
        if set(configuration) != CONFIGURATION_FIELDS:
            raise HarnessProtocolError(
                "Role-Treatment configuration fields are incomplete or unknown"
            )
        if configuration["user_config_policy"] != "exclude":
            raise HarnessProtocolError("hidden user configuration must be excluded")
        allowed_overrides = _string_list(
            configuration["invocation_overrides"],
            "permitted invocation overrides",
        )
        unknown = set(request.invocation_overrides) - set(allowed_overrides)
        if unknown:
            raise HarnessProtocolError(
                f"uncertified invocation overrides: {sorted(unknown)}"
            )
        resolved = {
            **configuration,
            "resolved_invocation_overrides": dict(request.invocation_overrides),
        }
        arguments = _string_list(configuration["arguments"], "native arguments")
        return resolved, arguments


    def _plan_from_profile(
        self, role_treatment: RoleTreatment, request: WrapperRequest
    ) -> LaunchPlan:
        configuration, native = self._configuration(role_treatment, request)
        prompt = _inside(request.prompt_file, request.workspace, "prompt file")
        schema = _inside(
            request.output_schema_file, request.workspace, "output schema file"
        )
        workspace = Path(request.workspace).resolve()
        profile = profile_for(self.harness)
        state_subdir = profile.get("state_subdir", "")
        # Every scalar the Role-Treatment declares, addressable from a profile.
        # The eight names below are kept verbatim and take precedence, so
        # rendered argv is unchanged and certification argv-exactness holds.
        substitutions = {
            **_flatten(role_treatment.to_dict()),
            "vendor_executable": role_treatment.wrapper.vendor_executable,
            "model_selector": role_treatment.model_route.selector,
            "reasoning_control": role_treatment.reasoning.control,
            "reasoning_requested": role_treatment.reasoning.requested,
            "schema_file": str(schema),
            "workspace_dir": str(workspace),
            "prompt_file": str(prompt),
            "state_dir": str(workspace / ".loopstrap" / state_subdir)
            if state_subdir
            else "",
        }
        argv, environment = render(profile, substitutions, native)
        config_digest = _digest(configuration)
        return LaunchPlan(
            invocation_id=request.invocation_id,
            harness=self.harness,
            argv=argv,
            stdin_file=prompt if profile["stdin"] == "prompt" else None,
            environment=environment,
            configuration_digest=config_digest,
            sent=self._sent(role_treatment, config_digest),
        )

    @staticmethod
    def _sent(
        role_treatment: RoleTreatment, configuration_digest: str
    ) -> dict[str, Any]:
        return {
            "model_selector": role_treatment.model_route.selector,
            "model_provider": role_treatment.model_route.provider,
            "reasoning_control": role_treatment.reasoning.control,
            "reasoning_value": role_treatment.reasoning.requested,
            "expected_wire_reasoning": role_treatment.reasoning.expected_wire,
            "orchestration": role_treatment.reasoning.orchestration,
            "configuration_digest": configuration_digest,
        }


class ProfileWrapper(_BaseWrapper):
    """The only wrapper. Which vendor a wrapper serves is data — a key in
    config/harness-profiles.v1.json — not a Python class.

    This replaces CodexWrapper, ClaudeCodeWrapper and GrokBuildWrapper, whose
    bodies were byte-identical once the profile seam landed on 2026-07-30: all
    three delegated to _plan_from_profile and differed only in a string. Keeping
    three classes meant adding a harness required editing Python, and it put
    vendor names in the kernel that the rest of the kernel is audited for not
    containing.
    """

    def __init__(self, harness: str) -> None:
        if not isinstance(harness, str) or not harness:
            raise SchemaError("wrapper harness must be a nonempty string")
        self.harness = harness

    def compile(
        self, role_treatment: RoleTreatment, request: WrapperRequest
    ) -> LaunchPlan:
        return self._plan_from_profile(role_treatment, request)


class HarnessWrapperRegistry:
    def __init__(self, wrappers: Iterable[HarnessWrapper]) -> None:
        rows = tuple(wrappers)
        if not rows or len({item.harness for item in rows}) != len(rows):
            raise SchemaError("wrapper harnesses must be nonempty and unique")
        self.wrappers = {item.harness: item for item in rows}

    @classmethod
    def default(cls, root: Path | None = None) -> "HarnessWrapperRegistry":
        """One wrapper per declared profile. Adding a harness is a config change."""
        return cls(ProfileWrapper(name) for name in sorted(load_profiles(root)))

    def get(self, harness: str) -> HarnessWrapper:
        try:
            return self.wrappers[harness]
        except KeyError as exc:
            raise HarnessProtocolError(
                f"no Loopstrap wrapper for harness: {harness}"
            ) from exc


@dataclass(frozen=True)
class LaunchAttestation:
    schema_version: int
    issuer: str
    invocation_id: str
    role_treatment_id: str
    role: str
    harness: str
    requested_identity_digest: str
    sent: dict[str, Any]
    observed: dict[str, Any]
    proof: dict[str, Any]
    sanitized_argv: tuple[str, ...]
    configuration_digest: str
    environment_names: tuple[str, ...]

    FIELDS = {
        "schema_version",
        "issuer",
        "invocation_id",
        "role_treatment_id",
        "role",
        "harness",
        "requested_identity_digest",
        "sent",
        "observed",
        "proof",
        "sanitized_argv",
        "configuration_digest",
        "environment_names",
    }

    @classmethod
    def validate_for_dispatch(
        cls,
        data: dict[str, Any],
        *,
        role_treatment: RoleTreatment,
        invocation_id: str,
    ) -> "LaunchAttestation":
        if not isinstance(data, dict):
            raise HarnessProtocolError("launch attestation must be an object")
        argv = data.get("sanitized_argv")
        environment_names = data.get("environment_names")
        configuration_digest = data.get("configuration_digest")
        sent = data.get("sent")
        if (
            not isinstance(argv, list)
            or not argv
            or not isinstance(environment_names, list)
            or not isinstance(configuration_digest, str)
            or not isinstance(sent, dict)
        ):
            raise HarnessProtocolError("launch attestation is incomplete")
        expected_sent = _BaseWrapper._sent(
            role_treatment, configuration_digest
        )
        plan = LaunchPlan(
            invocation_id=invocation_id,
            harness=role_treatment.harness,
            argv=tuple(argv),
            stdin_file=None,
            environment={name: "" for name in environment_names},
            configuration_digest=configuration_digest,
            sent=expected_sent,
        )
        return cls.validate(
            data, role_treatment=role_treatment, plan=plan
        )

    @classmethod
    def validate(
        cls,
        data: dict[str, Any],
        *,
        role_treatment: RoleTreatment,
        plan: LaunchPlan,
    ) -> "LaunchAttestation":
        if not isinstance(data, dict) or set(data) != cls.FIELDS:
            raise HarnessProtocolError("launch attestation fields are invalid")
        if data["schema_version"] != 1 or data["issuer"] != WRAPPER_ISSUER:
            raise HarnessProtocolError("launch attestation issuer or schema is invalid")
        exact = {
            "invocation_id": plan.invocation_id,
            "role_treatment_id": role_treatment.id,
            "role": role_treatment.role,
            "harness": role_treatment.harness,
            "requested_identity_digest": role_treatment.static_identity_digest(),
            "configuration_digest": plan.configuration_digest,
        }
        if any(data[key] != value for key, value in exact.items()):
            raise HarnessProtocolError("launch attestation binding differs")
        if data["sent"] != plan.sent:
            raise HarnessProtocolError("sent launch controls differ from compiled plan")
        argv = _string_list(data["sanitized_argv"], "sanitized launch argv")
        if argv != plan.argv:
            raise HarnessProtocolError("attested argv differs from compiled plan")
        environment_names = _string_list(
            data["environment_names"], "launch environment names"
        )
        if environment_names != tuple(sorted(plan.environment)):
            raise HarnessProtocolError("attested environment names differ")
        observed = data["observed"]
        if not isinstance(observed, dict) or set(observed) != {
            "models",
            "reasoning",
            "orchestration",
            "fallback_detected",
            "hidden_config_detected",
        }:
            raise HarnessProtocolError("observed launch fields are invalid")
        models = _string_list(observed["models"], "observed models")
        if not models or not set(models).issubset(
            set(role_treatment.model_route.allowed_resolved_models)
        ):
            raise HarnessProtocolError("an unapproved model was observed")
        if observed["fallback_detected"] is not False:
            raise HarnessProtocolError("model fallback was observed")
        if observed["hidden_config_detected"] is not False:
            raise HarnessProtocolError("hidden configuration was observed")
        if observed["orchestration"] != role_treatment.reasoning.orchestration:
            raise HarnessProtocolError("observed orchestration differs")
        proof = data["proof"]
        if not isinstance(proof, dict) or set(proof) != {
            "model",
            "reasoning",
            "configuration",
            "mapping_evidence_ref",
        }:
            raise HarnessProtocolError("launch proof fields are invalid")
        if proof["model"] != "runtime_event":
            raise HarnessProtocolError("model identity lacks direct runtime evidence")
        reasoning_proof = proof["reasoning"]
        if reasoning_proof not in role_treatment.reasoning.proof_sources:
            raise HarnessProtocolError("reasoning proof source was not certified")
        if reasoning_proof == "runtime_event":
            if observed["reasoning"] != role_treatment.reasoning.expected_wire:
                raise HarnessProtocolError("observed reasoning differs")
            if proof["mapping_evidence_ref"] is not None:
                raise HarnessProtocolError(
                    "direct reasoning evidence cannot cite a binary mapping"
                )
        else:
            reference = proof["mapping_evidence_ref"]
            if (
                observed["reasoning"] is not None
                or not isinstance(reference, str)
                or len(reference) != 71
                or not reference.startswith("sha256:")
                or any(character not in "0123456789abcdef" for character in reference[7:])
            ):
                raise HarnessProtocolError(
                    "unobserved reasoning requires a SHA-256 mapping evidence reference"
                )
        if proof["configuration"] != "sanitized_argv_and_digests":
            raise HarnessProtocolError("configuration proof is incomplete")
        return cls(
            schema_version=1,
            issuer=WRAPPER_ISSUER,
            invocation_id=data["invocation_id"],
            role_treatment_id=data["role_treatment_id"],
            role=data["role"],
            harness=data["harness"],
            requested_identity_digest=data["requested_identity_digest"],
            sent=dict(data["sent"]),
            observed={**observed, "models": list(models)},
            proof=dict(proof),
            sanitized_argv=argv,
            configuration_digest=data["configuration_digest"],
            environment_names=environment_names,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "issuer": self.issuer,
            "invocation_id": self.invocation_id,
            "role_treatment_id": self.role_treatment_id,
            "role": self.role,
            "harness": self.harness,
            "requested_identity_digest": self.requested_identity_digest,
            "sent": self.sent,
            "observed": self.observed,
            "proof": self.proof,
            "sanitized_argv": list(self.sanitized_argv),
            "configuration_digest": self.configuration_digest,
            "environment_names": list(self.environment_names),
        }
