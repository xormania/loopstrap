source "$TROOT/cases/lib.inc"
# enforces: spend wires + OWNER_HALT (L22) · uid forgery-proofing (L23/L40 — the wallet)
# tally on a known stream
S="$FIXROOT/known-stream.jsonl"
cat > "$S" << 'J'
{"type":"assistant","message":{"id":"a1","usage":{"input_tokens":1000000,"output_tokens":5000}}}
{"type":"result","total_cost_usd":1.23,"permission_denials":[]}
J
assert_eq "tally: processed tokens" "$(BRK --tally "$S")" "1005000"
assert_eq "tally: output tokens"    "$(BRK --tally-out "$S")" "5000"

# Snapshot updates for one assistant message id replace earlier usage. The same
# deduplication rule must feed status summaries, including the turn count.
SD="$FIXROOT/duplicate-stream.jsonl"
cat > "$SD" <<'J'
{"type":"assistant","message":{"id":"dup","usage":{"input_tokens":10,"output_tokens":1}}}
{"type":"assistant","message":{"id":"dup","usage":{"input_tokens":20,"output_tokens":2}}}
{"type":"result","total_cost_usd":0.75,"permission_denials":[{"tool":"Edit"},{"tool":"Bash"}]}
J
SUMMARY="$(BRK --summary "$SD")"
assert_eq "summary: duplicate message snapshots count once" \
  "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["processed_tokens"])' "$SUMMARY")" "22"
assert_eq "summary: turns count unique assistant message ids" \
  "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["turns"])' "$SUMMARY")" "1"
assert_eq "summary: permission denials are reported" \
  "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["denials"])' "$SUMMARY")" "2"

# Production path contract: sovereign producer and breaker consumer converge on
# reports/<cid>/override.env, never reports/<cid>/<cid>/override.env.
OWNER_PATH="$FIXROOT/reports/prodcid/owner-records.md"
assert_eq "override path: breaker consumes sovereign's canonical file" \
  "$(BRK --override-path "$OWNER_PATH" prodcid)" "$FIXROOT/reports/prodcid/override.env"
# tokens wire trips when processed > cap
D="$FIXROOT/wd"; rm -rf "$D"; mkdir -p "$D"; touch "$D/HALT.md"; rm -f "$D/HALT.md"
( sleep 300 ) & PID=$!
BRK "$S" 500000 "$PID" "$D/HALT.md" "$D/owner.md" testm testc campaign 0 out >/dev/null 2>&1 &
BP=$!; sleep 1; wait $BP 2>/dev/null; RC=$?
kill $PID 2>/dev/null || true
assert_eq "tokens wire: trips (rc=3) when 1.005M > cap 500k" "$RC" "3"
[ -f "$D/HALT.md" ] && ok "tokens wire: wrote sticky HALT" || no "tokens wire: no HALT written"
grep -q "tokens" "$D/HALT.md" 2>/dev/null && ok "HALT names the tripped wire" || no "HALT missing wire name"
# forgery-proof (L23 lane): a SAME-uid override is IGNORED — pilot proof is the uid delta
D2="$FIXROOT/wd2"; rm -rf "$D2"; mkdir -p "$D2/testc"
echo "OWNER_HALT=1" > "$D2/testc/override.env"
( sleep 2 ) & P2=$!
BRK "$S" 999999999 "$P2" "$D2/HALT.md" "$D2/owner.md" testm testc campaign 0 out >/dev/null 2>&1
RC2=$?
[ -f "$D2/HALT.md" ] && no "forgery-proof: same-uid override wrongly honored" || ok "forgery-proof: same-uid override ignored (no HALT)"
assert_eq "forgery-proof: breaker exits clean, not tripped" "$RC2" "0"
# tokens-out wire (D57 — xor's expensive currency): OUTPUT cap trips independently
D3="$FIXROOT/wd3"; rm -rf "$D3"; mkdir -p "$D3"
( sleep 300 ) & P3=$!
BRK "$S" 999999999 "$P3" "$D3/HALT.md" "$D3/owner.md" testm testc campaign 4000 out >/dev/null 2>&1 &
B3=$!; sleep 1; wait $B3 2>/dev/null; RC3=$?
kill $P3 2>/dev/null || true
assert_eq "tokens-out wire: trips (rc=3) when 5000 output > cap 4000" "$RC3" "3"
grep -q "tokens-out" "$D3/HALT.md" 2>/dev/null && ok "tokens-out HALT names the tripped wire" || no "tokens-out: HALT missing or unnamed"

# The campaign's USD cap is a live breaker input, not dashboard-only metadata.
D4="$FIXROOT/wd4"; rm -rf "$D4"; mkdir -p "$D4"
( sleep 300 ) & P4=$!
POLL_S=0.05 BRK "$S" 999999999 "$P4" "$D4/HALT.md" "$D4/owner.md" testm testc campaign 0 out 1.0 >/dev/null 2>&1 &
B4=$!; wait "$B4" 2>/dev/null; RC4=$?
kill "$P4" 2>/dev/null || true
assert_eq "budget wire: trips (rc=3) when stream cost exceeds USD cap" "$RC4" "3"
grep -q "wire tripped  : \*\*budget\*\*" "$D4/HALT.md" 2>/dev/null \
  && ok "budget HALT names the tripped wire" || no "budget HALT missing or unnamed"

# Vendor doubles are contracts: unsupported invocations must fail, otherwise
# misspelled production CLI calls become false greens.
codex --definitely-unsupported >/dev/null 2>&1; RC=$?
[ "$RC" -ne 0 ] && ok "strict mock: codex rejects unsupported invocation" || no "codex mock licensed unknown arguments"
claude --definitely-unsupported >/dev/null 2>&1; RC=$?
[ "$RC" -ne 0 ] && ok "strict mock: claude rejects unsupported invocation" || no "claude mock licensed unknown arguments"
gh definitely-unsupported >/dev/null 2>&1; RC=$?
[ "$RC" -ne 0 ] && ok "strict mock: gh rejects unsupported invocation" || no "gh mock licensed unknown command"
serena definitely-unsupported >/dev/null 2>&1; RC=$?
[ "$RC" -ne 0 ] && ok "strict mock: serena rejects unsupported invocation" || no "serena mock licensed unknown command"
