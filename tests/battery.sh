#!/usr/bin/env bash
# Full repercussion detector. Each required leg leaves a harness-owned receipt;
# the battery cannot print green if a dispatch line disappears.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
STATE="$(mktemp -d)"
trap 'rm -rf "$STATE"' EXIT
REC="$STATE/assertions.tsv"
SUMMARY="$STATE/suite-summary.tsv"
FAIL=0
REQUIRED=(syntax suite acceptance active integration telemetry readiness certification wall audit register-map)

run_leg() {
  local name="$1"; shift
  printf 'started\n' > "$STATE/$name.receipt"
  "$@"
  local rc=$?
  printf '%s\n' "$rc" > "$STATE/$name.receipt"
  [ "$rc" -eq 0 ] || FAIL=1
  return 0
}

run_leg syntax bash tests/check-syntax.sh
run_leg suite env LS_ASSERTION_RECORD="$REC" LS_SUITE_SUMMARY="$SUMMARY" bash tests/run-tests.sh
run_leg acceptance bash tests/run-acceptance.sh
run_leg active bash tests/run-active.sh
run_leg integration bash tests/run-integration.sh
run_leg telemetry bash tests/run-telemetry.sh
run_leg readiness bash -c \
  'PYTHONDONTWRITEBYTECODE=1 python3 tests/readiness/verify_freeze.py && PYTHONDONTWRITEBYTECODE=1 python3 tests/readiness/run.py'
run_leg certification bash -c \
  'PYTHONDONTWRITEBYTECODE=1 python3 tests/certification/verify_freeze.py && PYTHONDONTWRITEBYTECODE=1 python3 tests/certification/run.py'
run_leg wall ./wall.sh --sweep
run_leg audit bash artifacts/instance/tools/audit-consistency.sh
run_leg register-map bash tests/check-register-map.sh "$REC" "$SUMMARY"

for leg in "${REQUIRED[@]}"; do
  if [ ! -f "$STATE/$leg.receipt" ]; then
    echo "BATTERY WIRING FAILURE — required leg '$leg' did not run" >&2
    FAIL=1
  elif [ "$(<"$STATE/$leg.receipt")" != 0 ]; then
    FAIL=1
  fi
done
receipt_count="$(find "$STATE" -maxdepth 1 -name '*.receipt' -type f | wc -l)"
if [ "$receipt_count" -ne "${#REQUIRED[@]}" ]; then
  echo "BATTERY WIRING FAILURE — expected ${#REQUIRED[@]} receipts, found $receipt_count" >&2
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "════ BATTERY GREEN — syntax · suite · acceptance · active · integration · telemetry · readiness · certification · wall · audit · register-map (all receipts present) ════"
  exit 0
fi
echo "════ BATTERY RED — failed or missing leg above ════"
exit 1
