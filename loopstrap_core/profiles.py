from __future__ import annotations

"""Harness invocation profiles — the ruled tweak seam (assumed-basic basis).

The flag skeleton each vendor wrapper emits lives in
``config/harness-profiles.v1.json`` as data. Editing that file — never this
module — is how the invocation surface is corrected when a vendor CLI drifts
(machines.md D38). When the file is absent the built-in defaults below apply;
they are byte-identical to the historically certified argv, so the frozen
certification suite proves both paths. A present-but-invalid file fails loudly.

Template tokens, expanded per invocation:
  {vendor_executable} {model_selector} {reasoning_control}
  {reasoning_requested} {schema_file} {workspace_dir} {prompt_file}
Expansion markers (must appear as whole tokens):
  @native@   -> the Role-Treatment's certified native arguments, in order
"""

import json
from pathlib import Path
from typing import Any, Mapping

from .errors import SchemaError

PROFILE_SCHEMA_VERSION = 1
PROFILE_RELATIVE_PATH = Path("config") / "harness-profiles.v1.json"
_NATIVE_MARKER = "@native@"

DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "codex": {
        "version_pin": "0.144.6",
        "basis": "assumed-basic 2026-07-30; certified argv 0.144.1; D38 re-verify pending",
        "smoke_argv": ["{vendor_executable}", "exec", "--json", "-"],
        "argv": [
            "{vendor_executable}",
            "exec",
            "--model",
            "{model_selector}",
            "-c",
            '{reasoning_control}="{reasoning_requested}"',
            "--json",
            "--output-schema",
            "{schema_file}",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
            "--cd",
            "{workspace_dir}",
            _NATIVE_MARKER,
            "-",
        ],
        "stdin": "prompt",
        "environment": {},
    },
    "claude-code": {
        "version_pin": "2.1.216",
        "basis": "assumed-basic 2026-07-30; certified argv 2.1.215; D38 re-verify pending",
        "smoke_argv": [
            "{vendor_executable}",
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
        ],
        "argv": [
            "{vendor_executable}",
            "-p",
            "--model",
            "{model_selector}",
            "--effort",
            "{reasoning_requested}",
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--forward-subagent-text",
            "--json-schema",
            "{schema_file}",
            "--strict-mcp-config",
            _NATIVE_MARKER,
        ],
        "stdin": "prompt",
        "environment": {"CLAUDE_CONFIG_DIR": "{state_dir}"},
        "state_subdir": "claude-state",
    },
    "grok-build": {
        "version_pin": "ruled-out",
        "basis": "L4 ruling 2026-07-21; wrapper retained for registry completeness",
        "argv": [
            "{vendor_executable}",
            "--prompt-file",
            "{prompt_file}",
            "--verbatim",
            "--model",
            "{model_selector}",
            "--effort",
            "{reasoning_requested}",
            "--output-format",
            "streaming-json",
            "--cwd",
            "{workspace_dir}",
            "--no-auto-update",
            "--no-memory",
            _NATIVE_MARKER,
        ],
        "stdin": "none",
        "environment": {"GROK_CONFIG_DIR": "{state_dir}"},
        "state_subdir": "grok-state",
    },
}

_STDIN_MODES = {"prompt", "none"}
_cache: dict[Path, dict[str, dict[str, Any]]] = {}


def _validate(data: Any, source: str) -> dict[str, dict[str, Any]]:
    if not isinstance(data, dict) or data.get("version") != PROFILE_SCHEMA_VERSION:
        raise SchemaError(f"{source}: harness profile version must be {PROFILE_SCHEMA_VERSION}")
    harnesses = data.get("harnesses")
    if not isinstance(harnesses, dict) or not harnesses:
        raise SchemaError(f"{source}: harness profile requires a nonempty harnesses table")
    result: dict[str, dict[str, Any]] = {}
    for name, row in harnesses.items():
        if not isinstance(name, str) or not name or not isinstance(row, dict):
            raise SchemaError(f"{source}: harness profile rows must be named objects")
        argv = row.get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(token, str) or not token for token in argv)
        ):
            raise SchemaError(f"{source}: {name} argv must be a nonempty string list")
        stdin = row.get("stdin", "none")
        if stdin not in _STDIN_MODES:
            raise SchemaError(f"{source}: {name} stdin mode must be one of {sorted(_STDIN_MODES)}")
        environment = row.get("environment", {})
        if not isinstance(environment, dict) or any(
            not isinstance(key, str) or not key or not isinstance(value, str)
            for key, value in environment.items()
        ):
            raise SchemaError(f"{source}: {name} environment must map names to string templates")
        for field in ("version_pin", "basis"):
            if not isinstance(row.get(field, ""), str):
                raise SchemaError(f"{source}: {name} {field} must be a string")
        state_subdir = row.get("state_subdir", "")
        if not isinstance(state_subdir, str):
            raise SchemaError(f"{source}: {name} state_subdir must be a string")
        smoke_argv = row.get("smoke_argv", [])
        if not isinstance(smoke_argv, list) or any(
            not isinstance(token, str) or not token for token in smoke_argv
        ):
            raise SchemaError(f"{source}: {name} smoke_argv must be a string list")
        result[name] = {
            "version_pin": row.get("version_pin", ""),
            "basis": row.get("basis", ""),
            "argv": list(argv),
            "stdin": stdin,
            "environment": dict(environment),
            "state_subdir": state_subdir,
            "smoke_argv": list(smoke_argv),
        }
    return result


def load_profiles(root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Profiles from the kernel root's config file; built-in defaults when absent."""
    if root is None:
        root = Path(__file__).resolve().parents[1]
    root = Path(root).resolve()
    if root in _cache:
        return _cache[root]
    path = root / PROFILE_RELATIVE_PATH
    if not path.is_file():
        profiles = _validate(
            {"version": PROFILE_SCHEMA_VERSION, "harnesses": DEFAULT_PROFILES},
            "built-in defaults",
        )
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SchemaError(f"harness profile file unreadable: {exc}") from exc
        profiles = _validate(data, str(path))
    _cache[root] = profiles
    return profiles


def profile_for(harness: str, root: Path | None = None) -> dict[str, Any]:
    profiles = load_profiles(root)
    try:
        return profiles[harness]
    except KeyError as exc:
        raise SchemaError(f"no harness profile for: {harness}") from exc


def render(
    profile: Mapping[str, Any],
    substitutions: Mapping[str, str],
    native_arguments: tuple[str, ...],
) -> tuple[tuple[str, ...], dict[str, str]]:
    """Expand a profile's argv and environment templates. Unknown fields fail loudly."""
    argv: list[str] = []
    for token in profile["argv"]:
        if token == _NATIVE_MARKER:
            argv.extend(native_arguments)
            continue
        try:
            argv.append(token.format(**substitutions))
        except (KeyError, IndexError) as exc:
            raise SchemaError(f"harness profile token references unknown field: {token}") from exc
    environment: dict[str, str] = {}
    for name, template in profile["environment"].items():
        try:
            environment[name] = template.format(**substitutions)
        except (KeyError, IndexError) as exc:
            raise SchemaError(
                f"harness profile environment references unknown field: {template}"
            ) from exc
    return tuple(argv), environment
