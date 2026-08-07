#!/usr/bin/env bash
# Shared probe-environment setup — sourced by run.sh, anchors on the kit dir.
#
# The kit's source now lives inside loopstrap, which is a git working tree. The
# original refusal ("drop it somewhere neutral") existed because a probe repo
# git-walks upward and must never run near real project state. That property is
# kept exactly: run.sh stages the kit to a neutral directory and re-executes
# there, and this file still refuses if it finds itself inside a working tree.
set -euo pipefail
vendor="$1"
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if git -C "$KIT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "REFUSE  kit is inside a git working tree ($KIT)" >&2
  echo "        run.sh stages to a neutral directory; invoke run.sh, not this file" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="${PROBE_WORK_DIR:-$KIT/work}/${vendor}-${STAMP}"
REPORT_DIR="${PROBE_REPORT_DIR:-$KIT/reports}"
REPORT="$REPORT_DIR/${vendor}-report.md"
# The machine-readable half. The markdown is for a human; this is what
# probe-ingest.py validates and folds into config/harness-cli.v1.json, so the
# contract never has to parse prose.
SURFACE="$REPORT_DIR/${vendor}-surface.json"

mkdir -p "$WORK/probe-repo/sub" "$REPORT_DIR"
cd "$WORK/probe-repo"
[ -d .git ] || git init -q

# Credential hygiene: scrub the repo-credential class, plant the probe token.
# Vendor auth is untouched — the tool needs its own login to run at all.
unset GH_TOKEN GITHUB_TOKEN GH_ENTERPRISE_TOKEN GITHUB_ENTERPRISE_TOKEN 2>/dev/null || true
export PROBE_TOKEN=probe123

echo "kit           : $KIT"
echo "probe workdir : $WORK/probe-repo"
echo "report target : $REPORT"
echo "surface target: $SURFACE"
