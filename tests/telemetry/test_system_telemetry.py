from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

from support import certification_authority, digest, treatment, workflow_definition


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MOCK = ROOT / "tests" / "acceptance" / "mock_harness.py"


def make_system(base: Path, *, behavior: str):
    from loopstrap_core.system import LoopstrapSystem

    source = base / "source"
    source.mkdir()
    (source / "base.txt").write_text("base\n", encoding="utf-8")
    rows = [
        treatment(
            f"mock-{behavior}",
            harness="mock",
            model=f"deterministic-{behavior}",
            reasoning="fixed",
            command=[sys.executable, str(MOCK), "--behavior", behavior],
            capabilities=("json", "workspace_write"),
        )
    ]
    system = LoopstrapSystem.create(
        root_dir=base / "run",
        workflow=workflow_definition(),
        role_treatments={"version": 1, "role_treatments": rows},
        role_policy={
            "version": 1,
            "roles": {"implementer": {"role_treatment": f"mock-{behavior}"}},
        },
        source_dir=source,
        certification_authority=certification_authority(rows, base),
    )
    return system, rows


def prepare(system, *, visible_digest: str | None = None, holdout_digest: str | None = None):
    system.create_root(
        "root", contract_ref="sha256:" + digest("contract"), obligations=["O1"]
    )
    system.accept_contract("root")
    system.freeze_tests(
        "root",
        visible_digest=visible_digest or digest("visible"),
        holdout_digest=holdout_digest or digest("holdout"),
        obligation_map={"O1": ["T1"]},
        executable=True,
    )
    system.record_plan(
        "root", plan_digest=digest("plan"), responsibilities={"O1": "implementation"}
    )
    system.record_pre_review("root", accepted=True, leaf=True, unresolved_seams=[])


def authorization(system, treatment_id: str):
    from loopstrap_core.authority import Authorization

    view = system.control_view("root")
    return Authorization.from_dict(
        {
            "authorization_id": "auth-implement",
            "run_id": system.run_id,
            "cell_id": "root",
            "revision": view.revision,
            "role": "implementer",
            "role_treatment_id": treatment_id,
            "act": "dispatch",
        }
    )


def dispatch(system, treatment_id: str):
    return system.dispatch(
        authorization(system, treatment_id),
        prompt_ref="sha256:" + digest("prompt"),
        context_manifest_ref="sha256:" + digest("context"),
        context_lineage="implementation-lineage",
        cache_lineage="cache-lineage",
    )


def events(path: Path, event_type: str) -> list[sqlite3.Row]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        return list(
            connection.execute(
                "SELECT * FROM telemetry_events WHERE event_type=? "
                "ORDER BY collection_sequence",
                (event_type,),
            )
        )


class SystemTelemetryAcceptance(unittest.TestCase):
    def test_successful_attempt_mirrors_ledger_process_paths_bytes_and_lineage(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            system, rows = make_system(base, behavior="write")
            prepare(system)
            job = dispatch(system, str(rows[0]["id"]))
            db = system.telemetry.path
            receipt = system.telemetry.verify()
            ledger = system.ledger.verify()
            self.assertEqual(receipt["events"], len(ledger))
            with sqlite3.connect(db) as connection:
                connection.row_factory = sqlite3.Row
                mirrored = list(
                    connection.execute(
                        "SELECT event_id,source_sequence,source_hash,payload_json "
                        "FROM telemetry_events WHERE source='control-ledger' "
                        "ORDER BY source_sequence"
                    )
                )
                self.assertEqual(
                    [row["source_sequence"] for row in mirrored],
                    list(range(1, len(ledger) + 1)),
                )
                self.assertEqual(
                    [row["event_id"] for row in mirrored],
                    [event["event_id"] for event in ledger],
                )
                self.assertEqual(
                    [row["source_hash"] for row in mirrored],
                    [event["hash"] for event in ledger],
                )

            started = events(db, "harness.started")
            completed = events(db, "harness.completed")
            self.assertEqual(len(started), 1)
            self.assertEqual(len(completed), 1)
            started_payload = json.loads(started[0]["payload_json"])
            completed_payload = json.loads(completed[0]["payload_json"])
            self.assertEqual(started_payload["job_id"], job.job_id)
            self.assertEqual(started_payload["prompt_ref"], job.result.prompt_ref)
            self.assertEqual(
                started_payload["context_manifest_ref"],
                job.result.context_manifest_ref,
            )
            self.assertEqual(
                started_payload["role_treatment_static_identity"]["id"],
                rows[0]["id"],
            )
            self.assertEqual(
                started_payload["paths"]["workspace"], str(job.workspace.path)
            )
            trace = completed_payload["process_trace"]
            self.assertEqual(trace["argv"], rows[0]["command"])
            self.assertEqual(trace["cwd"], str(job.workspace.path))
            self.assertIsInstance(trace["pid"], int)
            self.assertGreater(trace["pid"], 0)
            self.assertGreaterEqual(trace["ended_monotonic_ns"], trace["started_monotonic_ns"])
            self.assertEqual(
                trace["duration_ns"],
                trace["ended_monotonic_ns"] - trace["started_monotonic_ns"],
            )
            self.assertEqual(trace["return_code"], 0)
            self.assertEqual(completed[0]["parent_event_id"], started[0]["event_id"])
            self.assertEqual(completed[0]["attempt_id"], job.job_id)

            with sqlite3.connect(db) as connection:
                raw_blob = connection.execute(
                    "SELECT bytes FROM telemetry_blobs WHERE reference=?",
                    (job.result.execution_ref,),
                ).fetchone()
                response_blob = connection.execute(
                    "SELECT bytes FROM telemetry_blobs WHERE reference=?",
                    (job.response_ref,),
                ).fetchone()
            self.assertIsNotNone(raw_blob)
            self.assertEqual(
                response_blob,
                (system.artifacts.get_bytes(job.response_ref),),
            )

    def test_failed_attempt_retains_trace_and_explicitly_unavailable_usage(
        self,
    ) -> None:
        from loopstrap_core.errors import HarnessProtocolError

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            system, rows = make_system(base, behavior="malformed")
            prepare(system)
            with self.assertRaises(HarnessProtocolError):
                dispatch(system, str(rows[0]["id"]))
            db = system.telemetry.path
            started = events(db, "harness.started")
            failed = events(db, "harness.failed")
            self.assertEqual(len(started), 1)
            self.assertEqual(len(failed), 1)
            failure = json.loads(failed[0]["payload_json"])
            self.assertEqual(failure["error_class"], "HarnessProtocolError")
            self.assertGreaterEqual(failure["latency_ms"], 0)
            self.assertEqual(failure["process_trace"]["return_code"], 0)
            self.assertEqual(failed[0]["parent_event_id"], started[0]["event_id"])
            self.assertIsNotNone(failure["execution_ref"])
            with sqlite3.connect(db) as connection:
                measurements = {
                    name: status
                    for name, status in connection.execute(
                        "SELECT name,status FROM telemetry_measurements "
                        "WHERE event_id=?",
                        (failed[0]["event_id"],),
                    )
                }
                copied = connection.execute(
                    "SELECT bytes FROM telemetry_blobs WHERE reference=?",
                    (failure["execution_ref"],),
                ).fetchone()
            for name in (
                "input_tokens",
                "output_tokens",
                "cost",
                "compute",
                "retries",
                "risk",
                "human_attention",
            ):
                self.assertEqual(measurements[name], "unavailable")
            self.assertEqual(measurements["latency_ms"], "observed")
            self.assertIsNotNone(copied)
            self.assertNotIn(b"sk-", copied[0])

    def test_authoritative_open_rebuilds_a_deleted_observation_mirror(self) -> None:
        from loopstrap_core.system import LoopstrapSystem

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            system, rows = make_system(base, behavior="write")
            prepare(system)
            job = dispatch(system, str(rows[0]["id"]))
            ledger_events = system.ledger.verify()
            database = system.telemetry.path
            database.unlink()
            database.with_name(database.name + "-wal").unlink(missing_ok=True)
            database.with_name(database.name + "-shm").unlink(missing_ok=True)

            reopened = LoopstrapSystem.open(
                root_dir=base / "run",
                workflow=workflow_definition(),
                role_treatments={"version": 1, "role_treatments": rows},
                role_policy={
                    "version": 1,
                    "roles": {
                        "implementer": {"role_treatment": str(rows[0]["id"])}
                    },
                },
                certification_authority=certification_authority(rows, base / "reopen"),
            )
            self.assertEqual(reopened.run_id, system.run_id)
            self.assertIn(job.job_id, reopened.jobs)
            self.assertEqual(reopened.telemetry.verify()["events"], len(ledger_events))
            self.assertEqual(
                [
                    row["source_sequence"]
                    for row in events(database, "harness.completed")
                ],
                [
                    event["seq"]
                    for event in ledger_events
                    if event["type"] == "harness.completed"
                ],
            )

    def test_verification_receipts_are_copied_with_timing_and_attempt_relationship(
        self,
    ) -> None:
        from loopstrap_core.verification import TestCommand, VerificationPlan

        plan = VerificationPlan.create(
            [
                TestCommand(
                    name="visible-file",
                    visibility="visible",
                    argv=(
                        sys.executable,
                        "-c",
                        "from pathlib import Path; assert Path('agent-output.txt').is_file()",
                    ),
                ),
                TestCommand(
                    name="holdout-content",
                    visibility="holdout",
                    argv=(
                        sys.executable,
                        "-c",
                        "from pathlib import Path; assert 'written' in Path('agent-output.txt').read_text()",
                    ),
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            system, rows = make_system(base, behavior="write")
            prepare(
                system,
                visible_digest=plan.visible_digest,
                holdout_digest=plan.holdout_digest,
            )
            job = dispatch(system, str(rows[0]["id"]))
            report_ref = system.verify_job_with_plan(job.job_id, plan)
            test_events = events(system.telemetry.path, "tests.executed")
            self.assertEqual(len(test_events), 1)
            payload = json.loads(test_events[0]["payload_json"])
            self.assertEqual(payload["report_ref"], report_ref)
            self.assertEqual(payload["attempt_id"], job.job_id)
            self.assertEqual(payload["paths"]["workspace"], str(job.workspace.path))
            self.assertEqual(len(payload["receipts"]), 2)
            self.assertEqual(
                payload["total_duration_ns"],
                sum(receipt["duration_ns"] for receipt in payload["receipts"]),
            )
            for receipt in payload["receipts"]:
                self.assertIn("argv_digest", receipt)
                self.assertIn("return_code", receipt)
                self.assertIn("stdout_bytes", receipt)
                self.assertIn("stderr_bytes", receipt)
                self.assertIn("started_at", receipt)
                self.assertIn("ended_at", receipt)
                self.assertGreaterEqual(receipt["duration_ns"], 0)
            with sqlite3.connect(system.telemetry.path) as connection:
                copied = connection.execute(
                    "SELECT bytes FROM telemetry_blobs WHERE reference=?",
                    (report_ref,),
                ).fetchone()
            self.assertEqual(copied, (system.artifacts.get_bytes(report_ref),))
