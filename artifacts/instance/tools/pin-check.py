#!/usr/bin/env python3
"""Report when a pinned tool has moved upstream, and rewrite the pin on request.

Dependabot exists to resolve transitive dependency trees. This repository has
none — pyproject.toml declares zero dependencies and every import is standard
library — so the only surface it could address is two floating action tags. The
dependency that actually matters is invisible to it: a 24MB CUE binary fetched
from a GitHub release and pinned by two digests. A version bump there is
worthless without recomputing both hashes, and computing them IS the work.

Three pin kinds, three different questions:

  vendored   config/*-tool.v1.json — we hold the binary, pinned by version plus
             archive and binary sha256. Question: has upstream released newer?
             Answerable, and --update closes the loop by fetching and hashing.

  ambient    config/tools.v1.json — whatever is on PATH. Not ours to pin, so the
             question is drift: does the installed version still match what the
             evidence in this repository was produced against? No digest is
             recorded, because a digest of /usr/bin/git is machine-specific and
             would report drift on every machine that is not this one.

  actions    .github/workflows/*.yml — `uses: owner/repo@ref`. Floating major
             tags already move within a major, so the only real question is
             whether a new major exists.

It reports. It never opens a pull request: a queue of bot branches is the cost
Dependabot charges, and the whole point of checking locally is that when you act
on it you are already where the reseal and the real evidence happen.

    pin-check.py --check
    pin-check.py --update cue [--write]

Exit 0 every pin current, 1 drift found, 2 upstream could not be reached.
A network failure is exit 2, never exit 0 — "could not check" and "checked and
current" are different answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request


CONFIG_DIR = Path("config")
WORKFLOWS = Path(".github") / "workflows"
USES = re.compile(r"^\s*-?\s*uses:\s*([\w.-]+/[\w.-]+)@(\S+)", re.MULTILINE)
RELEASE_OWNER_REPO = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/releases/")


class Unreachable(Exception):
    """Upstream could not be consulted. Distinct from 'no update available'."""


def latest_release(repo: str) -> str:
    """Latest release tag for owner/repo, preferring gh for auth and rate limit."""
    if shutil.which("gh"):
        done = subprocess.run(
            ["gh", "api", f"repos/{repo}/releases/latest", "--jq", ".tag_name"],
            capture_output=True,
            text=True,
        )
        if done.returncode == 0 and done.stdout.strip():
            return done.stdout.strip()
        if "rate limit" in done.stderr.lower():
            raise Unreachable(f"{repo}: rate limited")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "loopstrap-pin-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)["tag_name"]
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError) as exc:
        raise Unreachable(f"{repo}: {exc}") from exc


def vendored_pins(root: Path) -> list[dict]:
    pins = []
    for path in sorted((root / CONFIG_DIR).glob("*-tool.v1.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        match = RELEASE_OWNER_REPO.search(data.get("release_url", ""))
        pins.append(
            {
                "path": path,
                "tool": data.get("tool", path.stem),
                "version": data.get("version", ""),
                "repo": match.group(1) if match else None,
                "data": data,
            }
        )
    return pins


def ambient_pins(root: Path) -> list[dict]:
    path = root / CONFIG_DIR / "tools.v1.json"
    if not path.is_file():
        return []
    return [
        {"name": name, **spec}
        for name, spec in json.loads(path.read_text(encoding="utf-8"))["tools"].items()
    ]


def installed_version(spec: dict) -> str | None:
    command = spec.get("version_command")
    if not command or not shutil.which(command[0]):
        return None
    done = subprocess.run(command, capture_output=True, text=True)
    text = (done.stdout + done.stderr).strip()
    match = re.search(spec["version_pattern"], text)
    return match.group(1) if match else None


def action_pins(root: Path) -> list[tuple[str, str, Path]]:
    found = []
    for path in sorted((root / WORKFLOWS).glob("*.yml")):
        for repo, ref in USES.findall(path.read_text(encoding="utf-8")):
            found.append((repo, ref, path))
    return found


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(root: Path) -> int:
    stale, unreachable = [], []

    print("  vendored — we hold the binary, pinned by digest")
    for pin in vendored_pins(root):
        if not pin["repo"]:
            print(f"    {pin['tool']:10} {pin['version']:12} no release URL — cannot resolve upstream")
            unreachable.append(pin["tool"])
            continue
        try:
            newest = latest_release(pin["repo"])
        except Unreachable as exc:
            print(f"    {pin['tool']:10} {pin['version']:12} UNREACHABLE — {exc}")
            unreachable.append(pin["tool"])
            continue
        mark = "" if newest == pin["version"] else f"  -> {newest} available"
        print(f"    {pin['tool']:10} {pin['version']:12} {pin['repo']}{mark}")
        if newest != pin["version"]:
            stale.append(pin["tool"])

    ambient = ambient_pins(root)
    if ambient:
        print("  ambient — on PATH, recorded so evidence is reproducible")
        for spec in ambient:
            live = installed_version(spec)
            if live is None:
                print(f"    {spec['name']:10} {spec['recorded']:12} NOT INSTALLED")
                stale.append(spec["name"])
            elif live != spec["recorded"]:
                print(f"    {spec['name']:10} {spec['recorded']:12} installed {live} — recorded value is stale")
                stale.append(spec["name"])
            else:
                print(f"    {spec['name']:10} {spec['recorded']:12} matches installed")

    actions = action_pins(root)
    if actions:
        print("  actions — floating majors; only a new major matters")
        for repo, ref, path in actions:
            try:
                newest = latest_release(repo)
            except Unreachable as exc:
                print(f"    {repo:24} {ref:8} UNREACHABLE — {exc}")
                unreachable.append(repo)
                continue
            major = newest.split(".")[0]
            mark = "" if major == ref else f"  -> {newest} ({major})"
            print(f"    {repo:24} {ref:8} {path.name}{mark}")
            if major != ref:
                stale.append(f"{repo}@{ref}")

    print()
    if unreachable:
        print(f"  COULD NOT CHECK {len(unreachable)}: {', '.join(unreachable)}")
        print("  Not checking is not the same as checking current.")
        return 2
    if stale:
        print(f"  {len(stale)} PIN(S) BEHIND: {', '.join(stale)}")
        print("  pin-check.py --update <tool> --write  fetches, hashes and rewrites.")
        print("  Reseal afterwards — the pin is a sealed file.")
        return 1
    print("  ALL PINS CURRENT")
    return 0


def update(root: Path, tool: str, write: bool) -> int:
    pins = {pin["tool"]: pin for pin in vendored_pins(root)}
    if tool not in pins:
        print(f"  no vendored pin named {tool}; have: {', '.join(sorted(pins))}", file=sys.stderr)
        return 2
    pin = pins[tool]
    if not pin["repo"]:
        print(f"  {tool} has no release URL to resolve", file=sys.stderr)
        return 2
    try:
        newest = latest_release(pin["repo"])
    except Unreachable as exc:
        print(f"  UNREACHABLE — {exc}", file=sys.stderr)
        return 2
    if newest == pin["version"]:
        print(f"  {tool} is already {newest}")
        return 0

    url = pin["data"]["release_url"].replace(pin["version"], newest)
    print(f"  {tool} {pin['version']} -> {newest}")
    print(f"  fetching {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            archive = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"  UNREACHABLE — {exc}", file=sys.stderr)
        return 2

    archive_sha = digest(archive)
    relative = pin["data"]["binary_path"].replace(pin["version"], newest)
    name = Path(relative).name
    with tempfile.TemporaryDirectory() as scratch:
        blob = Path(scratch) / "archive"
        blob.write_bytes(archive)
        with tarfile.open(blob) as tar:
            member = next((m for m in tar.getmembers() if Path(m.name).name == name), None)
            if member is None:
                print(f"  archive has no member named {name}", file=sys.stderr)
                return 2
            extracted = tar.extractfile(member)
            binary_sha = digest(extracted.read()) if extracted else ""

    updated = dict(pin["data"])
    updated.update(
        version=newest,
        binary_path=relative,
        release_url=url,
        archive_sha256=archive_sha,
        binary_sha256=binary_sha,
    )
    rendered = json.dumps(updated, indent=2) + "\n"
    if not write:
        print(f"\n{rendered}")
        print("  --write applies it. The binary itself is not fetched into tools/;")
        print("  do that deliberately, then reseal.")
        return 1
    pin["path"].write_text(rendered, encoding="utf-8")
    print(f"  wrote {pin['path']}")
    print("  The binary in tools/ is NOT replaced — fetch it deliberately, then reseal.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update", metavar="TOOL")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    if args.update:
        return update(root, args.update, args.write)
    return check(root)


if __name__ == "__main__":
    raise SystemExit(main())
