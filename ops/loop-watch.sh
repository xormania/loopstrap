#!/usr/bin/env bash
# ops/loop-watch.sh <campaign-id> — live pretty-tail of the newest stream. READ-ONLY.
set -uo pipefail
CID="${1:?usage: loop-watch.sh <campaign-id>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(ls -t "$ROOT/artifacts/reports/$CID"/loop-*.jsonl 2>/dev/null | head -1)" || true
[ -n "${OUT:-}" ] || { echo "no stream for $CID"; exit 1; }
echo "watching $OUT  (Ctrl-C exits; loop unaffected)"
tail -n 20 -f "$OUT" | python3 -u -c '
import json, sys, datetime
for line in sys.stdin:
    try: ev=json.loads(line)
    except Exception: continue
    t=datetime.datetime.now().strftime("%H:%M:%S"); ty=ev.get("type","?")
    if ty=="assistant":
        c=(ev.get("message") or {}).get("content") or []
        for b in c:
            if b.get("type")=="tool_use": print(f"{t} ▸ {b.get('name','tool')}: {json.dumps(b.get('input',{}))[:110]}")
            elif b.get("type")=="text" and b.get("text","").strip(): print(f"{t} ✎ {b['text'].strip()[:110]}")
    elif ty=="result":
        print(f"{t} ■ result · ${ev.get('total_cost_usd','?')} · denials={len(ev.get('permission_denials') or [])}")
    elif ty=="system": print(f"{t} · {ev.get('subtype','system')}")
'
