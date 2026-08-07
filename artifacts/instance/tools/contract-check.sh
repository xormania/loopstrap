#!/usr/bin/env bash
# contract-check.sh — static coherence gate over the development contract.
#
# Two families, evaluated separately because they join different facts:
#   schema  — Python exact-field sets against CUE closed definitions
#   config  — the seven config/*.json files held in one namespace
#
# Fast, hermetic, deterministic: no clock, no network, no ordering dependence,
# no sleep.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CUE="$ROOT/tools/cue/v0.17.0/cue"

[ -x "$CUE" ] || { echo "CONTRACT ABORT: pinned CUE binary absent: $CUE" >&2; exit 2; }

# The escape hatch. A gate that cannot be stepped around eventually stops being a
# gate and starts being a wall — that is the specific way a development lane
# suffocates a project. This one is always available and never silent.
if [ "${LOOPSTRAP_GATE:-on}" = "off" ]; then
  echo "CONTRACT SKIPPED — LOOPSTRAP_GATE=off" >&2
  echo "  The gate was stepped around deliberately. Nothing was checked." >&2
  echo "  If this becomes routine, the gate is wrong, not the person skipping it." >&2
  exit 0
fi

# Budget. Counted from the emission lines, so it measures what can actually fire
# rather than what is written down.
BUDGET="$(python3 -c '
import json, sys
try:
    print(json.load(open(sys.argv[1]))["max_invariants"])
except Exception:
    print(-1)
' "$ROOT/config/gate-budget.v1.json")"
LIVE="$(grep -ohE 'for subject, reason in _[A-Za-z0-9]+' "$ROOT"/contract/*.cue | sort -u | wc -l)"
if [ "$BUDGET" -ge 0 ] && [ "$LIVE" -gt "$BUDGET" ]; then
  echo "CONTRACT FAILED — invariant budget exceeded: $LIVE live, $BUDGET allowed" >&2
  echo "  Delete one, or raise max_invariants in config/gate-budget.v1.json." >&2
  echo "  Raising it is a sealed change and shows in the seal delta, which is the point:" >&2
  echo "  this gate cannot grow without someone deciding that it should." >&2
  exit 1
fi

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

FAIL=0
DEFERRED_TOTAL=0

count_json() { python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'; }
print_rows() {
  python3 -c '
import json, sys
prefix = sys.argv[1]
for subject, reason in sorted(json.load(sys.stdin).items()):
    print(f"{prefix}{subject}: {reason}")
' "$1"
}

# --- C-SEAL-001 -------------------------------------------------------------
# The exclusion rules compiled into seal-tree.py and verify-tree.py must match
# config/seal.v1.json. Same idea as a framework checking its compiled container
# against the authored config.
if ! python3 "$ROOT/artifacts/instance/tools/gen-seal-rules.py" --root "$ROOT" --check >/dev/null 2>&1; then
  echo "CONTRACT FAILED — C-SEAL-001: compiled seal rules are stale" >&2
  echo "  fix: python3 artifacts/instance/tools/gen-seal-rules.py" >&2
  exit 1
fi

# --- schema family ----------------------------------------------------------
FACTS="$SCRATCH/facts.json"
python3 "$ROOT/artifacts/instance/tools/schema-facts.py" --root "$ROOT" --out "$FACTS"

if ! SCHEMA_DIAG="$(cd "$ROOT" && "$CUE" export \
      contract/extracted.cue \
      contract/declaration_schema_pairs.cue \
      contract/invariant_schema.cue \
      contract/invariant_lanes.cue \
      "$FACTS" -e diagnostics --out json 2>&1)"; then
  echo "CONTRACT ABORT: the schema contract failed to evaluate" >&2
  printf '%s\n' "$SCHEMA_DIAG" >&2
  exit 2
fi

# --- config family ----------------------------------------------------------
# CUE reads the JSON directly; --with-context supplies the filename so each file
# lands under its own key. Four of the seven declare a top-level `version`, so
# the nesting is load-bearing, not cosmetic.
CONFIGS="$SCRATCH/configs.json"
if ! (cd "$ROOT" && "$CUE" export --with-context \
      -l '"configs"' \
      -l 'strings.TrimSuffix(path.Base(filename), ".v1.json")' \
      -l '"data"' \
      config/*.json --out json) > "$CONFIGS" 2>"$SCRATCH/err"; then
  echo "CONTRACT ABORT: the config set failed to merge" >&2
  cat "$SCRATCH/err" >&2
  exit 2
fi

for expression in diagnostics deferred; do
  if ! OUT="$(cd "$ROOT" && "$CUE" export \
        contract/extracted_config.cue \
        contract/invariant_config.cue \
        "$CONFIGS" -e "$expression" --out json 2>&1)"; then
    echo "CONTRACT ABORT: the config contract failed to evaluate ($expression)" >&2
    printf '%s\n' "$OUT" >&2
    exit 2
  fi
  printf '%s' "$OUT" > "$SCRATCH/config-$expression.json"
done

# --- verdict ----------------------------------------------------------------
SCHEMA_COUNT="$(printf '%s' "$SCHEMA_DIAG" | count_json)"
CONFIG_COUNT="$(count_json < "$SCRATCH/config-diagnostics.json")"
DEFERRED_TOTAL="$(count_json < "$SCRATCH/config-deferred.json")"

if [ "$SCHEMA_COUNT" -ne 0 ] || [ "$CONFIG_COUNT" -ne 0 ]; then
  # Record every firing. A passing run writes nothing, so the file is a log of
  # what these checks have actually done — the only non-judgement input to
  # whether a detective invariant deserves its slot. Untracked and unsealed:
  # it changes when something breaks, not on every run.
  mkdir -p "$ROOT/proj"
  { printf '%s' "$SCHEMA_DIAG"; cat "$SCRATCH/config-diagnostics.json"; } \
    | python3 -c '
import json, sys, datetime
stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
for blob in sys.stdin.read().split("}{"):
    text = blob if blob.startswith("{") else "{" + blob
    text = text if text.endswith("}") else text + "}"
    try: rows = json.loads(text)
    except ValueError: continue
    for subject in rows:
        print(json.dumps({"at": stamp, "invariant": subject.split()[0]}))
' >> "$ROOT/proj/gate-firings.jsonl" 2>/dev/null || true

  echo "CONTRACT FAILED — $((SCHEMA_COUNT + CONFIG_COUNT)) diagnostic(s)" >&2
  printf '%s' "$SCHEMA_DIAG" | print_rows "  " >&2
  print_rows "  " < "$SCRATCH/config-diagnostics.json" >&2
  FAIL=1
fi

# Deferred findings are printed on every run, pass or fail. A deferred finding
# nobody prints is a waiver with extra steps.
if [ "$DEFERRED_TOTAL" -ne 0 ]; then
  echo "CONTRACT DEFERRED — $DEFERRED_TOTAL finding(s) that cannot bite in the current posture:"
  print_rows "  " < "$SCRATCH/config-deferred.json"
fi

[ "$FAIL" -eq 0 ] || exit 1

PAIRS="$(cd "$ROOT" && "$CUE" export contract/extracted.cue contract/declaration_schema_pairs.cue \
  contract/invariant_schema.cue contract/invariant_lanes.cue "$FACTS" -e 'len(pairs)' 2>/dev/null || echo '?')"
FACT_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["python"]))' "$FACTS")"
CONFIG_FILES="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["configs"]))' "$CONFIGS")"
echo "CONTRACT CLEAN — ${LIVE}/${BUDGET} invariants, ${PAIRS} declared pairs, ${FACT_COUNT} extracted field sets, ${CONFIG_FILES} configs unified, 0 diagnostics"
