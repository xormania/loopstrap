#!/usr/bin/env bash
# Deterministic machinery suite. The harness owns counters, event sequence, and
# summary; cases receive assertion functions but no exported record/counter path.
set -uo pipefail
umask 077
export LC_ALL=C TZ=UTC
TROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAMILY="$(cd "$TROOT/.." && pwd)"
STATE="$(mktemp -d)"
FIXROOT="$(mktemp -d)"
PRIVATE_REC="${LS_ASSERTION_RECORD:-$STATE/assertions.tsv}"
PRIVATE_SUMMARY="${LS_SUITE_SUMMARY:-$STATE/summary.tsv}"
trap 'rm -rf "$STATE" "$FIXROOT"' EXIT
mkdir -p "$FIXROOT/home"
export FIXROOT FAMILY TROOT HOME="$FIXROOT/home"
export PATH="$TROOT/mocks:/usr/bin:/bin"
unset LS_ASSERTION_RECORD LS_SUITE_SUMMARY REC CNT

printf '0\n' > "$STATE/pass"
printf '0\n' > "$STATE/fail"
printf '0\n' > "$STATE/sequence"
: > "$STATE/failed"
: > "$PRIVATE_REC"
: > "$PRIVATE_SUMMARY"
CASE="harness"

increment() {
  local file="$1" value
  value="$(<"$file")"
  printf '%s\n' "$((value+1))" > "$file"
}
emit_event() {
  local status="$1" label="$2" sequence
  increment "$STATE/sequence"
  sequence="$(<"$STATE/sequence")"
  printf '%s\t%s\t%s\t%s\n' "$sequence" "$CASE" "$label" "$status" >> "$PRIVATE_REC"
}
ok() {
  increment "$STATE/pass"
  emit_event PASS "$1"
  printf '  \033[32m✓\033[0m %s\n' "$1"
}
no() {
  increment "$STATE/fail"
  printf '%s\n' "$1" >> "$STATE/failed"
  emit_event FAIL "$1"
  printf '  \033[31m✗\033[0m %s\n     %s\n' "$1" "${2:-}"
}
assert_eq(){ [ "$2" = "$3" ] && ok "$1" || no "$1" "expected [$3] got [$2]"; }
assert_contains(){ grep -qF "$3" <<<"$2" && ok "$1" || no "$1" "missing [$3]"; }
harness_fail() {
  increment "$STATE/fail"
  printf 'HARNESS: %s\n' "$1" >> "$STATE/failed"
  emit_event FAIL "HARNESS: $1"
  printf '  \033[31m✗ HARNESS\033[0m %s\n' "$1"
}

# Prove the canonical helper definitions before cases run. A globally no-op
# helper cannot become the baseline oracle.
CASE="harness-selftest"
ok "selftest-ok" >/dev/null
no "selftest-no" "intentional" >/dev/null
assert_eq "selftest-eq-pass" x x >/dev/null
assert_eq "selftest-eq-fail" x y >/dev/null
if [ "$(<"$STATE/pass")" != 2 ] || [ "$(<"$STATE/fail")" != 2 ] \
   || [ "$(wc -l < "$PRIVATE_REC")" != 4 ]; then
  echo "FATAL: canonical assertion-helper self-test failed" >&2
  exit 2
fi
printf '0\n' > "$STATE/pass"
printf '0\n' > "$STATE/fail"
printf '0\n' > "$STATE/sequence"
: > "$STATE/failed"
: > "$PRIVATE_REC"
readonly -f increment emit_event ok no assert_eq assert_contains harness_fail

echo "════ Loopstrap machinery test suite ════"
echo "mocks: codex=$(command -v codex) claude=$(command -v claude) gh=$(command -v gh) serena=$(command -v serena)"
CASES=0
for case_file in "$TROOT"/cases/${1:-[a-z]*}.sh; do
  [ -f "$case_file" ] || continue
  CASES=$((CASES+1))
  CASE="$(basename "$case_file" .sh)"
  echo
  echo "── $CASE ──"
  [ -r "$case_file" ] || { harness_fail "case $CASE is unreadable"; continue; }
  pass_before="$(<"$STATE/pass")"
  fail_before="$(<"$STATE/fail")"
  error_file="$STATE/stderr.$CASE"
  source_rc_file="$STATE/source-rc.$CASE"
  (
    set +e
    # shellcheck disable=SC1090
    source "$case_file" 2>"$error_file"
    source_rc=$?
    printf '%s\n' "$source_rc" > "$source_rc_file"
    [ "$source_rc" -eq 0 ] && : > "$STATE/complete.$CASE"
  )
  case_rc=$?
  source_rc="$(cat "$source_rc_file" 2>/dev/null || echo 255)"
  [ "$case_rc" -eq 0 ] || harness_fail "case $CASE terminated abnormally (rc=$case_rc)"
  [ "$source_rc" -eq 0 ] || harness_fail "case $CASE source returned nonzero (rc=$source_rc)"
  [ -f "$STATE/complete.$CASE" ] || harness_fail "case $CASE did not reach the end of its file"
  if grep -q 'readonly function' "$error_file" 2>/dev/null; then
    harness_fail "case $CASE attempted to shadow an assertion helper"
  elif [ -s "$error_file" ]; then
    sed 's/^/  case stderr: /' "$error_file" >&2
  fi
  pass_after="$(<"$STATE/pass")"
  fail_after="$(<"$STATE/fail")"
  [ $((pass_after-pass_before + fail_after-fail_before)) -gt 0 ] \
    || harness_fail "case $CASE produced ZERO assertions"
done
CASE="harness"
[ "$CASES" -gt 0 ] || harness_fail "no case matched selector '${1:-[a-z]*}'"

PASS="$(<"$STATE/pass")"
FAIL="$(<"$STATE/fail")"
ASSERTIONS="$(<"$STATE/sequence")"
RECORD_ROWS="$(wc -l < "$PRIVATE_REC")"
if [ "$ASSERTIONS" -ne "$RECORD_ROWS" ]; then
  harness_fail "protected assertion count $ASSERTIONS != record rows $RECORD_ROWS"
  PASS="$(<"$STATE/pass")"; FAIL="$(<"$STATE/fail")"; ASSERTIONS="$(<"$STATE/sequence")"
fi
printf 'cases\t%s\nassertions\t%s\npass\t%s\nfail\t%s\n' \
  "$CASES" "$ASSERTIONS" "$PASS" "$FAIL" > "$PRIVATE_SUMMARY"
echo
echo "════ $PASS passed · $FAIL failed · $ASSERTIONS recorded assertions ════"
if [ "$FAIL" -eq 0 ]; then
  echo "SUITE GREEN — machinery verified under the declared fixtures."
  exit 0
fi
echo "RED:"
sed 's/^/  - /' "$STATE/failed"
exit 1
