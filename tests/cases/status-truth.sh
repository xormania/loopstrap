source "$TROOT/cases/lib.inc"
# The status surface consumes the breaker's canonical accounting instead of
# maintaining a second, divergent parser or printing unconditional health.
SW="$FIXROOT/status"; SR="$SW/artifacts/reports/c1"; SC="$SW/artifacts/campaigns/c1"
mkdir -p "$SW/ops" "$SW/artifacts/instance/tools" "$SR" "$SC" "$SW/repos/demo/plan"
cp "$FAMILY/ops/loop-status.sh" "$SW/ops/loop-status.sh"
cp "$FAMILY/artifacts/instance/tools/token-breaker.py" "$SW/artifacts/instance/tools/token-breaker.py"
printf '[demo]\nrepo="example/demo"\nint_branch="run/1/c1/int"\n' > "$SW/artifacts/members.toml"
printf 'max_loop_tokens = 1000\nmax_budget_usd = 5\nint_branch = "run/1/c1/int"\n' > "$SC/campaign.toml"
cat > "$SR/loop-test.jsonl" <<'J'
{"type":"assistant","message":{"id":"dup","usage":{"input_tokens":10,"output_tokens":1}}}
{"type":"assistant","message":{"id":"dup","usage":{"input_tokens":20,"output_tokens":2}}}
{"type":"result","total_cost_usd":0.75,"permission_denials":[{"tool":"Edit"},{"tool":"Bash"}]}
J
printf '# halted\n' > "$SW/repos/demo/plan/HALTED.md"
BEFORE="$(find "$SW" -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"
OUT="$(bash "$SW/ops/loop-status.sh" c1 demo 2>/dev/null)"
AFTER="$(find "$SW" -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"
assert_contains "status: processed tokens use snapshot-deduplicated accounting" "$OUT" "processed : 22 / 1000"
assert_contains "status: turns and denials come from canonical summary" "$OUT" "turns≈1  ·  denials 2"
assert_contains "status: HALTED guidance names the real owner ARM action" "$OUT" "owner ARM required"
assert_eq "status: read-only run leaves fixture bytes unchanged" "$AFTER" "$BEFORE"

