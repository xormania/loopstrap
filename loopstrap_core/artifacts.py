from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .errors import IntegrityError


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def put_bytes(self, data: bytes, *, media_type: str) -> str:
        del media_type
        digest = self._digest(data)
        reference = f"sha256:{digest}"
        path = self.path_for(reference)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != data:
                raise IntegrityError(f"artifact collision at {reference}")
            return reference
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        try:
            os.write(descriptor, data)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return reference

    def path_for(self, reference: str) -> Path:
        try:
            algorithm, digest = reference.split(":", 1)
        except ValueError as exc:
            raise IntegrityError("malformed artifact reference") from exc
        if algorithm != "sha256" or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise IntegrityError("malformed artifact reference")
        return self.root / digest[:2] / digest

    def get_bytes(self, reference: str) -> bytes:
        path = self.path_for(reference)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IntegrityError(f"artifact missing: {reference}") from exc
        if f"sha256:{self._digest(data)}" != reference:
            raise IntegrityError(f"artifact hash mismatch: {reference}")
        return data

