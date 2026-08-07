source "$TROOT/cases/lib.inc"
# Custody receipts must be immutable, self-contained, and independently
# verifiable. A later sweep may never overwrite a path signed by an earlier one.
CW="$FIXROOT/custody"; CR="$CW/repos/demo/plan"; RR="$CW/artifacts/reports/c1"
mkdir -p "$CR" "$CW/artifacts/reports"
cp "$FAMILY/custody-sweep.sh" "$CW/custody-sweep.sh"
printf 'state-v1\n' > "$CR/backlog.md"
printf '{"trace":1}\n' > "$CR/unit-1.jsonl"
( cd "$CW" && bash custody-sweep.sh demo c1 > "$CW/first.log" 2>&1 ); RC=$?
assert_eq "custody: first sweep exits 0" "$RC" "0"
FIRST="$(find "$RR" -mindepth 1 -maxdepth 1 -type d -name 'plan-sweep-*' | sort | head -1)"
[ -f "$FIRST/state/backlog.md" ] && [ -f "$FIRST/traces/unit-1.jsonl" ] \
  && ok "custody: snapshot contains state and trace bytes" || no "custody: snapshot is not self-contained"
( cd "$FIRST" && sha256sum -c MANIFEST.sha256 --quiet )
assert_eq "custody: first snapshot manifest verifies" "$?" "0"
FIRST_HASH="$(sha256sum "$FIRST/traces/unit-1.jsonl" | cut -d' ' -f1)"

printf '{"trace":2}\n' > "$CR/unit-1.jsonl"
( cd "$CW" && bash custody-sweep.sh demo c1 > "$CW/second.log" 2>&1 ); RC=$?
assert_eq "custody: second sweep exits 0" "$RC" "0"
COUNT="$(find "$RR" -mindepth 1 -maxdepth 1 -type d -name 'plan-sweep-*' | wc -l)"
assert_eq "custody: successive sweeps use distinct snapshot directories" "$COUNT" "2"
[ "$(sha256sum "$FIRST/traces/unit-1.jsonl" | cut -d' ' -f1)" = "$FIRST_HASH" ] \
  && ok "custody: later sweep cannot overwrite first signed trace" || no "custody: first trace changed after second sweep"
( cd "$FIRST" && sha256sum -c MANIFEST.sha256 --quiet )
assert_eq "custody: first manifest still verifies after later sweep" "$?" "0"

