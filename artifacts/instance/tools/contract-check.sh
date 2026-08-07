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
        contract/invariant_harness_cli.cue \
        contract/invariant_serena.cue \
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
echo "CONTRACT CLEAN — ${PAIRS} declared pairs, ${FACT_COUNT} extracted field sets, ${CONFIG_FILES} configs unified, 0 diagnostics"
