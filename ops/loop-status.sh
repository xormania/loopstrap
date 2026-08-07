#!/usr/bin/env bash
# ops/loop-status.sh <campaign-id> — one-screen mission-control truth. READ-ONLY.
# Owner seat tool (D76): recomputes wire distances from the live stream + ledger;
# never writes, never signals. Companion: loop-watch.sh (live).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CID="${1:?usage: loop-status.sh <campaign-id> [member]}"; M="${2:-$(grep -oP '^\[\K[^]]+' "$ROOT/artifacts/members.toml" | head -1)}"
RD="$ROOT/artifacts/reports/$CID"; REPO="$ROOT/repos/$M"
CT="$ROOT/artifacts/campaigns/$CID/campaign.toml"
tget(){ grep -E "^$1[[:space:]]*=" "$CT" 2>/dev/null | head -1 | sed 's/.*=[[:space:]]*//; s/[#].*//; s/"//g' | tr -d ' ' || true; }
OUT="$(ls -t "$RD"/loop-*.jsonl 2>/dev/null | head -1 || true)"
echo "════ $(date +%H:%M:%S) · $M / $CID ════"
[ -n "$OUT" ] || { echo "no stream yet — not launched or reports empty"; exit 0; }
AGE=$(( $(date +%s) - $(stat -c %Y "$OUT") ))
SUMMARY="$(python3 "$ROOT/artifacts/instance/tools/token-breaker.py" --summary "$OUT")"
python3 - "$OUT" "$(tget max_loop_tokens)" "$(tget max_budget_usd)" "$AGE" "$SUMMARY" << 'PY'
import json, sys
f, cap, usd_cap, age, raw = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
s=json.loads(raw)
tok=s["processed_tokens"]; out=s["output_tokens"]; den=s["denials"]
err=s["errors"]; turns=s["turns"]; usd=s["cost_usd"]
cap_i=int(cap) if str(cap).isdigit() else 0
pct=f"{100*tok/cap_i:.1f}%" if cap_i else "?"
print(f"stream    : {f.rsplit('/',1)[-1]} · last event {age}s ago" + ("  ⚠ STALL-RANGE" if age>240 else ""))
print(f"processed : {tok:,} / {cap or '?'}  ({pct})")
print(f"output    : {out:,}   ·  turns≈{turns}  ·  denials {den}  ·  errors {err}")
print(f"spend     : ${usd} / ${usd_cap or '?'}")
PY
echo "── unit/pass (plan) ──"
ls -t "$REPO"/plan/unit-*-pass-*.jsonl 2>/dev/null | head -2 | sed "s|.*/|  gen: |" || true
ls "$REPO"/plan/HALTED.md >/dev/null 2>&1 && echo "  ⛔ HALTED.md PRESENT — owner ARM required before relaunch" || echo "  halt: none"
tail -2 "$REPO"/plan/findings.md 2>/dev/null | sed 's/^/  finding: /' || true
echo "── git/PR ──"
INT="$(tget int_branch)"
echo "  int: $(git -C "$REPO" ls-remote origin "refs/heads/$INT" 2>/dev/null | cut -c1-7 || echo '?') · HEAD: $(git -C "$REPO" rev-parse --short HEAD 2>/dev/null)"
command -v gh >/dev/null && ( cd "$REPO" && gh pr list --state open --json number,title,statusCheckRollup \
  --template '{{range .}}  PR#{{.number}} {{.title}}{{"\n"}}{{end}}' ) 2>/dev/null || true
echo "── budgets (ledger) ──"
L="$ROOT/artifacts/reports/project-ledger.md"
[ -f "$L" ] && tail -2 "$L" | sed 's/^/  /' || echo "  no ledger yet"
