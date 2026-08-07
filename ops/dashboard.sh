#!/usr/bin/env bash
# ops/dashboard.sh <campaign-id> [member] — live full-screen monitor (D78).
# READ-ONLY. Pure bash + python3 stdlib — zero deps. Repaints every 10s; the
# git/PR panel is throttled to ~every 30s so it never hammers the remote.
# Single-campaign; structured for a future multi-loop wrapper (P10 lean).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CID="${1:?usage: dashboard.sh <campaign-id> [member]}"; M="${2:-$(grep -oP '^\[\K[^]]+' "$ROOT/artifacts/members.toml" | head -1)}"
RD="$ROOT/artifacts/reports/$CID"; REPO="$ROOT/repos/$M"
CT="$ROOT/artifacts/campaigns/$CID/campaign.toml"; L="$ROOT/artifacts/reports/project-ledger.md"
FB="$ROOT/artifacts/instance/assets/project-budget.toml"
tget(){ grep -E "^$1[[:space:]]*=" "$CT" 2>/dev/null | head -1 | sed 's/.*=[[:space:]]*//;s/[#].*//;s/"//g' | tr -d ' ' || true; }
trap 'tput cnorm 2>/dev/null; clear; echo "dashboard closed — loop unaffected."; exit 0' INT TERM
tput civis 2>/dev/null || true
GIT_CACHE=""; GIT_TS=0
while true; do
  OUT="$(ls -t "$RD"/loop-*.jsonl 2>/dev/null | head -1 || true)"
  NOW=$(date +%s)
  if [ $((NOW-GIT_TS)) -ge 30 ] && [ -d "$REPO/.git" ]; then
    INT="$(tget int_branch)"
    CM="$(git -C "$REPO" log --oneline -3 "origin/$INT" 2>/dev/null | sed 's/^/  /' || echo '  (no int yet)')"
    PR="$(command -v gh >/dev/null && (cd "$REPO" && gh pr list --state open \
         --json number,title,statusCheckRollup \
         --template '{{range .}}  #{{.number}} {{.title}} · {{range .statusCheckRollup}}{{.state}} {{end}}{{"\n"}}{{end}}' 2>/dev/null) || echo '')"
    GIT_CACHE="$CM"$'\n---PR---\n'"$PR"; GIT_TS=$NOW
  fi
  clear
  SUMMARY='{}'
  [ -n "$OUT" ] && SUMMARY="$(python3 "$ROOT/artifacts/instance/tools/token-breaker.py" --summary "$OUT")"
  python3 - "$OUT" "$(tget max_loop_tokens)" "$(tget max_budget_usd)" "$CID" "$M" "$REPO" "$L" "$GIT_CACHE" "$FB" "$SUMMARY" << 'PY'
import json, sys, os, time, glob
out, cap, usd_cap, cid, m, repo, ledger, gitc, fb, raw_summary = sys.argv[1:11]
def bar(frac, n=10):
    frac=max(0,min(1,frac)); f=int(round(frac*n)); return "█"*f+"░"*(n-f)
now=time.strftime("%H:%M:%S")
summary=json.loads(raw_summary)
tok=summary.get("processed_tokens",0); o=summary.get("output_tokens",0)
den=summary.get("denials",0); err=summary.get("errors",0)
turns=summary.get("turns",0); usd=summary.get("cost_usd",0.0)
age=None; live="○ idle"
if out and os.path.exists(out):
    age=int(time.time()-os.path.getmtime(out))
    live=f"● LIVE ({age}s)" if age<30 else (f"◐ quiet ({age}s)" if age<300 else f"○ stalled ({age}s)")
capi=int(cap) if str(cap).isdigit() else 0
uc=float(usd_cap) if usd_cap else 0
def stall_wire():
    if age is None: return "· idle"
    return "✓ stall" if age<240 else "⚠ STALL"
W=62
print(f" LOOPSTRAP CONDUCTOR · {m}/{cid} · {now} · {live}")
print(" "+"─"*W)
print(" BUDGETS         now         cap       bar")
print(f"  processed  {tok/1e6:6.2f}M   {(str(round(capi/1e6,1))+'M') if capi else '  —':>7}   {bar(tok/capi) if capi else '·'*10}  {(100*tok/capi if capi else 0):4.1f}%")
print(f"  output     {o/1e3:6.1f}k        —      ·   turns≈{turns}")
print(f"  spend      ${usd:6.2f}   {('$'+str(uc)) if uc else '  —':>7}   {bar(usd/uc) if uc else '·'*10}  {(100*usd/uc if uc else 0):4.0f}%")
print(f" HEALTH      stall={stall_wire():9} denials={den:<3} errors={err:<3} repeat=not-derived progress=not-derived")
# unit / judges from plan
units=sorted(glob.glob(repo+"/plan/unit-*-pass-*.jsonl"))
u=units[-1].rsplit('/',1)[-1].replace('.jsonl','') if units else "(none yet)"
print(f" UNIT        {u}")
halt=os.path.exists(repo+"/plan/HALTED.md")
if halt: print("  ⛔ HALTED.md PRESENT — owner ARM required before relaunch")
# git panel (cached)
cm, _, pr = gitc.partition("---PR---")
print(" COMMITS (int, last 3)")
print(cm.rstrip() or "  (none)")
print(" PR / CHECKS")
print(pr.strip("\n") or "  (no open PRs)")
# ledger totals for this run
tl=to=0; mg=0; tu=0.0
if os.path.exists(ledger):
    for ln in open(ledger):
        if f"cid={cid}" in ln:
            for tok_field,acc in (("loop_tokens","tl"),("loop_out","to")):
                pass
            import re
            def g(k):
                mm=re.search(k+r"=([0-9.]+)",ln); return float(mm.group(1)) if mm else 0
            tl+=g("loop_tokens"); to+=g("loop_out"); tu+=g("loop_usd"); mg+=int(g("merges"))
print(" "+"─"*W)
print(f" LEDGER run-total: {tl/1e6:.2f}M tok · ${tu:.2f} · {mg} merges")
print(" q/Ctrl-C quit · READ-ONLY · levers: ops/sovereign.sh · detail: ops/loop-status.sh")
PY
  # non-blocking quit on 'q'
  if read -rsn1 -t 10 key 2>/dev/null; then [ "$key" = "q" ] && { tput cnorm 2>/dev/null; clear; echo "closed."; exit 0; }; fi
done
