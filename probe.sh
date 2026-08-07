#!/usr/bin/env bash
# probe.sh — comprehension probe: does the loop harness read the doctrine correctly?
# Model inference is NOT deterministic; the GRADING is: fixed questions, closed enums,
# exact-match against the key. A stable FAIL means either the doctrine text is ambiguous
# (design intake — fix the doc) or the harness misreads it (fix the kickoff). Both are
# findings worth having. Rerun a FAIL once to separate flake from stable.
# Read-only: codex runs sandboxed read-only from the root; nothing is written by the model.
set -u
Q=artifacts/instance/tools/probe-questions.md
K=artifacts/instance/tools/probe-key.md
[ -f "$Q" ] && [ -f "$K" ] || { echo "probe files missing"; exit 2; }
command -v codex >/dev/null || { echo "codex CLI not found"; exit 2; }
OUT=$(mktemp)
codex exec --sandbox read-only "$(cat "$Q")" > "$OUT" 2>/dev/null
PASS=0; FAIL=0
while read -r LINE; do
  N=${LINE%%:*}
  GOT=$(grep -Eo "^${N}: *[A-Z-]+" "$OUT" | tail -1 | tr -d ' ')
  WANT=$(echo "$LINE" | tr -d ' ')
  if [ "$GOT" = "$WANT" ]; then echo "PASS  $LINE"; PASS=$((PASS+1))
  else echo "FAIL  want[$LINE] got[${GOT:-<no answer>}]"; FAIL=$((FAIL+1)); fi
done < <(grep '^PQ' "$K")
echo "== probe: PASS=$PASS FAIL=$FAIL  (transcript: $OUT) =="
[ "$FAIL" -eq 0 ]
