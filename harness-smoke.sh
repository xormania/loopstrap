#!/usr/bin/env bash
# harness-smoke.sh — one bounded, profile-driven harness invocation.
#
#   bash harness-smoke.sh <codex|claude-code> [--live]
#
# Default mode uses tests/mocks on PATH: zero tokens, proves the seam end to
# end (profile -> rendered argv -> process -> output). --live uses the real
# CLI on PATH: spends a few tokens; a flag rejection in live mode is the D38
# drift signal — correct config/harness-profiles.v1.json, not this script.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="${1:-}"; MODE="${2:-mock}"
[ -n "$HARNESS" ] || { echo "usage: harness-smoke.sh <codex|claude-code> [--live]" >&2; exit 2; }
[ "$MODE" = "--live" ] || export PATH="$ROOT/tests/mocks:$PATH"

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
printf 'Reply with the single word READY and nothing else.\n' > "$WORK/prompt.txt"
printf '{"type":"object"}\n' > "$WORK/schema.json"

mapfile -t ARGV < <(python3 - "$ROOT" "$HARNESS" "$WORK" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from loopstrap_core.profiles import profile_for, render
root, harness, work = sys.argv[1], sys.argv[2], Path(sys.argv[3])
executable = {"codex": "codex", "claude-code": "claude"}.get(harness, harness)
profile = profile_for(harness, Path(root))
subs = {
    "vendor_executable": executable,
    "model_selector": "smoke-model",
    "reasoning_control": "model_reasoning_effort",
    "reasoning_requested": "low",
    "schema_file": str(work / "schema.json"),
    "workspace_dir": str(work),
    "prompt_file": str(work / "prompt.txt"),
    "state_dir": str(work / ".loopstrap" / (profile.get("state_subdir") or "state")),
}
source = dict(profile)
if profile.get("smoke_argv"):
    source["argv"] = profile["smoke_argv"]
    source["environment"] = {}
argv, env = render(source, subs, ())
for name, value in env.items():
    print(f"__ENV__{name}={value}")
print("__STDIN__" + profile["stdin"])
for token in argv:
    print(token)
PY
)
STDIN_MODE="none"; CMD=()
for token in "${ARGV[@]}"; do
  case "$token" in
    __ENV__*) kv="${token#__ENV__}"; export "${kv%%=*}"="${kv#*=}";;
    __STDIN__*) STDIN_MODE="${token#__STDIN__}";;
    *) CMD+=("$token");;
  esac
done
mkdir -p "$WORK/.loopstrap"
echo "smoke argv: ${CMD[*]}"
set +e
if [ "$STDIN_MODE" = "prompt" ]; then
  OUT="$(timeout 120 "${CMD[@]}" < "$WORK/prompt.txt" 2>&1)"
else
  OUT="$(timeout 120 "${CMD[@]}" 2>&1)"
fi
RC=$?
set -e
echo "---- first lines ----"; printf '%s\n' "$OUT" | head -5
echo "---- exit $RC (mode: ${MODE#--}) ----"
exit "$RC"
