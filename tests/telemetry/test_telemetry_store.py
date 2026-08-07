from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def treatment() -> dict[str, object]:
    return {
        "id": "implementer-mock-v1",
        "role": "implementer",
        "harness": "mock",
        "model_route": {
            "provider": "mock-provider",
            "selector": "mock-model",
            "allowed_resolved_models": ["mock-model"],
            "fallback_policy": "deny",
        },
        "reasoning": {
            "control": "effort",
            "requested": "high",
            "expected_wire": "high",
            "orchestration": "single-agent",
            "proof_sources": ["runtime_event"],
        },
        "wrapper": {
            "id": "mock-wrapper",
            "version": "1",
            "vendor_executable": "mock",
        },
        "configuration": {"profile": "strict", "temperature": 0},
        "capabilities": ["json", "workspace_write"],
    }


class TelemetryStoreAcceptance(unittest.TestCase):
    def test_versioned_wal_store_is_idempotent_append_only_and_tamper_evident(
        self,
    ) -> None:
        from loopstrap_core.errors import IdempotencyError, IntegrityError
        from loopstrap_core.telemetry import TelemetryStore

        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "telemetry.sqlite3"
            store = TelemetryStore(path)
            first = store.record_event(
                event_id="event-1",
                run_id="run-1",
                event_type="run.created",
                payload={"state": "created"},
                context={"work_unit_id": "root"},
                observed_at="2026-07-24T04:00:00.000000Z",
                monotonic_ns=100,
                source="test",
                source_sequence=1,
                source_hash="a" * 64,
            )
            replay = store.record_event(
                event_id="event-1",
                run_id="run-1",
                event_type="run.created",
                payload={"state": "created"},
                context={"work_unit_id": "root"},
                observed_at="2026-07-24T04:00:00.000000Z",
                monotonic_ns=100,
                source="test",
                source_sequence=1,
                source_hash="a" * 64,
            )
            self.assertEqual(first, replay)
            with self.assertRaises(IdempotencyError):
                store.record_event(
                    event_id="event-1",
                    run_id="run-1",
                    event_type="run.created",
                    payload={"state": "different"},
                    context={"work_unit_id": "root"},
                    observed_at="2026-07-24T04:00:00.000000Z",
                    monotonic_ns=100,
                    source="test",
                    source_sequence=1,
                    source_hash="a" * 64,
                )
            receipt = store.verify()
            self.assertEqual(receipt["events"], 1)

            with sqlite3.connect(path) as connection:
                self.assertEqual(
                    connection.execute("PRAGMA journal_mode").fetchone()[0].lower(),
                    "wal",
                )
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "UPDATE telemetry_events SET event_type='changed' "
                        "WHERE event_id='event-1'"
                    )
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "DELETE FROM telemetry_events WHERE event_id='event-1'"
                    )
                connection.execute("DROP TRIGGER telemetry_events_no_update")
                connection.execute(
                    "UPDATE telemetry_events SET event_type='changed' "
                    "WHERE event_id='event-1'"
                )
            with self.assertRaises(IntegrityError):
                store.verify()

    def test_raw_usage_identity_references_paths_and_relationships_are_lossless(
        self,
    ) -> None:
        from loopstrap_core.telemetry import TelemetryStore

        prompt_ref = digest(b"prompt")
        execution_ref = digest(b"execution")
        role_treatment = treatment()
        payload = {
            "job_id": "job-1",
            "cell_id": "root.1",
            "cell_revision": 7,
            "role": "implementer",
            "role_treatment_id": role_treatment["id"],
            "requested_role_treatment": role_treatment,
            "usage": {
                "input_tokens": 120,
                "output_tokens": None,
                "cost": None,
                "cache_read_tokens": 80,
                "vendor_breakdown": {"reasoning_tokens": 40},
            },
            "latency_ms": 1500,
            "duration_ns": 1_500_000_000,
            "prompt_ref": prompt_ref,
            "execution_ref": execution_ref,
            "workspace_path": "/tmp/run/workspaces/job-1",
        }
        context = {
            "work_unit_id": "root.1",
            "attempt_id": "job-1",
            "parent_event_id": "started-1",
            "cause_event_id": "reservation-1",
            "paths": {
                "run_root": "/tmp/run",
                "workspace": "/tmp/run/workspaces/job-1",
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "telemetry.sqlite3"
            store = TelemetryStore(path)
            store.record_event(
                event_id="completed-1",
                run_id="run-1",
                event_type="harness.completed",
                payload=payload,
                context=context,
                observed_at="2026-07-24T04:00:01.500000Z",
                monotonic_ns=1_600_000_000,
                source="control-ledger",
                source_sequence=9,
                source_hash="b" * 64,
            )
            store.verify()
            with sqlite3.connect(path) as connection:
                connection.row_factory = sqlite3.Row
                event = connection.execute(
                    "SELECT * FROM telemetry_events WHERE event_id='completed-1'"
                ).fetchone()
                assert event is not None
                self.assertEqual(json.loads(event["payload_json"]), payload)
                self.assertEqual(json.loads(event["context_json"]), context)
                self.assertEqual(event["collection_sequence"], 1)
                self.assertEqual(event["source_sequence"], 9)
                self.assertEqual(event["cell_id"], "root.1")
                self.assertEqual(event["work_unit_id"], "root.1")
                self.assertEqual(event["attempt_id"], "job-1")
                self.assertEqual(event["parent_event_id"], "started-1")
                self.assertEqual(event["cause_event_id"], "reservation-1")

                measurements = {
                    row["name"]: (row["status"], json.loads(row["value_json"]))
                    for row in connection.execute(
                        "SELECT name,status,value_json FROM telemetry_measurements "
                        "WHERE event_id='completed-1'"
                    )
                }
                self.assertEqual(measurements["input_tokens"], ("observed", 120))
                self.assertEqual(measurements["output_tokens"], ("unavailable", None))
                self.assertEqual(measurements["cost"], ("unavailable", None))
                self.assertEqual(measurements["cache_read_tokens"], ("observed", 80))
                self.assertEqual(
                    measurements["vendor_breakdown"],
                    ("observed", {"reasoning_tokens": 40}),
                )
                self.assertEqual(measurements["latency_ms"], ("observed", 1500))
                self.assertEqual(
                    measurements["duration_ns"], ("observed", 1_500_000_000)
                )

                identity = connection.execute(
                    "SELECT * FROM telemetry_role_treatments"
                ).fetchone()
                assert identity is not None
                self.assertEqual(identity["role_treatment_id"], "implementer-mock-v1")
                self.assertEqual(identity["role"], "implementer")
                self.assertEqual(identity["harness"], "mock")
                self.assertEqual(identity["provider"], "mock-provider")
                self.assertEqual(identity["model_selector"], "mock-model")
                self.assertEqual(identity["reasoning_requested"], "high")
                self.assertEqual(identity["orchestration"], "single-agent")
                self.assertEqual(identity["wrapper_id"], "mock-wrapper")
                self.assertEqual(json.loads(identity["identity_json"]), role_treatment)

                references = {
                    (row["json_path"], row["reference"])
                    for row in connection.execute(
                        "SELECT json_path,reference FROM telemetry_references "
                        "WHERE event_id='completed-1'"
                    )
                }
                self.assertIn(("$.prompt_ref", prompt_ref), references)
                self.assertIn(("$.execution_ref", execution_ref), references)
                paths = {
                    (row["relation"], row["path"])
                    for row in connection.execute(
                        "SELECT relation,path FROM telemetry_paths "
                        "WHERE event_id='completed-1'"
                    )
                }
                self.assertIn(("$.workspace_path", "/tmp/run/workspaces/job-1"), paths)
                self.assertIn(("$.paths.run_root", "/tmp/run"), paths)

    def test_available_blobs_and_snapshot_files_are_copied_and_deduplicated(
        self,
    ) -> None:
        from loopstrap_core.telemetry import TelemetryStore
        from loopstrap_core.workspace import SnapshotStore

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = TelemetryStore(root / "telemetry.sqlite3")
            data = b"same bytes\n"
            reference = digest(data)
            first = root / "artifact-a"
            second = root / "artifact-b"
            first.write_bytes(data)
            second.write_bytes(data)
            store.capture_blob(
                reference=reference,
                data=data,
                source_kind="artifact",
                source_path=first,
                event_id="event-1",
            )
            store.capture_blob(
                reference=reference,
                data=data,
                source_kind="artifact-copy",
                source_path=second,
                event_id="event-2",
            )

            source = root / "source"
            source.mkdir()
            (source / "a.txt").write_bytes(data)
            (source / "b.txt").write_text("different\n", encoding="utf-8")
            snapshots = SnapshotStore(root / "snapshots")
            snapshot_ref = snapshots.capture(source)
            store.capture_snapshot(
                reference=snapshot_ref,
                snapshot_directory=snapshots.path_for(snapshot_ref),
                event_id="snapshot-event",
            )
            receipt = store.verify()
            self.assertEqual(receipt["snapshots"], 1)
            with sqlite3.connect(store.path) as connection:
                copied = connection.execute(
                    "SELECT bytes FROM telemetry_blobs WHERE reference=?",
                    (reference,),
                ).fetchone()
                self.assertEqual(copied, (data,))
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM telemetry_blobs WHERE reference=?",
                        (reference,),
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM telemetry_blob_sources WHERE reference=?",
                        (reference,),
                    ).fetchone()[0],
                    3,
                )
                entries = connection.execute(
                    "SELECT relative_path,entry_type,blob_ref "
                    "FROM telemetry_snapshot_entries WHERE snapshot_ref=? "
                    "ORDER BY relative_path",
                    (snapshot_ref,),
                ).fetchall()
                self.assertEqual([row[0] for row in entries], ["a.txt", "b.txt"])
                self.assertEqual(entries[0][2], reference)

    def test_concurrent_writers_receive_gap_free_collection_order(self) -> None:
        from loopstrap_core.telemetry import TelemetryStore

        with tempfile.TemporaryDirectory() as raw:
            store = TelemetryStore(Path(raw) / "telemetry.sqlite3")

            def append(index: int) -> None:
                store.record_event(
                    event_id=f"event-{index:03d}",
                    run_id="run-1",
                    event_type="sample",
                    payload={"index": index},
                    context={},
                    observed_at=f"2026-07-24T04:00:{index % 60:02d}.000000Z",
                    monotonic_ns=index,
                    source="concurrent-test",
                )

            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(append, range(40)))
            with sqlite3.connect(store.path) as connection:
                sequences = [
                    row[0]
                    for row in connection.execute(
                        "SELECT collection_sequence FROM telemetry_events "
                        "WHERE run_id='run-1' ORDER BY collection_sequence"
                    )
                ]
            self.assertEqual(sequences, list(range(1, 41)))
            self.assertEqual(store.verify()["events"], 40)

    def test_sensitive_payload_is_refused_before_persistence(self) -> None:
        from loopstrap_core.errors import SensitiveDataError
        from loopstrap_core.telemetry import TelemetryStore

        with tempfile.TemporaryDirectory() as raw:
            store = TelemetryStore(Path(raw) / "telemetry.sqlite3")
            with self.assertRaises(SensitiveDataError):
                store.record_event(
                    event_id="event-secret",
                    run_id="run-1",
                    event_type="bad",
                    payload={"api_key": "do-not-store"},
                    context={},
                    observed_at="2026-07-24T04:00:00.000000Z",
                    monotonic_ns=1,
                    source="test",
                )
            self.assertEqual(store.verify()["events"], 0)
