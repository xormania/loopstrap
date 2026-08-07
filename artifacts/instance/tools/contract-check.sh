#!/usr/bin/env bash
# contract-check.sh — static coherence gate over the development contract.
#
# Extracts field-set facts from both schema languages, joins them against the
# declared pairings in contract/, and prints every diagnostic. Fast, hermetic,
# and deterministic: no clock, no network, no ordering dependence, no sleep.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CUE="$ROOT/tools/cue/v0.17.0/cue"

[ -x "$CUE" ] || { echo "CONTRACT ABORT: pinned CUE binary absent: $CUE" >&2; exit 2; }

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT
FACTS="$SCRATCH/facts.json"

python3 "$ROOT/artifacts/instance/tools/schema-facts.py" --root "$ROOT" --out "$FACTS"

# Evaluating `diagnostics` is the whole gate. A malformed contract is a CUE
# error and exits non-zero here rather than being reported as clean.
if ! DIAGNOSTICS="$(cd "$ROOT" && "$CUE" export \
      contract/extracted.cue \
      contract/declaration_schema_pairs.cue \
      contract/invariant_schema.cue \
      "$FACTS" -e diagnostics --out json 2>&1)"; then
  echo "CONTRACT ABORT: the contract itself failed to evaluate" >&2
  printf '%s\n' "$DIAGNOSTICS" >&2
  exit 2
fi

COUNT="$(printf '%s' "$DIAGNOSTICS" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
if [ "$COUNT" -eq 0 ]; then
  PAIRS="$(cd "$ROOT" && "$CUE" export contract/*.cue "$FACTS" -e 'len(pairs)' 2>/dev/null || echo '?')"
  FACT_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["python"]))' "$FACTS")"
  echo "CONTRACT CLEAN — ${PAIRS} declared pairs, ${FACT_COUNT} extracted Python field sets, 0 diagnostics"
  exit 0
fi

echo "CONTRACT FAILED — ${COUNT} diagnostic(s)" >&2
printf '%s' "$DIAGNOSTICS" | python3 -c '
import json, sys
for subject, reason in sorted(json.load(sys.stdin).items()):
    print(f"  {subject}: {reason}", file=sys.stderr)
'
exit 1
