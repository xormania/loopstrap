source "$TROOT/cases/lib.inc"
# enforces: MAYDAY walls = member-planted guards, backup + byte-restore (L42)
SV="$FIXROOT/sovroot"; rm -rf "$SV"; mkdir -p "$SV/ops" "$SV/repos/demo/.claude" "$SV/artifacts/reports/guard" "$SV/artifacts"
printf '[demo]\nrepo = "example/demo"\nint_branch = "dev"\n' > "$SV/artifacts/members.toml"
printf '{"permissions": {"deny": ["Edit(plan/**)"], "allow": []}}\n' > "$SV/repos/demo/.claude/settings.json"
cp "$FAMILY/ops/sovereign.sh" "$SV/ops/sovereign.sh"
ORIG="$(sha256sum "$SV/repos/demo/.claude/settings.json" | cut -d' ' -f1)"
"$SV/ops/sovereign.sh" walls off >/dev/null 2>&1
[ -f "$SV/repos/demo/.claude/settings.json.sovereign-bak" ] && ok "sovereign walls off: backup created beside guard" || no "sovereign walls off: no backup"
python3 -c "import json;d=json.load(open('$SV/repos/demo/.claude/settings.json'));exit(0 if d['permissions']['deny']==[] else 1)" \
  && ok "sovereign walls off: member deny emptied" || no "sovereign walls off: deny not emptied"
"$SV/ops/sovereign.sh" walls on >/dev/null 2>&1
NOW="$(sha256sum "$SV/repos/demo/.claude/settings.json" | cut -d' ' -f1)"
[ "$NOW" = "$ORIG" ] && ok "sovereign walls on: guard restored byte-exact" || no "sovereign walls on: restore differs"
[ ! -f "$SV/repos/demo/.claude/settings.json.sovereign-bak" ] && ok "sovereign walls on: backup consumed" || no "sovereign walls on: backup left behind"

# MAYDAY must call the same member-guard implementation, not superseded root settings.
printf 'guard\nw\n' | "$SV/ops/sovereign.sh" mayday guard "test" > "$SV/mayday.log" 2>&1; RC=$?
assert_eq "sovereign MAYDAY walls-only exits 0" "$RC" "0"
python3 -c "import json;d=json.load(open('$SV/repos/demo/.claude/settings.json'));exit(0 if d['permissions']['deny']==[] else 1)" \
  && ok "sovereign MAYDAY empties the member guard" || no "sovereign MAYDAY targeted the wrong guard"
grep -q 'action=walls-only' "$SV/mayday.log" && ok "sovereign MAYDAY reports the selected action truthfully" || no "sovereign MAYDAY invented a halt"
"$SV/ops/sovereign.sh" walls on >/dev/null 2>&1
NOW="$(sha256sum "$SV/repos/demo/.claude/settings.json" | cut -d' ' -f1)"
[ "$NOW" = "$ORIG" ] && ok "sovereign MAYDAY stand-down restores member guard byte-exact" || no "sovereign MAYDAY guard did not restore"

# A hard stop is campaign-scoped. Run two real breakers and prove only the
# selected breaker/runner pair is terminated.
TB="$FAMILY/artifacts/instance/tools/token-breaker.py"
: > "$SV/guard.stream"; : > "$SV/other.stream"
( sleep 300 ) & R1=$!
( sleep 300 ) & R2=$!
POLL_S=0.05 python3 "$TB" "$SV/guard.stream" 999999999 "$R1" \
  "$SV/repos/demo/plan/guard-HALTED.md" "$SV/artifacts/reports/guard/owner-records.md" demo guard campaign 0 out 999 >/dev/null 2>&1 &
B1=$!
POLL_S=0.05 python3 "$TB" "$SV/other.stream" 999999999 "$R2" \
  "$SV/repos/demo/plan/other-HALTED.md" "$SV/artifacts/reports/other/owner-records.md" demo other campaign 0 out 999 >/dev/null 2>&1 &
B2=$!
sleep 0.2
printf 'guard\n' | "$SV/ops/sovereign.sh" stop guard "scope test" > "$SV/stop.log" 2>&1; STOP_RC=$?
wait "$R1" 2>/dev/null; R1_RC=$?
kill -0 "$R2" 2>/dev/null; R2_ALIVE=$?
kill -0 "$B2" 2>/dev/null; B2_ALIVE=$?
assert_eq "sovereign stop: selected campaign command exits 0" "$STOP_RC" "0"
[ "$R1_RC" -ne 0 ] && [ "$R2_ALIVE" -eq 0 ] && [ "$B2_ALIVE" -eq 0 ] \
  && ok "sovereign stop: kills only the matching campaign pair" || no "sovereign stop crossed campaign scope"
grep -q "matched breaker/runner pairs: 1" "$SV/stop.log" \
  && ok "sovereign stop: reports the matched process count truthfully" || no "sovereign stop count is false"
[ -f "$SV/artifacts/reports/guard/override.env" ] \
  && [ ! -e "$SV/artifacts/reports/guard/guard/override.env" ] \
  && ok "sovereign stop: writes the canonical override path" || no "sovereign stop wrote the disconnected override path"
kill "$R2" "$B2" "$B1" 2>/dev/null || true
wait "$R2" "$B2" "$B1" 2>/dev/null || true

# Invalid JSON must refuse before backup/banner creation and leave bytes alone.
printf '{bad json\n' > "$SV/repos/demo/.claude/settings.json"
BAD="$(sha256sum "$SV/repos/demo/.claude/settings.json" | cut -d' ' -f1)"
"$SV/ops/sovereign.sh" walls off > "$SV/bad.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "invalid guard JSON" "$SV/bad.log" && ok "sovereign malformed guard refuses nonzero" || no "sovereign malformed guard reported success"
[ "$(sha256sum "$SV/repos/demo/.claude/settings.json" | cut -d' ' -f1)" = "$BAD" ] \
  && [ ! -e "$SV/repos/demo/.claude/settings.json.sovereign-bak" ] \
  && [ ! -e "$SV/.claude/SOVEREIGN-MODE" ] \
  && ok "sovereign malformed refusal leaves no backup/banner or byte mutation" || no "sovereign malformed refusal left partial state"
