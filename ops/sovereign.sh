#!/usr/bin/env bash
# ops/sovereign.sh — xor's owner-control surface. Producer paths are identical
# to the launcher's and breaker's consumer path: reports/<cid>/override.env.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OR="$ROOT/artifacts/reports"
BANNER="$ROOT/.claude/SOVEREIGN-MODE"
T(){ date -Iseconds; }
fail(){ echo "REFUSE  $*" >&2; exit 1; }
log(){ mkdir -p "$OR"; printf '%s SOVEREIGN %s\n' "$(T)" "$*" >> "$OR/owner-records.md"; }
override_path(){ printf '%s/%s/override.env' "$OR" "$1"; }

append_override() {
  local cid="$1" row="$2" path
  path="$(override_path "$cid")"
  mkdir -p "$(dirname "$path")" || return 1
  (
    flock -x 9
    printf '%s\n' "$row" >&9
  ) 9>>"$path" || return 1
  chown "$(id -u)":"$(id -g)" "$path" 2>/dev/null || true
}

guard_files() {
  shopt -s nullglob
  local files=(
    "$ROOT"/repos/*/.claude/settings.json
    "$ROOT"/.worktrees/*/.claude/settings.json
  )
  shopt -u nullglob
  local file
  for file in "${files[@]}"; do
    printf '%s\n' "$file"
  done
}

walls_off() {
  [ ! -f "$BANNER" ] || { echo "already OFF since $(cat "$BANNER")"; return 0; }
  mapfile -t guards < <(guard_files)
  [ "${#guards[@]}" -gt 0 ] || fail "no member-planted guard files found"
  for settings in "${guards[@]}"; do
    [ ! -e "$settings.sovereign-bak" ] || fail "stale guard backup exists: $settings.sovereign-bak"
    python3 - "$settings" <<'PY' >/dev/null || fail "invalid guard JSON: $settings"
import json, sys
data=json.load(open(sys.argv[1], encoding="utf-8"))
if not isinstance(data, dict) or not isinstance(data.get("permissions"), dict):
    raise SystemExit(1)
PY
  done
  for settings in "${guards[@]}"; do
    cp -p -- "$settings" "$settings.sovereign-bak" || fail "backup failed: $settings"
  done
  changed=()
  for settings in "${guards[@]}"; do
    if python3 - "$settings" <<'PY'
import json, os, sys, tempfile
path=sys.argv[1]
with open(path, encoding="utf-8") as source:
    data=json.load(source)
data["permissions"]["deny"]=[]
data["_sovereign"]="walls OFF by owner break-glass — restore with ops/sovereign.sh walls on"
fd, temp=tempfile.mkstemp(prefix=".sovereign.", dir=os.path.dirname(path))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(data, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temp, path)
finally:
    if os.path.exists(temp): os.unlink(temp)
PY
    then
      changed+=("$settings")
    else
      for restore in "${guards[@]}"; do
        [ -f "$restore.sovereign-bak" ] && cp -p -- "$restore.sovereign-bak" "$restore"
        rm -f -- "$restore.sovereign-bak"
      done
      fail "guard mutation failed; every changed guard was rolled back"
    fi
  done
  mkdir -p "$(dirname "$BANNER")"
  date -Iseconds > "$BANNER" || fail "could not write sovereign banner"
  log "WALLS OFF (member-planted, ${#changed[@]} guard file(s))"
  echo "⚠ walls OFF — ${#changed[@]} member session guard(s) emptied. Restore: ops/sovereign.sh walls on"
}

walls_on() {
  shopt -s nullglob
  local backups=(
    "$ROOT"/repos/*/.claude/settings.json.sovereign-bak
    "$ROOT"/.worktrees/*/.claude/settings.json.sovereign-bak
  )
  shopt -u nullglob
  [ "${#backups[@]}" -gt 0 ] || {
    [ ! -f "$BANNER" ] && { echo "walls already on"; return 0; }
    fail "sovereign banner exists but no guard backups exist"
  }
  for backup in "${backups[@]}"; do
    target="${backup%.sovereign-bak}"
    cp -p -- "$backup" "$target" || fail "restore failed: $target"
  done
  for backup in "${backups[@]}"; do rm -f -- "$backup" || fail "cannot consume backup: $backup"; done
  rm -f -- "$BANNER" || fail "cannot remove sovereign banner"
  log "WALLS ON (${#backups[@]} guard(s) restored byte-exact)"
  echo "walls restored ✓ (${#backups[@]} member guard(s))"
}

case "${1:-status}" in
status)
  echo "════ sovereign status · $(T) ════"
  [ -f "$BANNER" ] && echo "  walls   : ⚠ OFF since $(cat "$BANNER")" || echo "  walls   : ON"
  shopt -s nullglob
  for lock in "$OR"/*/.launch.lock "$ROOT"/.launch-*.lock; do
    pids="$(fuser "$lock" 2>/dev/null | tr -s ' ' || true)"
    [ -n "$pids" ] && echo "  running : $lock → pids$pids"
  done
  for paused in "$OR"/*/PAUSED; do
    echo "  paused  : ⏸ $(basename "$(dirname "$paused")") since $(cat "$paused")"
  done
  shopt -u nullglob
  pgrep -af 'token-breaker' 2>/dev/null | sed 's/^/  breaker : /' || true
  ;;
stop)
  CID="${2:?stop <cid> \"reason\"}"; RSN="${3:-owner override}"
  echo "This hard-stops only the live breaker/runner bound to campaign $CID."
  read -rp "Type the campaign id to confirm: " confirmed
  [ "$confirmed" = "$CID" ] || fail "confirmation did not match"
  killed=0
  while IFS= read -r breaker_pid; do
    [ -r "/proc/$breaker_pid/cmdline" ] || continue
    mapfile -d '' -t argv < "/proc/$breaker_pid/cmdline"
    [ "${argv[8]:-}" = "$CID" ] || continue
    runner_pid="${argv[4]:-}"
    breaker_path="${argv[5]:-}"
    [ -n "$runner_pid" ] && kill "$runner_pid" 2>/dev/null || true
    kill "$breaker_pid" 2>/dev/null || true
    if [ -n "$breaker_path" ]; then
      mkdir -p "$(dirname "$breaker_path")"
      printf '# HALTED — OWNER-OVERRIDE\nwhen: %s\nwhy: %s\nby: sovereign stop\n' \
        "$(T)" "$RSN" > "$breaker_path"
    fi
    killed=$((killed+1))
  done < <(pgrep -f 'token-breaker.py' 2>/dev/null || true)
  append_override "$CID" "OWNER_HALT=1" || fail "could not write owner halt override"
  log "STOP cid=$CID reason=\"$RSN\" matched_breakers=$killed"
  echo "STOP issued for $CID — matched breaker/runner pairs: $killed"
  ;;
walls)
  case "${2:?walls off|on}" in
    off) walls_off ;;
    on)  walls_on ;;
    *) fail "usage: sovereign.sh walls off|on" ;;
  esac
  ;;
panpan)
  CID="${2:?panpan <cid> <key> <value>}"; KEY="${3:?key}"; VAL="${4:?value}"
  case "$KEY" in
    tokens)  row="OWNER_MAX_LOOP_TOKENS=$VAL" ;;
    usd)     row="OWNER_MAX_BUDGET_USD=$VAL" ;;
    stall_s) row="OWNER_STALL_S=$VAL" ;;
    deny_n)  row="OWNER_DENY_N=$VAL" ;;
    cadence) row="OWNER_POLL_S=$VAL" ;;
    *) fail "unknown key $KEY (tokens|usd|stall_s|deny_n|cadence)" ;;
  esac
  append_override "$CID" "$row" || fail "override write failed"
  log "PANPAN cid=$CID $KEY=$VAL"
  echo "📻 PAN-PAN · $CID · $KEY → $VAL — breaker adopts at its next poll."
  ;;
mayday)
  CID="${2:?mayday <cid> [reason]}"; RSN="${3:-MAYDAY: pilot taking positive control}"
  echo "🚨 MAY DAY — member guards will be disabled, then the selected campaign action applied."
  read -rp "Confirm MAY DAY by typing the campaign id: " confirmed
  [ "$confirmed" = "$CID" ] || fail "confirmation did not match"
  walls_off
  read -rp "  Conductor action — [p]ause / [h]alt / [w]alls-only: " action
  case "${action:-p}" in
    h|H)
      append_override "$CID" "OWNER_HALT_REASON=$RSN" || fail "reason write failed"
      append_override "$CID" "OWNER_HALT=1" || fail "halt write failed"
      outcome="halt";;
    w|W)
      outcome="walls-only";;
    p|P|"")
      append_override "$CID" "OWNER_PAUSE=1" || fail "pause write failed"
      mkdir -p "$OR/$CID"; date -Iseconds > "$OR/$CID/PAUSED" || fail "pause marker write failed"
      outcome="pause";;
    *)
      fail "unknown MAYDAY action: $action";;
  esac
  log "MAYDAY cid=$CID reason=\"$RSN\" action=$outcome"
  echo "🚨 MAY DAY DECLARED · $CID · action=$outcome. Stand down guards: sovereign.sh walls on"
  ;;
pause)
  CID="${2:?pause <cid> [reason]}"; RSN="${3:-owner pause}"
  append_override "$CID" "OWNER_PAUSE=1" || fail "pause write failed"
  mkdir -p "$OR/$CID"; date -Iseconds > "$OR/$CID/PAUSED" || fail "pause marker write failed"
  log "PAUSE cid=$CID reason=\"$RSN\""
  echo "⏸ PAUSE · $CID — breaker freezes the bound runner tree at next poll."
  ;;
resume)
  CID="${2:?resume <cid>}"
  append_override "$CID" "OWNER_PAUSE=0" || fail "resume write failed"
  rm -f "$OR/$CID/PAUSED" || fail "pause marker removal failed"
  log "RESUME cid=$CID"
  echo "▶ RESUME · $CID — breaker thaws the bound runner tree at next poll."
  ;;
force-launch)
  fail "P8 is unruled — force-launch is not wired"
  ;;
*)
  fail "usage: sovereign.sh status|stop|walls|panpan|mayday|pause|resume|force-launch"
  ;;
esac
