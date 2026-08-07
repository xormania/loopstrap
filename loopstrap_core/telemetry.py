from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import time
from typing import Any, Iterable

from .atomic import canonical_json
from .errors import IdempotencyError, IntegrityError, SchemaError
from .ledger import _reject_sensitive


SCHEMA_VERSION = 1
DIGEST_PREFIX = "sha256:"
KNOWN_USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cost",
    "compute",
    "retries",
    "risk",
    "human_attention",
)
MEASUREMENT_UNITS = {
    "input_tokens": "tokens",
    "output_tokens": "tokens",
    "cost": "currency",
    "compute": "provider_units",
    "retries": "count",
    "risk": "risk_units",
    "human_attention": "attention_units",
    "latency_ms": "milliseconds",
    "duration_ns": "nanoseconds",
    "total_duration_ns": "nanoseconds",
    "raw_redaction_count": "count",
}
APPEND_TABLES = (
    "telemetry_meta",
    "telemetry_events",
    "telemetry_relationships",
    "telemetry_measurements",
    "telemetry_role_treatments",
    "telemetry_event_treatments",
    "telemetry_references",
    "telemetry_reference_observations",
    "telemetry_paths",
    "telemetry_blobs",
    "telemetry_blob_sources",
    "telemetry_snapshots",
    "telemetry_snapshot_entries",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaError(f"{label} must be a nonempty string")
    return value


def _canonical_text(value: Any) -> str:
    return canonical_json(value).decode("utf-8")


def _sha256(data: bytes) -> str:
    return DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def _is_reference(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith(DIGEST_PREFIX):
        return False
    digest = value[len(DIGEST_PREFIX) :]
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def _path_snapshot(path: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "unavailable",
        "path_type": None,
        "mode": None,
        "size_bytes": None,
        "mtime_ns": None,
    }
    try:
        metadata = os.lstat(path)
    except OSError:
        return result
    if stat.S_ISREG(metadata.st_mode):
        path_type = "file"
    elif stat.S_ISDIR(metadata.st_mode):
        path_type = "directory"
    elif stat.S_ISLNK(metadata.st_mode):
        path_type = "symlink"
    else:
        path_type = "other"
    return {
        "status": "observed",
        "path_type": path_type,
        "mode": stat.S_IMODE(metadata.st_mode),
        "size_bytes": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
    }


def _walk(
    value: Any,
    *,
    path: str = "$",
    under_paths: bool = False,
) -> Iterable[tuple[str, str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            child = f"{path}.{key_text}"
            normalized = key_text.lower()
            child_under_paths = under_paths or normalized == "paths"
            if isinstance(item, str):
                if _is_reference(item):
                    yield ("reference", child, item)
                if (
                    child_under_paths
                    or normalized in {"cwd", "workspace", "run_root"}
                    or normalized.endswith("_path")
                    or normalized.endswith("_dir")
                    or normalized.endswith("_root")
                ):
                    yield ("path", child, item)
            yield from _walk(
                item,
                path=child,
                under_paths=child_under_paths,
            )
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            child = f"{path}[{index}]"
            if isinstance(item, str) and _is_reference(item):
                yield ("reference", child, item)
            yield from _walk(item, path=child, under_paths=under_paths)


class TelemetryStore:
    """Append-only, non-authoritative observation mirror."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=30.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS telemetry_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS telemetry_events (
                    event_id TEXT PRIMARY KEY,
                    event_digest TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    collection_sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    monotonic_ns INTEGER,
                    captured_at TEXT NOT NULL,
                    captured_monotonic_ns INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    source_sequence INTEGER,
                    source_hash TEXT,
                    schema_version INTEGER NOT NULL,
                    cell_id TEXT,
                    cell_revision INTEGER,
                    work_unit_id TEXT,
                    attempt_id TEXT,
                    role TEXT,
                    role_treatment_id TEXT,
                    parent_event_id TEXT,
                    cause_event_id TEXT,
                    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
                    context_json TEXT NOT NULL CHECK(json_valid(context_json)),
                    UNIQUE(run_id, collection_sequence),
                    UNIQUE(source, run_id, source_sequence)
                );

                CREATE TABLE IF NOT EXISTS telemetry_relationships (
                    event_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    related_event_id TEXT NOT NULL,
                    PRIMARY KEY(event_id, relation, related_event_id),
                    FOREIGN KEY(event_id) REFERENCES telemetry_events(event_id)
                );

                CREATE TABLE IF NOT EXISTS telemetry_measurements (
                    event_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('observed','unavailable')),
                    unit TEXT,
                    value_json TEXT NOT NULL CHECK(json_valid(value_json)),
                    PRIMARY KEY(event_id, name),
                    FOREIGN KEY(event_id) REFERENCES telemetry_events(event_id)
                );

                CREATE TABLE IF NOT EXISTS telemetry_role_treatments (
                    treatment_digest TEXT PRIMARY KEY,
                    role_treatment_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    harness TEXT NOT NULL,
                    provider TEXT,
                    model_selector TEXT,
                    reasoning_requested TEXT,
                    orchestration TEXT,
                    wrapper_id TEXT,
                    configuration_json TEXT NOT NULL CHECK(json_valid(configuration_json)),
                    identity_json TEXT NOT NULL CHECK(json_valid(identity_json)),
                    static_identity_json TEXT NOT NULL CHECK(json_valid(static_identity_json))
                );

                CREATE TABLE IF NOT EXISTS telemetry_event_treatments (
                    event_id TEXT NOT NULL,
                    treatment_digest TEXT NOT NULL,
                    relationship TEXT NOT NULL,
                    PRIMARY KEY(event_id, treatment_digest, relationship),
                    FOREIGN KEY(event_id) REFERENCES telemetry_events(event_id),
                    FOREIGN KEY(treatment_digest)
                        REFERENCES telemetry_role_treatments(treatment_digest)
                );

                CREATE TABLE IF NOT EXISTS telemetry_references (
                    event_id TEXT NOT NULL,
                    json_path TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    PRIMARY KEY(event_id, json_path, reference),
                    FOREIGN KEY(event_id) REFERENCES telemetry_events(event_id)
                );

                CREATE TABLE IF NOT EXISTS telemetry_reference_observations (
                    reference TEXT NOT NULL,
                    event_id TEXT,
                    status TEXT NOT NULL CHECK(status IN ('captured','unavailable')),
                    source_kind TEXT NOT NULL,
                    source_path TEXT,
                    observed_at TEXT NOT NULL,
                    PRIMARY KEY(reference, event_id, status, source_kind, source_path)
                );

                CREATE TABLE IF NOT EXISTS telemetry_paths (
                    observation_digest TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    path TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('observed','unavailable')),
                    path_type TEXT,
                    mode INTEGER,
                    size_bytes INTEGER,
                    mtime_ns INTEGER,
                    observed_at TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES telemetry_events(event_id)
                );

                CREATE TABLE IF NOT EXISTS telemetry_blobs (
                    reference TEXT PRIMARY KEY,
                    bytes BLOB NOT NULL,
                    byte_count INTEGER NOT NULL,
                    first_captured_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS telemetry_blob_sources (
                    reference TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    event_id TEXT NOT NULL DEFAULT '',
                    captured_at TEXT NOT NULL,
                    PRIMARY KEY(reference, source_kind, source_path, event_id),
                    FOREIGN KEY(reference) REFERENCES telemetry_blobs(reference)
                );

                CREATE TABLE IF NOT EXISTS telemetry_snapshots (
                    snapshot_ref TEXT PRIMARY KEY,
                    manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json)),
                    manifest_blob_ref TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    first_event_id TEXT NOT NULL DEFAULT '',
                    captured_at TEXT NOT NULL,
                    FOREIGN KEY(manifest_blob_ref) REFERENCES telemetry_blobs(reference)
                );

                CREATE TABLE IF NOT EXISTS telemetry_snapshot_entries (
                    snapshot_ref TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    mode INTEGER NOT NULL,
                    target TEXT,
                    content_sha256 TEXT,
                    size_bytes INTEGER,
                    blob_ref TEXT,
                    PRIMARY KEY(snapshot_ref, relative_path),
                    FOREIGN KEY(snapshot_ref) REFERENCES telemetry_snapshots(snapshot_ref),
                    FOREIGN KEY(blob_ref) REFERENCES telemetry_blobs(reference)
                );

                CREATE INDEX IF NOT EXISTS telemetry_events_run_type
                    ON telemetry_events(run_id, event_type, collection_sequence);
                CREATE INDEX IF NOT EXISTS telemetry_events_attempt
                    ON telemetry_events(run_id, attempt_id, collection_sequence);
                CREATE INDEX IF NOT EXISTS telemetry_measurements_name
                    ON telemetry_measurements(name, status);
                CREATE INDEX IF NOT EXISTS telemetry_references_reference
                    ON telemetry_references(reference);
                CREATE INDEX IF NOT EXISTS telemetry_paths_path
                    ON telemetry_paths(path);
                """
            )
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.execute(
                "INSERT OR IGNORE INTO telemetry_meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
            for table in APPEND_TABLES:
                connection.executescript(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {table}_no_update
                    BEFORE UPDATE ON {table}
                    BEGIN
                        SELECT RAISE(ABORT, 'telemetry is append-only');
                    END;
                    CREATE TRIGGER IF NOT EXISTS {table}_no_delete
                    BEFORE DELETE ON {table}
                    BEGIN
                        SELECT RAISE(ABORT, 'telemetry is append-only');
                    END;
                    """
                )

    @staticmethod
    def _dimensions(
        payload: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        treatment = payload.get("requested_role_treatment")
        if not isinstance(treatment, dict):
            treatment = context.get("requested_role_treatment")
        role_treatment_id = (
            context.get("role_treatment_id")
            or payload.get("role_treatment_id")
            or (treatment.get("id") if isinstance(treatment, dict) else None)
        )
        cell_id = context.get("cell_id") or payload.get("cell_id")
        cell_revision = (
            context.get("cell_revision")
            if context.get("cell_revision") is not None
            else payload.get("cell_revision", payload.get("revision"))
        )
        attempt_id = (
            context.get("attempt_id")
            or payload.get("attempt_id")
            or payload.get("job_id")
            or payload.get("invocation_id")
            or payload.get("dispatch_id")
        )
        return {
            "cell_id": cell_id,
            "cell_revision": cell_revision,
            "work_unit_id": context.get("work_unit_id") or payload.get("work_unit_id") or cell_id,
            "attempt_id": attempt_id,
            "role": context.get("role") or payload.get("role"),
            "role_treatment_id": role_treatment_id,
            "parent_event_id": context.get("parent_event_id") or payload.get("parent_event_id"),
            "cause_event_id": context.get("cause_event_id") or payload.get("cause_event_id"),
        }

    @staticmethod
    def _event_digest(row: dict[str, Any]) -> str:
        return _sha256(canonical_json(row))

    @staticmethod
    def _measurement_rows(
        event_type: str, payload: dict[str, Any]
    ) -> dict[str, tuple[str, str | None, Any]]:
        rows: dict[str, tuple[str, str | None, Any]] = {}
        usage = payload.get("usage")
        if event_type in {"harness.completed", "harness.failed"}:
            usage_object = usage if isinstance(usage, dict) else {}
            for name in KNOWN_USAGE_FIELDS:
                value = usage_object.get(name)
                rows[name] = (
                    "unavailable" if value is None else "observed",
                    MEASUREMENT_UNITS.get(name),
                    value,
                )
            for name, value in usage_object.items():
                if name not in rows:
                    rows[str(name)] = (
                        "unavailable" if value is None else "observed",
                        MEASUREMENT_UNITS.get(str(name)),
                        value,
                    )
        for name in (
            "latency_ms",
            "duration_ns",
            "total_duration_ns",
            "raw_redaction_count",
        ):
            if name in payload:
                value = payload[name]
                rows[name] = (
                    "unavailable" if value is None else "observed",
                    MEASUREMENT_UNITS.get(name),
                    value,
                )
        receipts = payload.get("receipts")
        if isinstance(receipts, list):
            for index, receipt in enumerate(receipts):
                if not isinstance(receipt, dict):
                    continue
                label = str(receipt.get("name", index))
                for field in (
                    "return_code",
                    "stdout_bytes",
                    "stderr_bytes",
                    "latency_ms",
                    "duration_ns",
                ):
                    if field not in receipt:
                        continue
                    value = receipt[field]
                    rows[f"verification.{index}.{label}.{field}"] = (
                        "unavailable" if value is None else "observed",
                        MEASUREMENT_UNITS.get(field),
                        value,
                    )
        return rows

    @staticmethod
    def _treatment(
        payload: dict[str, Any],
    ) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
        effective = payload.get("requested_role_treatment")
        if not isinstance(effective, dict):
            return None
        static_identity = payload.get("role_treatment_static_identity")
        if not isinstance(static_identity, dict):
            static_identity = effective
        claimed = payload.get("role_treatment_static_digest")
        actual = _sha256(canonical_json(static_identity))
        if claimed is not None and claimed != actual:
            raise IntegrityError("telemetry Role-Treatment digest differs from identity")
        return actual, effective, static_identity

    def record_event(
        self,
        *,
        event_id: str,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        context: dict[str, Any],
        observed_at: str,
        monotonic_ns: int | None,
        source: str,
        source_sequence: int | None = None,
        source_hash: str | None = None,
    ) -> int:
        event_id = _text(event_id, "telemetry event id")
        run_id = _text(run_id, "telemetry run id")
        event_type = _text(event_type, "telemetry event type")
        source = _text(source, "telemetry source")
        observed_at = _text(observed_at, "telemetry observation time")
        if not isinstance(payload, dict) or not isinstance(context, dict):
            raise SchemaError("telemetry payload and context must be objects")
        if (
            monotonic_ns is not None
            and (
                isinstance(monotonic_ns, bool)
                or not isinstance(monotonic_ns, int)
                or monotonic_ns < 0
            )
        ):
            raise SchemaError("telemetry monotonic time must be a nonnegative integer")
        if source_sequence is not None and (
            isinstance(source_sequence, bool)
            or not isinstance(source_sequence, int)
            or source_sequence < 1
        ):
            raise SchemaError("telemetry source sequence must be a positive integer")
        _reject_sensitive(payload)
        _reject_sensitive(context)
        dimensions = self._dimensions(payload, context)
        payload_json = _canonical_text(payload)
        context_json = _canonical_text(context)
        digest_basis = {
            "event_id": event_id,
            "run_id": run_id,
            "event_type": event_type,
            "observed_at": observed_at,
            "monotonic_ns": monotonic_ns,
            "source": source,
            "source_sequence": source_sequence,
            "source_hash": source_hash,
            "schema_version": SCHEMA_VERSION,
            **dimensions,
            "payload": payload,
            "context": context,
        }
        event_digest = self._event_digest(digest_basis)
        captured_at = _utc_now()
        captured_monotonic_ns = time.monotonic_ns()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT event_digest,collection_sequence FROM telemetry_events "
                "WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if existing is not None:
                if existing["event_digest"] != event_digest:
                    connection.rollback()
                    raise IdempotencyError(
                        f"telemetry event id reused with different content: {event_id}"
                    )
                connection.commit()
                return int(existing["collection_sequence"])
            sequence = int(
                connection.execute(
                    "SELECT COALESCE(MAX(collection_sequence),0)+1 "
                    "FROM telemetry_events WHERE run_id=?",
                    (run_id,),
                ).fetchone()[0]
            )
            try:
                connection.execute(
                    """
                    INSERT INTO telemetry_events(
                        event_id,event_digest,run_id,collection_sequence,event_type,
                        observed_at,monotonic_ns,captured_at,captured_monotonic_ns,
                        source,source_sequence,source_hash,schema_version,
                        cell_id,cell_revision,work_unit_id,attempt_id,role,
                        role_treatment_id,parent_event_id,cause_event_id,
                        payload_json,context_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        event_id,
                        event_digest,
                        run_id,
                        sequence,
                        event_type,
                        observed_at,
                        monotonic_ns,
                        captured_at,
                        captured_monotonic_ns,
                        source,
                        source_sequence,
                        source_hash,
                        SCHEMA_VERSION,
                        dimensions["cell_id"],
                        dimensions["cell_revision"],
                        dimensions["work_unit_id"],
                        dimensions["attempt_id"],
                        dimensions["role"],
                        dimensions["role_treatment_id"],
                        dimensions["parent_event_id"],
                        dimensions["cause_event_id"],
                        payload_json,
                        context_json,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise IdempotencyError(
                    "telemetry source sequence or event identity conflicts"
                ) from exc
            for relation in ("parent", "cause"):
                related = dimensions[f"{relation}_event_id"]
                if related:
                    connection.execute(
                        "INSERT INTO telemetry_relationships"
                        "(event_id,relation,related_event_id) VALUES(?,?,?)",
                        (event_id, relation, related),
                    )
            for name, (status, unit, value) in self._measurement_rows(
                event_type, payload
            ).items():
                connection.execute(
                    "INSERT INTO telemetry_measurements"
                    "(event_id,name,status,unit,value_json) VALUES(?,?,?,?,?)",
                    (event_id, name, status, unit, _canonical_text(value)),
                )
            observed_treatment = self._treatment(payload)
            if observed_treatment is not None:
                treatment_digest, effective, static_identity = observed_treatment
                route = effective.get("model_route", {})
                reasoning = effective.get("reasoning", {})
                wrapper = effective.get("wrapper", {})
                configuration = effective.get("configuration", {})
                connection.execute(
                    """
                    INSERT OR IGNORE INTO telemetry_role_treatments(
                        treatment_digest,role_treatment_id,role,harness,provider,
                        model_selector,reasoning_requested,orchestration,wrapper_id,
                        configuration_json,identity_json,static_identity_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        treatment_digest,
                        str(effective.get("id", "")),
                        str(effective.get("role", "")),
                        str(effective.get("harness", "")),
                        route.get("provider") if isinstance(route, dict) else None,
                        route.get("selector") if isinstance(route, dict) else None,
                        reasoning.get("requested")
                        if isinstance(reasoning, dict)
                        else None,
                        reasoning.get("orchestration")
                        if isinstance(reasoning, dict)
                        else None,
                        wrapper.get("id") if isinstance(wrapper, dict) else None,
                        _canonical_text(
                            configuration if isinstance(configuration, dict) else {}
                        ),
                        _canonical_text(effective),
                        _canonical_text(static_identity),
                    ),
                )
                stored = connection.execute(
                    "SELECT identity_json,static_identity_json "
                    "FROM telemetry_role_treatments WHERE treatment_digest=?",
                    (treatment_digest,),
                ).fetchone()
                if (
                    stored is None
                    or stored["identity_json"] != _canonical_text(effective)
                    or stored["static_identity_json"] != _canonical_text(static_identity)
                ):
                    connection.rollback()
                    raise IntegrityError("telemetry Role-Treatment digest collision")
                connection.execute(
                    "INSERT INTO telemetry_event_treatments"
                    "(event_id,treatment_digest,relationship) VALUES(?,?,?)",
                    (event_id, treatment_digest, "requested"),
                )
            seen_walk: set[tuple[str, str, str]] = set()
            for container in (payload, context):
                for kind, json_path, value in _walk(container):
                    key = (kind, json_path, value)
                    if key in seen_walk:
                        continue
                    seen_walk.add(key)
                    if kind == "reference":
                        connection.execute(
                            "INSERT INTO telemetry_references"
                            "(event_id,json_path,reference) VALUES(?,?,?)",
                            (event_id, json_path, value),
                        )
                    else:
                        self._insert_path(
                            connection,
                            event_id=event_id,
                            relation=json_path,
                            path=value,
                            observed_at=captured_at,
                        )
            connection.commit()
            return sequence

    @staticmethod
    def _insert_path(
        connection: sqlite3.Connection,
        *,
        event_id: str,
        relation: str,
        path: str,
        observed_at: str,
    ) -> None:
        snapshot = _path_snapshot(path)
        observation_digest = _sha256(
            canonical_json(
                {
                    "event_id": event_id,
                    "relation": relation,
                    "path": path,
                    **snapshot,
                }
            )
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO telemetry_paths(
                observation_digest,event_id,relation,path,status,path_type,mode,
                size_bytes,mtime_ns,observed_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                observation_digest,
                event_id,
                relation,
                path,
                snapshot["status"],
                snapshot["path_type"],
                snapshot["mode"],
                snapshot["size_bytes"],
                snapshot["mtime_ns"],
                observed_at,
            ),
        )

    def observe_path(self, *, event_id: str, relation: str, path: Path) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._insert_path(
                connection,
                event_id=event_id,
                relation=relation,
                path=str(path),
                observed_at=_utc_now(),
            )
            connection.commit()

    def ingest_ledger_events(
        self,
        events: Iterable[dict[str, Any]],
        *,
        ledger_path: Path,
        run_root: Path,
    ) -> None:
        for event in events:
            context = {
                "actor": event["actor"],
                "prev_hash": event["prev_hash"],
            }
            monotonic_ns = event["payload"].get("observed_monotonic_ns")
            if not isinstance(monotonic_ns, int) or isinstance(monotonic_ns, bool):
                monotonic_ns = None
            self.record_event(
                event_id=event["event_id"],
                run_id=event["run_id"],
                event_type=event["type"],
                payload=event["payload"],
                context=context,
                observed_at=event["timestamp"],
                monotonic_ns=monotonic_ns,
                source="control-ledger",
                source_sequence=event["seq"],
                source_hash=event["hash"],
            )
            self.observe_path(
                event_id=event["event_id"],
                relation="capture.ledger_path",
                path=ledger_path,
            )
            self.observe_path(
                event_id=event["event_id"],
                relation="capture.run_root",
                path=run_root,
            )
            self.observe_path(
                event_id=event["event_id"],
                relation="capture.telemetry_path",
                path=self.path,
            )

    def observe_reference(
        self,
        *,
        reference: str,
        event_id: str | None,
        status: str,
        source_kind: str,
        source_path: Path | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT OR IGNORE INTO telemetry_reference_observations(
                    reference,event_id,status,source_kind,source_path,observed_at
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    reference,
                    event_id,
                    status,
                    source_kind,
                    str(source_path) if source_path is not None else None,
                    _utc_now(),
                ),
            )
            connection.commit()

    def capture_blob(
        self,
        *,
        reference: str,
        data: bytes,
        source_kind: str,
        source_path: Path,
        event_id: str | None,
    ) -> str:
        if not isinstance(data, bytes):
            raise SchemaError("telemetry blob data must be bytes")
        if not _is_reference(reference) or _sha256(data) != reference:
            raise IntegrityError("telemetry blob reference differs from bytes")
        source_kind = _text(source_kind, "telemetry blob source kind")
        source_path = Path(source_path)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT bytes FROM telemetry_blobs WHERE reference=?",
                (reference,),
            ).fetchone()
            if existing is not None and bytes(existing["bytes"]) != data:
                connection.rollback()
                raise IntegrityError("telemetry blob digest collision")
            connection.execute(
                "INSERT OR IGNORE INTO telemetry_blobs"
                "(reference,bytes,byte_count,first_captured_at) VALUES(?,?,?,?)",
                (reference, data, len(data), _utc_now()),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO telemetry_blob_sources(
                    reference,source_kind,source_path,event_id,captured_at
                ) VALUES(?,?,?,?,?)
                """,
                (
                    reference,
                    source_kind,
                    str(source_path),
                    event_id or "",
                    _utc_now(),
                ),
            )
            connection.commit()
        self.observe_reference(
            reference=reference,
            event_id=event_id,
            status="captured",
            source_kind=source_kind,
            source_path=source_path,
        )
        return reference

    def capture_snapshot(
        self,
        *,
        reference: str,
        snapshot_directory: Path,
        event_id: str | None,
    ) -> None:
        snapshot_directory = Path(snapshot_directory)
        manifest_path = snapshot_directory / "manifest.json"
        tree = snapshot_directory / "tree"
        try:
            manifest_bytes = manifest_path.read_bytes()
            manifest = json.loads(manifest_bytes)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntegrityError(f"telemetry snapshot manifest is unavailable: {reference}") from exc
        if not isinstance(manifest, list) or _sha256(canonical_json(manifest)) != reference:
            raise IntegrityError("telemetry snapshot manifest digest differs")
        manifest_blob_ref = _sha256(manifest_bytes)
        self.capture_blob(
            reference=manifest_blob_ref,
            data=manifest_bytes,
            source_kind="snapshot-manifest",
            source_path=manifest_path,
            event_id=event_id,
        )
        entries: list[tuple[Any, ...]] = []
        for item in manifest:
            if not isinstance(item, dict):
                raise IntegrityError("telemetry snapshot entry is malformed")
            relative = item.get("path")
            entry_type = item.get("type")
            mode = item.get("mode")
            if (
                not isinstance(relative, str)
                or not relative
                or not isinstance(entry_type, str)
                or isinstance(mode, bool)
                or not isinstance(mode, int)
            ):
                raise IntegrityError("telemetry snapshot entry fields are invalid")
            blob_ref: str | None = None
            size_bytes: int | None = None
            content_sha256 = item.get("sha256")
            entry_path = tree / relative
            if entry_type == "file":
                data = entry_path.read_bytes()
                observed = hashlib.sha256(data).hexdigest()
                if content_sha256 != observed:
                    raise IntegrityError("telemetry snapshot file digest differs")
                blob_ref = DIGEST_PREFIX + observed
                size_bytes = len(data)
                self.capture_blob(
                    reference=blob_ref,
                    data=data,
                    source_kind="snapshot-file",
                    source_path=entry_path,
                    event_id=event_id,
                )
            entries.append(
                (
                    reference,
                    relative,
                    entry_type,
                    mode,
                    item.get("target"),
                    content_sha256,
                    size_bytes,
                    blob_ref,
                )
            )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT OR IGNORE INTO telemetry_snapshots(
                    snapshot_ref,manifest_json,manifest_blob_ref,source_path,
                    first_event_id,captured_at
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    reference,
                    _canonical_text(manifest),
                    manifest_blob_ref,
                    str(snapshot_directory),
                    event_id or "",
                    _utc_now(),
                ),
            )
            for entry in entries:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO telemetry_snapshot_entries(
                        snapshot_ref,relative_path,entry_type,mode,target,
                        content_sha256,size_bytes,blob_ref
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    entry,
                )
            connection.commit()
        self.observe_reference(
            reference=reference,
            event_id=event_id,
            status="captured",
            source_kind="snapshot",
            source_path=snapshot_directory,
        )

    def capture_available_references(
        self,
        *,
        artifacts: Any,
        snapshots: Any,
    ) -> None:
        with self._connect() as connection:
            rows = list(
                connection.execute(
                    "SELECT reference,MIN(event_id) AS event_id "
                    "FROM telemetry_references GROUP BY reference"
                )
            )
        for row in rows:
            reference = row["reference"]
            event_id = row["event_id"]
            artifact_path = artifacts.path_for(reference)
            snapshot_path = snapshots.path_for(reference)
            captured = False
            if artifact_path.is_file() and not artifact_path.is_symlink():
                data = artifact_path.read_bytes()
                self.capture_blob(
                    reference=reference,
                    data=data,
                    source_kind="artifact",
                    source_path=artifact_path,
                    event_id=event_id,
                )
                captured = True
            if snapshot_path.is_dir() and not snapshot_path.is_symlink():
                self.capture_snapshot(
                    reference=reference,
                    snapshot_directory=snapshot_path,
                    event_id=event_id,
                )
                captured = True
            if not captured:
                self.observe_reference(
                    reference=reference,
                    event_id=event_id,
                    status="unavailable",
                    source_kind="unresolved",
                    source_path=None,
                )

    def verify(self) -> dict[str, int]:
        with self._connect() as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise IntegrityError(f"telemetry SQLite integrity check failed: {integrity}")
            if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise IntegrityError("telemetry schema version differs")
            meta = connection.execute(
                "SELECT value FROM telemetry_meta WHERE key='schema_version'"
            ).fetchone()
            if meta is None or meta["value"] != str(SCHEMA_VERSION):
                raise IntegrityError("telemetry schema metadata differs")
            triggers = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger'"
                )
            }
            expected_triggers = {
                f"{table}_{action}"
                for table in APPEND_TABLES
                for action in ("no_update", "no_delete")
            }
            if not expected_triggers.issubset(triggers):
                raise IntegrityError("telemetry append-only triggers are incomplete")
            events = list(
                connection.execute(
                    "SELECT * FROM telemetry_events ORDER BY run_id,collection_sequence"
                )
            )
            per_run: dict[str, list[int]] = {}
            for row in events:
                payload = json.loads(row["payload_json"])
                context = json.loads(row["context_json"])
                dimensions = {
                    key: row[key]
                    for key in (
                        "cell_id",
                        "cell_revision",
                        "work_unit_id",
                        "attempt_id",
                        "role",
                        "role_treatment_id",
                        "parent_event_id",
                        "cause_event_id",
                    )
                }
                basis = {
                    "event_id": row["event_id"],
                    "run_id": row["run_id"],
                    "event_type": row["event_type"],
                    "observed_at": row["observed_at"],
                    "monotonic_ns": row["monotonic_ns"],
                    "source": row["source"],
                    "source_sequence": row["source_sequence"],
                    "source_hash": row["source_hash"],
                    "schema_version": row["schema_version"],
                    **dimensions,
                    "payload": payload,
                    "context": context,
                }
                if self._event_digest(basis) != row["event_digest"]:
                    raise IntegrityError(
                        f"telemetry event digest mismatch: {row['event_id']}"
                    )
                per_run.setdefault(row["run_id"], []).append(
                    int(row["collection_sequence"])
                )
            for run_id, sequences in per_run.items():
                if sequences != list(range(1, len(sequences) + 1)):
                    raise IntegrityError(
                        f"telemetry collection sequence has a gap: {run_id}"
                    )
            for row in connection.execute(
                "SELECT reference,bytes,byte_count FROM telemetry_blobs"
            ):
                data = bytes(row["bytes"])
                if _sha256(data) != row["reference"] or len(data) != row["byte_count"]:
                    raise IntegrityError(
                        f"telemetry blob digest mismatch: {row['reference']}"
                    )
            for row in connection.execute(
                "SELECT snapshot_ref,manifest_json FROM telemetry_snapshots"
            ):
                if _sha256(canonical_json(json.loads(row["manifest_json"]))) != row[
                    "snapshot_ref"
                ]:
                    raise IntegrityError(
                        f"telemetry snapshot digest mismatch: {row['snapshot_ref']}"
                    )
            return {
                "events": len(events),
                "measurements": connection.execute(
                    "SELECT COUNT(*) FROM telemetry_measurements"
                ).fetchone()[0],
                "references": connection.execute(
                    "SELECT COUNT(*) FROM telemetry_references"
                ).fetchone()[0],
                "paths": connection.execute(
                    "SELECT COUNT(*) FROM telemetry_paths"
                ).fetchone()[0],
                "blobs": connection.execute(
                    "SELECT COUNT(*) FROM telemetry_blobs"
                ).fetchone()[0],
                "snapshots": connection.execute(
                    "SELECT COUNT(*) FROM telemetry_snapshots"
                ).fetchone()[0],
            }
