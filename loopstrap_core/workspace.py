from __future__ import annotations

from dataclasses import dataclass
import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
from typing import Any

from .atomic import atomic_write_json, canonical_json
from .errors import AuthorityError, IntegrityError, PromotionError, StaleResultError, WorkspaceBoundaryError


SAFE_JOB = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


class SnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _inventory(self, source: Path) -> list[dict[str, Any]]:
        source_real = source.resolve()
        rows: list[dict[str, Any]] = []
        for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
            relative = path.relative_to(source).as_posix()
            mode = stat.S_IMODE(path.lstat().st_mode)
            if path.is_symlink():
                target = os.readlink(path)
                resolved = (path.parent / target).resolve()
                if not _inside(resolved, source_real):
                    raise WorkspaceBoundaryError(f"symlink escapes source snapshot: {relative}")
                rows.append({"path": relative, "type": "symlink", "mode": mode, "target": target})
            elif path.is_dir():
                rows.append({"path": relative, "type": "directory", "mode": mode})
            elif path.is_file():
                content = path.read_bytes()
                rows.append(
                    {
                        "path": relative,
                        "type": "file",
                        "mode": mode,
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )
            else:
                raise WorkspaceBoundaryError(f"unsupported source entry: {relative}")
        return rows

    def capture(self, source: Path) -> str:
        source = Path(source)
        if not source.is_dir() or source.is_symlink():
            raise WorkspaceBoundaryError("snapshot source must be a real directory")
        inventory = self._inventory(source)
        digest = hashlib.sha256(canonical_json(inventory)).hexdigest()
        reference = f"sha256:{digest}"
        destination = self.root / digest
        if destination.exists():
            self.verify(reference)
            return reference
        temporary = self.root / f".{digest}.{os.getpid()}.tmp"
        if temporary.exists():
            shutil.rmtree(temporary)
        temporary.mkdir(mode=0o700)
        tree = temporary / "tree"
        shutil.copytree(source, tree, symlinks=True)
        (temporary / "manifest.json").write_bytes(canonical_json(inventory) + b"\n")
        os.replace(temporary, destination)
        return reference

    def path_for(self, reference: str) -> Path:
        try:
            algorithm, digest = reference.split(":", 1)
        except ValueError as exc:
            raise IntegrityError("malformed snapshot reference") from exc
        if algorithm != "sha256" or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise IntegrityError("malformed snapshot reference")
        return self.root / digest

    def _directory(self, reference: str) -> Path:
        return self.path_for(reference)

    def verify(self, reference: str) -> None:
        directory = self._directory(reference)
        manifest_path = directory / "manifest.json"
        tree = directory / "tree"
        if not manifest_path.is_file() or not tree.is_dir():
            raise IntegrityError(f"snapshot incomplete: {reference}")
        try:
            declared = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IntegrityError(f"snapshot manifest invalid: {reference}") from exc
        actual = self._inventory(tree)
        if declared != actual:
            raise IntegrityError(f"snapshot content drift: {reference}")
        digest = hashlib.sha256(canonical_json(actual)).hexdigest()
        if reference != f"sha256:{digest}":
            raise IntegrityError(f"snapshot digest mismatch: {reference}")

    def materialize(self, reference: str, destination: Path) -> None:
        self.verify(reference)
        destination = Path(destination)
        if destination.exists() or destination.is_symlink():
            raise WorkspaceBoundaryError(f"materialization destination already exists: {destination}")
        shutil.copytree(self._directory(reference) / "tree", destination, symlinks=True)


@dataclass(frozen=True)
class Workspace:
    job_id: str
    path: Path
    base_snapshot: str


class WorkspaceManager:
    def __init__(self, snapshots: SnapshotStore, root: Path, pointer: Path) -> None:
        self.snapshots = snapshots
        self.root = Path(root)
        self.pointer = Path(pointer)
        self.pointer_lock = self.pointer.with_name(f".{self.pointer.name}.lock")
        self.root.mkdir(parents=True, exist_ok=True)
        self.pointer_lock.touch(exist_ok=True)
        self.__permit = object()

    def initialize(self, snapshot: str) -> None:
        self.snapshots.verify(snapshot)
        if self.pointer.exists():
            current = self.current_snapshot()
            if current != snapshot:
                raise PromotionError("candidate pointer is already initialized differently")
            return
        atomic_write_json(self.pointer, {"snapshot": snapshot})

    def current_snapshot(self) -> str:
        try:
            value = json.loads(self.pointer.read_text(encoding="utf-8"))
            snapshot = value["snapshot"]
        except (OSError, KeyError, json.JSONDecodeError, TypeError) as exc:
            raise IntegrityError("candidate pointer is missing or malformed") from exc
        self.snapshots.verify(snapshot)
        return snapshot

    def prepare(self, job_id: str, base_snapshot: str) -> Workspace:
        if not SAFE_JOB.fullmatch(job_id):
            raise WorkspaceBoundaryError(f"unsafe job id: {job_id}")
        path = self.root / job_id
        if path.exists() or path.is_symlink():
            raise WorkspaceBoundaryError(f"workspace already exists: {job_id}")
        self.snapshots.materialize(base_snapshot, path)
        return Workspace(job_id=job_id, path=path, base_snapshot=base_snapshot)

    def capture_result(self, workspace: Workspace, *, verified: bool) -> str:
        if not verified:
            raise PromotionError("unverified workspace cannot become a candidate")
        expected = self.root / workspace.job_id
        if workspace.path != expected or not _inside(workspace.path.resolve(), self.root.resolve()):
            raise WorkspaceBoundaryError("workspace is outside manager custody")
        return self.snapshots.capture(workspace.path)

    def _executor_permit(self) -> object:
        return self.__permit

    def promote(self, snapshot: str, *, expected_current: str, permit: object | None) -> None:
        if permit is not self.__permit:
            raise AuthorityError("only the deterministic executor may promote a candidate")
        self.snapshots.verify(snapshot)
        with self.pointer_lock.open("r+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                current = self.current_snapshot()
                if current != expected_current:
                    raise StaleResultError(
                        f"candidate changed: expected {expected_current}, current is {current}"
                    )
                atomic_write_json(self.pointer, {"snapshot": snapshot})
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
