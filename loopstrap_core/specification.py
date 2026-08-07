from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

from .atomic import canonical_json
from .errors import IntegrityError, SchemaError, SpecificationError


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
REQUIRED_PROJECT_FILES = {
    "package.cue",
    "lexicon.cue",
    "contracts.cue",
    "realization.cue",
}


@dataclass(frozen=True)
class ToolPin:
    version: str
    sha256: str

    def validate(self) -> None:
        if not VERSION_RE.fullmatch(self.version):
            raise SchemaError("CUE pin version must be an exact stable version")
        if not SHA256_RE.fullmatch(self.sha256):
            raise SchemaError("CUE pin SHA-256 is malformed")


@dataclass(frozen=True)
class SpecificationSnapshot:
    _canonical: bytes
    digest: str
    cue_version: str
    schema_version: str

    @classmethod
    def create(
        cls,
        document: dict[str, Any],
        *,
        cue_version: str,
        schema_version: str,
        input_manifest: dict[str, str],
    ) -> "SpecificationSnapshot":
        if not isinstance(document, dict):
            raise SchemaError("compiled specification must be an object")
        envelope = dict(document)
        envelope["compiler"] = {
            "tool": "cue",
            "version": cue_version,
            "schema_version": schema_version,
        }
        envelope["inputs"] = {
            key: input_manifest[key] for key in sorted(input_manifest)
        }
        encoded = canonical_json(envelope)
        return cls(
            _canonical=encoded,
            digest="sha256:" + hashlib.sha256(encoded).hexdigest(),
            cue_version=cue_version,
            schema_version=schema_version,
        )

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        *,
        expected_digest: str | None = None,
    ) -> "SpecificationSnapshot":
        try:
            document = json.loads(data)
            compiler = document["compiler"]
            cue_version = compiler["version"]
            schema_version = compiler["schema_version"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("specification snapshot bytes are invalid") from exc
        if not isinstance(document, dict):
            raise ValueError("specification snapshot must be an object")
        canonical = canonical_json(document)
        digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
        if expected_digest is not None and digest != expected_digest:
            raise ValueError("specification snapshot digest does not match")
        return cls(
            _canonical=canonical,
            digest=digest,
            cue_version=str(cue_version),
            schema_version=str(schema_version),
        )

    @property
    def document(self) -> dict[str, Any]:
        return json.loads(self._canonical)

    def to_bytes(self) -> bytes:
        return bytes(self._canonical)


class CUECompiler:
    def __init__(
        self,
        *,
        binary: Path,
        pin: ToolPin,
        schema_root: Path,
        timeout_seconds: float = 20.0,
        max_output_bytes: int = 8_000_000,
    ) -> None:
        self.binary = Path(os.path.abspath(binary))
        self.pin = pin
        self.schema_root = Path(os.path.abspath(schema_root))
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.pin.validate()
        if timeout_seconds <= 0 or max_output_bytes <= 0:
            raise SchemaError("CUE process bounds must be positive")

    def verify_tool(self) -> None:
        if (
            not self.binary.is_file()
            or self.binary.is_symlink()
            or not os.access(self.binary, os.X_OK)
        ):
            raise IntegrityError("pinned CUE executable is absent or unsafe")
        digest = hashlib.sha256(self.binary.read_bytes()).hexdigest()
        if digest != self.pin.sha256:
            raise IntegrityError("pinned CUE executable digest differs")
        try:
            result = subprocess.run(
                [str(self.binary), "version"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IntegrityError("pinned CUE executable could not report its version") from exc
        output = result.stdout + result.stderr
        if (
            result.returncode != 0
            or len(output) > self.max_output_bytes
            or f"cue version {self.pin.version}\n".encode("utf-8") not in output
        ):
            raise IntegrityError("pinned CUE executable version differs")

    def export(self, project_root: Path, *, expression: str) -> dict[str, Any]:
        self.verify_tool()
        project_root = Path(project_root)
        if not project_root.is_dir() or project_root.is_symlink():
            raise SpecificationError("project package must be a real directory")
        project_root = Path(os.path.abspath(project_root))
        schema = self.schema_root / "project.cue"
        if not schema.is_file() or schema.is_symlink():
            raise SpecificationError("Loopstrap CUE project schema is absent")
        found = {
            path.name
            for path in project_root.glob("*.cue")
            if path.is_file() and not path.is_symlink()
        }
        missing = REQUIRED_PROJECT_FILES - found
        if missing:
            raise SpecificationError(
                f"project package lacks required CUE files: {sorted(missing)}"
            )
        project_files = sorted(REQUIRED_PROJECT_FILES)
        with tempfile.TemporaryDirectory(prefix="loopstrap-cue-") as raw_home:
            command = [
                str(self.binary),
                "-C",
                str(project_root),
                "export",
                str(schema),
                *project_files,
                "-e",
                expression,
                "--out",
                "json",
            ]
            try:
                result = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout_seconds,
                    check=False,
                    env={
                        "PATH": "/usr/bin:/bin",
                        "LANG": "C.UTF-8",
                        "HOME": raw_home,
                        "CUE_CACHE_DIR": str(Path(raw_home) / "cache"),
                    },
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise SpecificationError("CUE compilation failed to execute") from exc
        if (
            len(result.stdout) > self.max_output_bytes
            or len(result.stderr) > self.max_output_bytes
        ):
            raise SpecificationError("CUE compilation exceeded output bounds")
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise SpecificationError(f"CUE rejected project package: {detail}")
        try:
            value = json.loads(result.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SpecificationError("CUE export did not return JSON") from exc
        if not isinstance(value, dict):
            raise SpecificationError("CUE project export must be an object")
        return value

    def validate_data(
        self,
        value: dict[str, Any],
        *,
        schema_file: str,
        definition: str,
    ) -> None:
        self.verify_tool()
        relative = Path(schema_file)
        if relative.is_absolute() or ".." in relative.parts:
            raise SpecificationError("CUE schema filename escapes schema root")
        schema = self.schema_root / relative
        if not schema.is_file() or schema.is_symlink():
            raise SpecificationError(f"Loopstrap CUE schema is absent: {schema_file}")
        with tempfile.TemporaryDirectory(prefix="loopstrap-cue-data-") as raw:
            root = Path(raw)
            data_path = root / "input.json"
            data_path.write_bytes(canonical_json(value))
            try:
                result = subprocess.run(
                    [
                        str(self.binary),
                        "vet",
                        str(schema),
                        str(data_path),
                        "-d",
                        definition,
                        "-c",
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout_seconds,
                    check=False,
                    env={
                        "PATH": "/usr/bin:/bin",
                        "LANG": "C.UTF-8",
                        "HOME": raw,
                        "CUE_CACHE_DIR": str(root / "cache"),
                    },
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise SpecificationError("CUE data validation failed to execute") from exc
        if (
            len(result.stdout) > self.max_output_bytes
            or len(result.stderr) > self.max_output_bytes
        ):
            raise SpecificationError("CUE data validation exceeded output bounds")
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise SpecificationError(f"CUE rejected structured data: {detail}")


class SpecificationCompiler:
    SCHEMA_VERSION = "loopstrap.project/v1"

    def __init__(self, cue: CUECompiler) -> None:
        self.cue = cue

    def compile(self, project_root: Path) -> SpecificationSnapshot:
        project_root = Path(project_root)
        document = self.cue.export(project_root, expression="project")
        manifest: dict[str, str] = {}
        for name in sorted(REQUIRED_PROJECT_FILES):
            path = project_root / name
            manifest[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return SpecificationSnapshot.create(
            document,
            cue_version=self.cue.pin.version,
            schema_version=self.SCHEMA_VERSION,
            input_manifest=manifest,
        )
