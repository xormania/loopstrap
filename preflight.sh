#!/usr/bin/env bash
# preflight.sh — run before every counted pass (process.md §11). Verifies the
# machine honors containment and the run's inputs are what the plan pinned.
# Cheap: a red preflight costs seconds, not a pass. Read-only; mutates nothing.
#   ./preflight.sh <member> [campaign-id]      (default CID: <member>-c2)
#   exit 0 = clear to run · nonzero = a wall; the message names it
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
m="${1:-}"; [ -n "$m" ] || { echo "usage: ./preflight.sh <member> [campaign-id]"; exit 2; }
CID="${2:-${m}-c2}"
REPO="$ROOT/repos/$m"
CAMP="$ROOT/artifacts/campaigns/$CID"
MAN="$ROOT/artifacts/instance/assets/environment-manifest.md"
F=0
no(){ echo "WALL  $*"; F=$((F+1)); }
ok(){ echo "ok    $*"; }

# ── cited-input hash verification (§7, the plan-upfront anti-drift spine) ──
# The backlog header pins every cited input by sha256; verify each still matches.
BL="$CAMP/backlog.md"
if [ -f "$BL" ]; then
  # lines of the form:  <sha256>  <relpath>   (a pinned-inputs block in the header)
  pins="$(grep -oE '^[0-9a-f]{64}  [^ ].*$' "$BL" 2>/dev/null || true)"
  if [ -n "$pins" ]; then
    while read -r h rel; do
      f="$ROOT/$rel"; [ -f "$f" ] || { no "cited input missing: $rel"; continue; }
      cur="$(sha256sum "$f" | cut -d' ' -f1)"
      [ "$cur" = "$h" ] && ok "cited-input hash: $rel" || no "cited-input HASH MISMATCH: $rel (pinned $h, now $cur)"
    done <<< "$pins"
  else
    echo "note  no pinned-input block in $CID/backlog.md yet — hash gate dormant (fill at prep)"
  fi
else
  no "no backlog at $CID — nothing to verify"
fi

# ── wall R1 (D68/D69): base footing — live main must equal the declared base ──
BSHA="$(grep -E '^base_sha' "$CAMP/campaign.toml" 2>/dev/null | sed 's/.*"\([0-9a-fA-Z-]*\)".*/\1/' || true)"
BREF="$(grep -E '^base_ref' "$CAMP/campaign.toml" 2>/dev/null | sed 's/.*"\([^"]*\)".*/\1/' || true)"; BREF="${BREF:-main}"
if [ -n "$BSHA" ] && [ "$BSHA" != "SET-BY-PREP" ] && [ "$BSHA" != "AUTO" ]; then
  LIVE="$(git -C "$REPO" ls-remote origin "refs/heads/$BREF" 2>/dev/null | cut -f1 || true)"
  if [ "$LIVE" = "$BSHA" ]; then ok "base footing: origin/$BREF == declared ${BSHA:0:12}"
  else no "BASE MISMATCH: origin/$BREF=${LIVE:-<none>} ≠ declared $BSHA — ensure the base branch (setup step 3) (R1: never mint a footing)"; fi
else
  echo "note  base_sha unset/sentinel — prep stamps it; loop HALTS on any silent-basis judgment (R1)"
fi

# ── wall 1: codex repo trust pre-recorded (silent-config-drop if absent) ──
TRUST="$HOME/.codex/config.toml"
if [ -f "$TRUST" ] && grep -q "projects" "$TRUST" 2>/dev/null && grep -qF "$REPO" "$TRUST" 2>/dev/null; then
  ok "codex trust recorded for $m"
else
  no "codex trust NOT recorded for $REPO — exec silently drops project config (seed [projects.\"$REPO\"] in ~/.codex/config.toml)"
fi

# ── wall 2: single-live-session (rule 8) ──
LOCK="$REPO/.git/loopstrap-loop.lock"
if [ -f "$LOCK" ] && command -v flock >/dev/null && ! flock -n "$LOCK" true 2>/dev/null; then
  no "another loop session holds $m (rule 8)"
else
  ok "no competing session on $m"
fi

# ── wall 3: serena health (the planted MCP line assumes a working CLI) ──
if command -v serena >/dev/null 2>&1; then
  ok "serena CLI present"
else
  no "serena CLI not found — the planted [mcp_servers.serena] line will fail"
fi

# ── wall 4: model/effort/summary asserted against the manifest (FR-010) ──
if [ -f "$MAN" ]; then
  for key in model model_reasoning_effort model_reasoning_summary; do
    want="$(grep -oE "$key[[:space:]]*[:=][[:space:]]*[\"']?[A-Za-z0-9._-]+" "$MAN" 2>/dev/null | head -1 | sed -E "s/.*[:=][[:space:]]*[\"']?//")"
    got="$(grep -oE "$key[[:space:]]*=[[:space:]]*[\"']?[A-Za-z0-9._-]+" "$HOME/.codex/config.toml" 2>/dev/null | head -1 | sed -E "s/.*=[[:space:]]*[\"']?//")"
    if [ -z "$want" ]; then echo "note  manifest pins no $key"; continue; fi
    [ "$got" = "$want" ] && ok "$key = $want (matches manifest)" || no "$key: manifest pins '$want', codex config has '${got:-<unset>}'"
  done
else
  no "environment manifest absent ($MAN) — provision.sh has not run / manifest unauthored"
fi

# ── env walls: gh auth + push-token present ──
[ -n "${GH_TOKEN:-}" ] && ok "GH_TOKEN in env" || no "GH_TOKEN not in session env"
gh auth status >/dev/null 2>&1 && ok "gh authenticated" || no "gh auth status failed"

# ── staging drift ──
if "$ROOT/install-configs.sh" --check >/dev/null 2>&1; then ok "staging drift-free"; else no "staging drift — run install-configs.sh"; fi

echo "----"
[ "$F" = "0" ] && echo "PREFLIGHT CLEAR — $m/$CID may run" || echo "PREFLIGHT: $F wall(s) — resolve before a counted pass"
exit "$F"
