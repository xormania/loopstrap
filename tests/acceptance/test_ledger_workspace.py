from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import unittest

from support import digest


class LedgerAcceptance(unittest.TestCase):
    def test_ledger_is_sequence_numbered_hash_chained_and_tamper_evident(self) -> None:
        from loopstrap_core.errors import IntegrityError
        from loopstrap_core.ledger import EventLedger

        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.jsonl"
            ledger = EventLedger(path, run_id="run-1")
            ledger.append("e1", "run.created", "executor", {"workflow": "v1"})
            ledger.append("e2", "cell.created", "executor", {"cell_id": "root"})
            events = ledger.verify()
            self.assertEqual([event["seq"] for event in events], [1, 2])
            self.assertEqual(events[1]["prev_hash"], events[0]["hash"])
            original = path.read_text(encoding="utf-8")
            path.write_text(original.replace('"cell_id":"root"', '"cell_id":"evil"'), encoding="utf-8")
            with self.assertRaises(IntegrityError):
                ledger.verify()

    def test_idempotent_retry_is_noop_but_conflicting_reuse_is_rejected(self) -> None:
        from loopstrap_core.errors import IdempotencyError
        from loopstrap_core.ledger import EventLedger

        with tempfile.TemporaryDirectory() as raw:
            ledger = EventLedger(Path(raw) / "events.jsonl", run_id="run-1")
            first = ledger.append("stable-key", "job.dispatched", "executor", {"job_id": "j1"})
            retry = ledger.append("stable-key", "job.dispatched", "executor", {"job_id": "j1"})
            self.assertEqual(first, retry)
            self.assertEqual(len(ledger.verify()), 1)
            with self.assertRaises(IdempotencyError):
                ledger.append("stable-key", "job.dispatched", "executor", {"job_id": "j2"})

    def test_partial_final_record_is_quarantined_without_rewriting_verified_prefix(self) -> None:
        from loopstrap_core.errors import IntegrityError
        from loopstrap_core.ledger import EventLedger

        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.jsonl"
            ledger = EventLedger(path, run_id="run-1")
            ledger.append("e1", "run.created", "executor", {})
            prefix = path.read_bytes()
            with path.open("ab") as stream:
                stream.write(b'{"seq":2,"incomplete"')
            with self.assertRaises(IntegrityError):
                ledger.verify()
            quarantine = ledger.quarantine_partial_tail()
            self.assertEqual(path.read_bytes(), prefix)
            self.assertEqual(quarantine.read_bytes(), b'{"seq":2,"incomplete"')
            self.assertEqual(len(ledger.verify()), 1)

    def test_concurrent_appenders_produce_one_complete_total_order(self) -> None:
        from loopstrap_core.ledger import EventLedger

        with tempfile.TemporaryDirectory() as raw:
            ledger = EventLedger(Path(raw) / "events.jsonl", run_id="run-1")
            barrier = threading.Barrier(9)
            errors: list[BaseException] = []

            def append(index: int) -> None:
                try:
                    barrier.wait()
                    ledger.append(f"e-{index}", "observation", "worker", {"index": index})
                except BaseException as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=append, args=(index,)) for index in range(8)]
            for thread in threads:
                thread.start()
            barrier.wait()
            for thread in threads:
                thread.join()
            self.assertEqual(errors, [])
            events = ledger.verify()
            self.assertEqual([event["seq"] for event in events], list(range(1, 9)))
            self.assertEqual({event["payload"]["index"] for event in events}, set(range(8)))

    def test_credential_shaped_evidence_is_rejected(self) -> None:
        from loopstrap_core.errors import SensitiveDataError
        from loopstrap_core.ledger import EventLedger

        with tempfile.TemporaryDirectory() as raw:
            ledger = EventLedger(Path(raw) / "events.jsonl", run_id="run-1")
            bad_payloads = (
                {"token": "secret"},
                {"nested": {"password": "secret"}},
                {"authorization": "Bearer abcdefghijklmnopqrstuvwxyz"},
                {"value": "ghp_abcdefghijklmnopqrstuvwxyz123456"},
            )
            for index, payload in enumerate(bad_payloads):
                with self.assertRaises(SensitiveDataError):
                    ledger.append(f"bad-{index}", "bad", "worker", payload)
            self.assertEqual(ledger.verify(), [])

    def test_reducer_rebuilds_identical_state_from_verified_events(self) -> None:
        from loopstrap_core.ledger import EventLedger
        from loopstrap_core.state import StateReducer

        with tempfile.TemporaryDirectory() as raw:
            ledger = EventLedger(Path(raw) / "events.jsonl", run_id="run-1")
            ledger.append("e1", "cell.created", "executor", {"cell_id": "root", "phase": "tests"})
            ledger.append(
                "e2",
                "cell.transitioned",
                "executor",
                {"cell_id": "root", "from": "tests", "to": "plan", "revision": 2},
            )
            first = StateReducer.replay(ledger.verify())
            second = StateReducer.replay(EventLedger(ledger.path, run_id="run-1").verify())
            self.assertEqual(first, second)
            self.assertEqual(first["cells"]["root"]["phase"], "plan")


class ArtifactAndWorkspaceAcceptance(unittest.TestCase):
    def make_source(self, root: Path) -> Path:
        source = root / "source"
        source.mkdir()
        (source / "main.txt").write_text("original\n", encoding="utf-8")
        (source / "nested").mkdir()
        (source / "nested" / "data.txt").write_text("data\n", encoding="utf-8")
        return source

    def test_artifacts_are_content_addressed_and_immutable(self) -> None:
        from loopstrap_core.artifacts import ArtifactStore
        from loopstrap_core.errors import IntegrityError

        with tempfile.TemporaryDirectory() as raw:
            store = ArtifactStore(Path(raw) / "artifacts")
            ref1 = store.put_bytes(b"same bytes", media_type="text/plain")
            ref2 = store.put_bytes(b"same bytes", media_type="text/plain")
            self.assertEqual(ref1, ref2)
            self.assertEqual(store.get_bytes(ref1), b"same bytes")
            object_path = store.path_for(ref1)
            object_path.chmod(0o600)
            object_path.write_bytes(b"tampered")
            with self.assertRaises(IntegrityError):
                store.get_bytes(ref1)

    def test_agent_workspace_isolated_until_executor_promotion(self) -> None:
        from loopstrap_core.executor import Executor
        from loopstrap_core.workspace import SnapshotStore, WorkspaceManager

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self.make_source(root)
            snapshots = SnapshotStore(root / "snapshots")
            base = snapshots.capture(source)
            manager = WorkspaceManager(snapshots, root / "workspaces", root / "candidate.json")
            manager.initialize(base)
            workspace = manager.prepare("job-1", base)
            (workspace.path / "main.txt").write_text("candidate\n", encoding="utf-8")
            self.assertEqual((source / "main.txt").read_text(encoding="utf-8"), "original\n")
            self.assertEqual(manager.current_snapshot(), base)
            candidate = manager.capture_result(workspace, verified=True)
            self.assertEqual(manager.current_snapshot(), base)
            Executor("executor-1").promote(manager, candidate, expected_current=base)
            self.assertEqual(manager.current_snapshot(), candidate)
            materialized = root / "materialized"
            snapshots.materialize(candidate, materialized)
            self.assertEqual((materialized / "main.txt").read_text(encoding="utf-8"), "candidate\n")

    def test_workspace_rejects_escape_paths_and_external_symlinks(self) -> None:
        from loopstrap_core.errors import WorkspaceBoundaryError
        from loopstrap_core.workspace import SnapshotStore, WorkspaceManager

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self.make_source(root)
            outside = root / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            os.symlink(outside, source / "escape")
            snapshots = SnapshotStore(root / "snapshots")
            with self.assertRaises(WorkspaceBoundaryError):
                snapshots.capture(source)
            (source / "escape").unlink()
            os.symlink("nested/data.txt", source / "inside")
            base = snapshots.capture(source)
            manager = WorkspaceManager(snapshots, root / "workspaces", root / "candidate.json")
            manager.initialize(base)
            for job_id in ("../escape", "/absolute", "nested/job"):
                with self.assertRaises(WorkspaceBoundaryError, msg=job_id):
                    manager.prepare(job_id, base)

    def test_direct_or_failed_promotion_is_refused(self) -> None:
        from loopstrap_core.errors import AuthorityError, PromotionError
        from loopstrap_core.workspace import SnapshotStore, WorkspaceManager

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self.make_source(root)
            snapshots = SnapshotStore(root / "snapshots")
            base = snapshots.capture(source)
            manager = WorkspaceManager(snapshots, root / "workspaces", root / "candidate.json")
            manager.initialize(base)
            workspace = manager.prepare("job-1", base)
            (workspace.path / "main.txt").write_text("unverified\n", encoding="utf-8")
            with self.assertRaises(PromotionError):
                manager.capture_result(workspace, verified=False)
            candidate = manager.capture_result(workspace, verified=True)
            with self.assertRaises(AuthorityError):
                manager.promote(candidate, expected_current=base, permit=None)
            self.assertEqual(manager.current_snapshot(), base)

    def test_promotion_compare_and_swap_rejects_stale_result(self) -> None:
        from loopstrap_core.errors import StaleResultError
        from loopstrap_core.executor import Executor
        from loopstrap_core.workspace import SnapshotStore, WorkspaceManager

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self.make_source(root)
            snapshots = SnapshotStore(root / "snapshots")
            base = snapshots.capture(source)
            manager = WorkspaceManager(snapshots, root / "workspaces", root / "candidate.json")
            manager.initialize(base)
            executor = Executor("executor")
            w1 = manager.prepare("job-1", base)
            w2 = manager.prepare("job-2", base)
            (w1.path / "main.txt").write_text("first\n", encoding="utf-8")
            (w2.path / "main.txt").write_text("stale\n", encoding="utf-8")
            first = manager.capture_result(w1, verified=True)
            stale = manager.capture_result(w2, verified=True)
            executor.promote(manager, first, expected_current=base)
            pointer_before = (root / "candidate.json").read_bytes()
            with self.assertRaises(StaleResultError):
                executor.promote(manager, stale, expected_current=base)
            self.assertEqual((root / "candidate.json").read_bytes(), pointer_before)

    def test_atomic_candidate_pointer_survives_interrupted_replacement(self) -> None:
        from loopstrap_core.atomic import atomic_write_json

        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "candidate.json"
            atomic_write_json(path, {"snapshot": "one"})

            def fail_before_replace(_temporary: Path, _target: Path) -> None:
                raise OSError("injected replacement failure")

            with self.assertRaises(OSError):
                atomic_write_json(path, {"snapshot": "two"}, before_replace=fail_before_replace)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"snapshot": "one"})
            leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
            self.assertEqual(leftovers, [])

