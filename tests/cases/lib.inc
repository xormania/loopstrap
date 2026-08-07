# sourced by each case — case-local helpers ONLY.
# ok/no/assert_eq/assert_contains live in run-tests.sh and are deliberately NOT
# redefined here (2026-07-23): the harness hashes those four definitions across
# every case, so a case that shadows one is caught. A duplicate definition here
# would make that check unable to tell shadowing from the normal pattern.
BRK(){ python3 "$FAMILY/artifacts/instance/tools/token-breaker.py" "$@"; }
