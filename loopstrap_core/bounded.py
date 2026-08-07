"""Bounded subprocess execution.

Extracted from HarnessDispatcher so that modules which merely need to run a
command under a wall clock and an output ceiling do not have to import the
dispatcher. verification.py and certification.py were reaching into
HarnessDispatcher._run_bounded and ._environment for exactly that; those were
the only runtime edges from the authority core into the control plane.

This module depends on errors only. Nothing here decides anything: it starts a
process, bounds it, records what happened, and returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time
from typing import Any

from .errors import (
    HarnessExecutionError,
    HarnessInterruptedError,
    HarnessOutputLimitError,
    HarnessProtocolError,
    HarnessTimeoutError,
    SensitiveDataError,
)


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


def sanitized_environment(requested: dict[str, str]) -> dict[str, str]:
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


def terminate(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def process_trace(
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


def run_bounded(
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
        error.process_trace = process_trace(
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
        terminate(process)
        process.stdout.close()
        process.stderr.close()
        error = HarnessInterruptedError(
            "harness input stream was interrupted",
            stdout=bytes(output),
            stderr=bytes(errors),
        )
        error.process_trace = process_trace(
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
                terminate(process)
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
                    terminate(process)
                    raise HarnessOutputLimitError(
                        f"harness output exceeded {max_output_bytes} bytes",
                        stdout=bytes(output),
                        stderr=bytes(errors),
                    )
        remaining = deadline - time.monotonic()
        try:
            return_code = process.wait(timeout=max(remaining, 0.001))
        except subprocess.TimeoutExpired as exc:
            terminate(process)
            raise HarnessTimeoutError(
                f"harness exceeded {timeout_seconds} seconds",
                stdout=bytes(output),
                stderr=bytes(errors),
            ) from exc
    except HarnessExecutionError as exc:
        exc.process_trace = process_trace(
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
        terminate(process)
        error = HarnessInterruptedError(
            "harness execution was interrupted",
            stdout=bytes(output),
            stderr=bytes(errors),
        )
        error.process_trace = process_trace(
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
    trace = process_trace(
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
