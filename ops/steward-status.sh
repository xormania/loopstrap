#!/usr/bin/env bash
# steward-status.sh — one screen of current state (L36). Read-only intent; the only
# writes are audit's byte-noop regen comparison. The steward's first command of any session.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
echo "══════ LOOPSTRAP STATUS · $(date -u +%FT%TZ) · $ROOT ══════"
sha256sum -c loopstrap.manifest --quiet 2>/dev/null && echo "tree     : ✓ matches loopstrap.manifest ($(wc -l < loopstrap.manifest) files)" || echo "tree     : ✗ DRIFT vs manifest — land a courier or investigate"
echo "configs  : $(./install-configs.sh --check 2>/dev/null | tail -1)"
echo "wall     : $(./wall.sh --sweep 2>/dev/null | tail -2 | head -1)"
echo "audit    : $(bash artifacts/instance/tools/audit-consistency.sh 2>/dev/null | tail -3 | head -1 | sed 's/^ *//')"
echo "── members (registry) ──"
for m in $(grep -oP '^\[\K[^]]+' artifacts/members.toml 2>/dev/null); do
  st="staging:$([ -d "artifacts/agent-configs/$m" ] && echo ✓ || echo ✗)"
  if [ -f "artifacts/contracts/$m/docs-manifest.toml" ]; then lic="docs:LICENSED"
  else lic="docs:spec-less(read-only)"; fi
  if [ -d "repos/$m/.git" ]; then rp="repo:✓ $(git -C "repos/$m" rev-parse --short origin/$(grep -A3 "^\[$m\]" artifacts/members.toml | grep -oP 'int_branch *= *"\K[^"]+') 2>/dev/null || echo '?')"
  else rp="repo:absent"; fi
  echo "  $m — $st · $lic · $rp"
done
echo "── runs ──"
B="$(ls repos/*/plan/HALTED.md 2>/dev/null | tr '\n' ' ')"; echo "  breakers : ${B:-none}"
P="$(ls artifacts/reports/*/PAUSED 2>/dev/null | tr '\n' ' ')"; echo "  paused   : ${P:-none}"
L="$(ls .git/loopstrap-loop.lock repos/*/.git/loopstrap-loop.lock 2>/dev/null | tr '\n' ' ')"; echo "  locks    : ${L:-none}"
echo "  board    : artifacts/campaigns/board.md ($(date -u -r artifacts/campaigns/board.md +%F 2>/dev/null || echo '?'))"
echo "  pending  : instance/first-prep.md (the deferred-build queue)"
