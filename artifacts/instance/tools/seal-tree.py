#!/usr/bin/env python3
"""Regenerate loopstrap.modes and loopstrap.manifest for a clean source tree."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys


def regular_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for base, dirs, names in os.walk(root, followlinks=False):
        base_path = Path(base)
        dirs[:] = sorted(
            name for name in dirs if not (base_path / name).is_symlink()
        )
        for name in sorted(names):
            path = base_path / name
            if path.name == "loopstrap.manifest" or path.is_symlink():
                continue
            if path.is_file():
                result.append(path)
    return sorted(result, key=lambda path: path.relative_to(root).as_posix())


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    modes_path = root / "loopstrap.modes"
    modes_path.touch(mode=0o644, exist_ok=True)
    os.chmod(modes_path, 0o644)

    files = regular_files(root)
    mode_text = "".join(
        f"{stat.S_IMODE(path.stat().st_mode):04o}\t{path.relative_to(root).as_posix()}\n"
        for path in files
    )
    modes_path.write_text(mode_text, encoding="utf-8")

    files = regular_files(root)
    manifest_text = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  ./{path.relative_to(root).as_posix()}\n"
        for path in files
    )
    (root / "loopstrap.manifest").write_text(manifest_text, encoding="utf-8")
    print(f"SEALED — {len(files)} files with hashes and modes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
