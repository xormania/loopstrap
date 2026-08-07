#!/usr/bin/env python3
"""Is the binary about to be launched the one that was probed?

Vendors ship often. A surface snapshot is only true of the exact executable that
produced it, so the snapshot needs an invalidation signal that is cheap enough to
run before every loop, not once per release.

That signal is identity, not behaviour: the version string the binary reports and
the sha256 of the resolved file. No tokens, no vendor round trip, milliseconds.
If either moved, the recorded surface describes a different program and every
C-CLI finding derived from it is stale.

This is a PREFLIGHT, deliberately not a battery leg. It reads whatever happens to
be installed on this machine, so its result is environment-dependent — exactly
the nondeterminism the battery must not contain. The battery proves the tree is
consistent; this proves the machine matches the tree.

    harness-identity.py [--root DIR] [--harness NAME] [--require-probed]

Exit 0 all known harnesses match, 1 on drift, 2 on a configuration problem.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def resolve(executable: str) -> Path | None:
    found = shutil.which(executable)
    return Path(found).resolve() if found else None


def installed_version(executable: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=20,
            env={"PATH": "/usr/bin:/bin:" + (Path.home() / ".local/bin").as_posix(),
                 "LC_ALL": "C", "TZ": "UTC", "HOME": str(Path.home())},
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return (completed.stdout or completed.stderr).strip().splitlines()[0] if (
        completed.stdout or completed.stderr
    ) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--harness")
    parser.add_argument(
        "--require-probed",
        action="store_true",
        help="also fail when a harness surface has never been probed",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    cli = json.loads((root / "config" / "harness-cli.v1.json").read_text("utf-8"))
    treatments = json.loads(
        (root / "config" / "role-treatments.v1.json").read_text("utf-8")
    )["role_treatments"]
    executables = {t["harness"]: t["wrapper"]["vendor_executable"] for t in treatments}

    drift: list[str] = []
    notes: list[str] = []
    checked = 0

    for harness, surface in sorted(cli["harnesses"].items()):
        if args.harness and harness != args.harness:
            continue
        executable = executables.get(harness)
        if not executable:
            notes.append(f"{harness}: no Role-Treatment names an executable; not checked")
            continue

        if surface["provenance"] != "probed":
            message = (
                f"{harness}: surface is '{surface['provenance']}', never probed — "
                f"identity cannot be verified against a snapshot that was asserted"
            )
            (drift if args.require_probed else notes).append(message)
            continue

        path = resolve(executable)
        if path is None:
            notes.append(f"{harness}: {executable!r} is not installed here; not checked")
            continue

        checked += 1
        reported = installed_version(executable)
        if reported is None:
            drift.append(f"{harness}: {executable} --version did not answer")
            continue
        if surface["version"] not in reported:
            drift.append(
                f"{harness}: installed reports {reported!r}, snapshot recorded "
                f"{surface['version']!r} — re-probe before arming"
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if surface["binary_sha256"] and digest != surface["binary_sha256"]:
            drift.append(
                f"{harness}: {path} sha256 {digest[:16]}… does not match the probed "
                f"{surface['binary_sha256'][:16]}… — same version string, different "
                f"binary"
            )

    for note in notes:
        print(f"  note   {note}")
    if drift:
        print(f"HARNESS IDENTITY DRIFT — {len(drift)} finding(s)", file=sys.stderr)
        for item in drift:
            print(f"  {item}", file=sys.stderr)
        print(
            "\nThe recorded surface describes a different program. Re-run "
            "probe/run.sh and ingest before arming.",
            file=sys.stderr,
        )
        return 1
    print(f"HARNESS IDENTITY OK — {checked} harness(es) match their probed snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
