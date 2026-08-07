from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from .atomic import canonical_json
from .errors import IdempotencyError, IntegrityError, SensitiveDataError


ZERO_HASH = "0" * 64
SENSITIVE_KEYS = {
    "token",
    "password",
    "secret",
    "credential",
    "authorization",
    "api_key",
    "apikey",
    "private_key",
}
SENSITIVE_VALUES = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
)


def _reject_sensitive(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in SENSITIVE_KEYS:
                raise SensitiveDataError(f"sensitive evidence field rejected: {'.'.join((*path, str(key)))}")
            _reject_sensitive(item, (*path, str(key)))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_sensitive(item, (*path, str(index)))
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SENSITIVE_VALUES):
        raise SensitiveDataError(f"credential-shaped evidence value rejected at {'.'.join(path)}")


def _event_hash(event_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(event_without_hash)).hexdigest()


class EventLedger:
    def __init__(self, path: Path, *, run_id: str) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.lock_path = self.path.with_name(f".{self.path.name}.lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self.lock_path.touch(exist_ok=True)

    def _read_unlocked(self) -> list[dict[str, Any]]:
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise IntegrityError("ledger has a partial final record")
        events: list[dict[str, Any]] = []
        previous = ZERO_HASH
        for line_number, raw_line in enumerate(raw.splitlines(), 1):
            try:
                event = json.loads(raw_line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntegrityError(f"ledger record {line_number} is malformed") from exc
            required = {
                "seq",
                "event_id",
                "run_id",
                "type",
                "actor",
                "timestamp",
                "payload",
                "prev_hash",
                "hash",
            }
            if set(event) != required:
                raise IntegrityError(f"ledger record {line_number} fields are invalid")
            if event["seq"] != line_number:
                raise IntegrityError(f"ledger sequence mismatch at record {line_number}")
            if event["run_id"] != self.run_id:
                raise IntegrityError(f"ledger run mismatch at record {line_number}")
            if event["prev_hash"] != previous:
                raise IntegrityError(f"ledger chain mismatch at record {line_number}")
            claimed = event["hash"]
            basis = dict(event)
            del basis["hash"]
            actual = _event_hash(basis)
            if claimed != actual:
                raise IntegrityError(f"ledger hash mismatch at record {line_number}")
            _reject_sensitive(event["payload"])
            previous = claimed
            events.append(event)
        ids = [event["event_id"] for event in events]
        if len(set(ids)) != len(ids):
            raise IntegrityError("ledger contains duplicate event ids")
        return events

    def verify(self) -> list[dict[str, Any]]:
        with self.lock_path.open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            try:
                return self._read_unlocked()
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def append(
        self,
        event_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        _reject_sensitive(payload)
        with self.lock_path.open("r+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                events = self._read_unlocked()
                matching = [event for event in events if event["event_id"] == event_id]
                if matching:
                    existing = matching[0]
                    if (
                        existing["type"] == event_type
                        and existing["actor"] == actor
                        and existing["payload"] == payload
                    ):
                        return existing
                    raise IdempotencyError(f"event id reused with different content: {event_id}")
                basis = {
                    "seq": len(events) + 1,
                    "event_id": event_id,
                    "run_id": self.run_id,
                    "type": event_type,
                    "actor": actor,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": payload,
                    "prev_hash": events[-1]["hash"] if events else ZERO_HASH,
                }
                event = {**basis, "hash": _event_hash(basis)}
                encoded = canonical_json(event) + b"\n"
                descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND)
                try:
                    os.write(descriptor, encoded)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                return event
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def quarantine_partial_tail(self) -> Path:
        with self.lock_path.open("r+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                raw = self.path.read_bytes()
                if not raw or raw.endswith(b"\n"):
                    raise IntegrityError("ledger has no partial tail to quarantine")
                boundary = raw.rfind(b"\n") + 1
                prefix, tail = raw[:boundary], raw[boundary:]
                quarantine = self.path.with_name(
                    f"{self.path.name}.partial.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"
                )
                descriptor = os.open(quarantine, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    os.write(descriptor, tail)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                with self.path.open("r+b") as stream:
                    stream.truncate(len(prefix))
                    stream.flush()
                    os.fsync(stream.fileno())
                self._read_unlocked()
                return quarantine
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

