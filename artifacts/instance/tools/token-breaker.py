#!/usr/bin/env python3
"""token-breaker.py — the loop's live tripwire battery (D49 token wall + D52 wires).

Follows the launcher's stream and trips the SAME machinery for every wall:
sticky plan/HALTED.md (only xor arms) · owner-record line · SIGTERM→SIGKILL.
Catching failure SOONER than the terminal caps (xor, 2026-07-19):

  tokens        cumulative processed tokens > cap (min of campaign/family — D49/D50)
  tokens-out    cumulative OUTPUT tokens > cap_out (repo tier — xor's expensive currency, D57)
  stall         no stream growth for STALL_S seconds while the runner lives (default 900)
  denial-storm  >= DENY_N permission-denials within the last WINDOW tool results (6 / 40)
  error-storm   >= ERR_MIN errors AND error fraction >= ERR_FRAC in last WINDOW (12 / 0.6 / 40)
  repeat-loop   one identical (tool,input) call >= REPEAT_N times in the last REPEAT_K (5 / 8)
  no-progress   PROG_CHECKS consecutive PROG_TOK-token checkpoints with zero movement in
                plan/ or .git/refs (2 checkpoints x 40M default => trips by ~80M, not 2.4B)
  gen-runaway   a single generator invocation's live JSONL (plan/unit-*-pass-*.jsonl)
                exceeds GEN_MB megabytes (default 25) — Codex's own early wire; bytes
                as the vendor-agnostic proxy until S1 verifies the token fields (D54)

Stall is BEAST-AWARE (D54): liveness = growth in the loop stream OR in the
generator's live JSONLs — a long legitimate codex exec never false-trips it.

Env knobs (xor's, per launch): STALL_S DENY_N ERR_MIN ERR_FRAC WINDOW REPEAT_N
REPEAT_K PROG_TOK PROG_CHECKS TW_DISABLE (comma list of wire names).
Accounting rule unchanged: in + cache_creation + cache_read + out, per assistant
message id, snapshot-overwrite (no chunk double-count).

Usage: token-breaker.py <stream> <cap_tokens> <runner_pid> <breaker_path>
                        <owner_records> <member> <cid> [wall_label] [cap_out] [out_label]
       token-breaker.py --tally <stream>        # processed total
       token-breaker.py --tally-out <stream>    # OUTPUT total (D57 repo currency)
"""
import hashlib, json, os, signal, sys, time
from collections import deque
from datetime import datetime, timezone

def stream_summary(path):
    per, per_out = {}, {}
    denials = errors = 0
    cost = 0.0
    try:
        for line in open(path, errors="ignore"):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            m = ev.get("message") or {}
            u = m.get("usage")
            mid = m.get("id")
            if ev.get("type") == "assistant" and u and mid:
                per[mid] = ((u.get("input_tokens") or 0)
                            + (u.get("cache_creation_input_tokens") or 0)
                            + (u.get("cache_read_input_tokens") or 0)
                            + (u.get("output_tokens") or 0))
                per_out[mid] = u.get("output_tokens") or 0
            if ev.get("type") == "result":
                raw_cost = ev.get("total_cost_usd")
                if isinstance(raw_cost, (int, float)):
                    cost = float(raw_cost)
                denials += len(ev.get("permission_denials") or [])
            if ev.get("is_error") or ev.get("subtype") == "error":
                errors += 1
    except FileNotFoundError:
        pass
    return {
        "processed_tokens": sum(per.values()),
        "output_tokens": sum(per_out.values()),
        "turns": len(per),
        "denials": denials,
        "errors": errors,
        "cost_usd": cost,
    }

if len(sys.argv) >= 3 and sys.argv[1] in ("--tally", "--tally-out", "--summary"):
    summary = stream_summary(sys.argv[2])
    if sys.argv[1] == "--tally":
        print(summary["processed_tokens"])
    elif sys.argv[1] == "--tally-out":
        print(summary["output_tokens"])
    else:
        print(json.dumps(summary, sort_keys=True))
    sys.exit(0)
if len(sys.argv) == 4 and sys.argv[1] == "--override-path":
    print(os.path.join(os.path.dirname(os.path.abspath(sys.argv[2])), "override.env"))
    sys.exit(0)

stream, cap, pid, breaker, owner, member, cid = (
    sys.argv[1], int(sys.argv[2]), int(sys.argv[3]),
    sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7])
wall_label = sys.argv[8] if len(sys.argv) > 8 else "campaign"
cap_out = int(sys.argv[9]) if len(sys.argv) > 9 else 0
out_label = sys.argv[10] if len(sys.argv) > 10 else "repo-output"
cap_usd = float(sys.argv[11]) if len(sys.argv) > 11 else 0.0
E = os.environ.get
STALL_S   = int(E("STALL_S", "900"))
DENY_N    = int(E("DENY_N", "6"))
ERR_MIN   = int(E("ERR_MIN", "12"))
ERR_FRAC  = float(E("ERR_FRAC", "0.6"))
WINDOW    = int(E("WINDOW", "40"))
REPEAT_N  = int(E("REPEAT_N", "5"))
REPEAT_K  = int(E("REPEAT_K", "8"))
PROG_TOK  = int(E("PROG_TOK", "40000000"))
PROG_CHECKS = int(E("PROG_CHECKS", "2"))
GEN_MB    = float(E("GEN_MB", "25"))
POLL_S    = float(E("POLL_S", "0.5"))
DISABLED  = set(x.strip() for x in E("TW_DISABLE", "").split(",") if x.strip())

repo = os.path.dirname(os.path.dirname(os.path.abspath(breaker)))
plan_dir = os.path.join(repo, "plan")

def gen_jsonls():
    out = []
    try:
        for fn in os.listdir(plan_dir):
            if fn.startswith("unit-") and fn.endswith(".jsonl"):
                fp = os.path.join(plan_dir, fn)
                try: st = os.stat(fp)
                except OSError: continue
                out.append((fp, st.st_size, st.st_mtime))
    except FileNotFoundError:
        pass
    return out
per_msg, per_out, results, calls = {}, {}, deque(maxlen=WINDOW), deque(maxlen=REPEAT_K)
cost_usd = 0.0
last_growth = time.time()
next_ckpt, stagnant, prev_fs = PROG_TOK, 0, None

def total(): return sum(per_msg.values())
def total_out(): return sum(per_out.values())
def alive(p):
    try: os.kill(p, 0); return True
    except OSError: return False
def _descendants(root):
    kids, table = [], {}
    try:
        for d in os.listdir("/proc"):
            if not d.isdigit(): continue
            try:
                with open(f"/proc/{d}/stat") as f: parts = f.read().split()
                table.setdefault(int(parts[3]), []).append(int(d))
            except OSError: pass
    except OSError: pass
    stack = [root]
    while stack:
        p = stack.pop()
        for c in table.get(p, []): kids.append(c); stack.append(c)
    return kids
def _sig_tree(root, sig):
    # STOP: parent first (no new children); CONT: children first, parent last
    kids = _descendants(root)
    order = [root] + kids if sig == signal.SIGSTOP else kids + [root]
    for p in order:
        try: os.kill(p, sig)
        except OSError: pass
def note(line):
    with open(owner, "a") as f: f.write(line + "\n")

def fs_state():
    tot, cnt, newest = 0, 0, 0.0
    for base in (os.path.join(repo, "plan"), os.path.join(repo, ".git", "refs")):
        for root, _, files in os.walk(base):
            for fn in files:
                try:
                    st = os.stat(os.path.join(root, fn))
                    tot += st.st_size; cnt += 1; newest = max(newest, st.st_mtime)
                except OSError: pass
    return (tot, cnt, round(newest, 2))

def trip(wire, detail):
    tok = total()
    os.makedirs(os.path.dirname(breaker), exist_ok=True)
    with open(breaker, "w") as f:
        f.write(f"""# HALTED — {member} · campaign {cid}

Written by the TRIPWIRE BATTERY (D49/D52), not the loop. Sticky: only xor
removes this file. Failure class: **halt** — a wire tripped, human required.

## Condition
- wire tripped  : **{wire}**
- detail        : {detail}
- tokens at trip: {tok:,} processed / {total_out():,} output   (processed-cap context: {cap:,} [{wall_label}])
- stream        : {stream}

## What happened to the run
Runner SIGTERM'd (SIGKILL after 10 s if needed). plan/ state and local commits
are intact (loss-proof); relaunch resumes from plan/backlog.md after xor arms.

## xor's act
Read the stream tail around the trip. Legitimate pattern → tune the wire's env
knob or TW_DISABLE it for the relaunch (knobs in this file's header), or re-rule
caps in the design lane (D47). Runaway confirmed → the stream is the evidence;
findings route as usual. Then remove this file and relaunch.
""")
    note(f"{datetime.now(timezone.utc).isoformat()} · TRIPWIRE {wire} · "
         f"{member}/{cid} · {detail} · tokens {tok:,} · runner pid {pid} terminated")
    if alive(pid):
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if not alive(pid): break
            time.sleep(0.5)
        if alive(pid): os.kill(pid, signal.SIGKILL)
    sys.exit(3)

def check_wires():
    global next_ckpt, stagnant, prev_fs
    if "tokens" not in DISABLED and total() > cap:
        trip("tokens", f"{total():,} processed > cap {cap:,}")
    if "tokens-out" not in DISABLED and cap_out > 0 and total_out() > cap_out:
        trip("tokens-out", f"{total_out():,} OUTPUT tokens > cap {cap_out:,} [{out_label}] — xor's expensive currency (D57)")
    if "budget" not in DISABLED and cap_usd > 0 and cost_usd > cap_usd:
        trip("budget", f"${cost_usd:.4f} > cap ${cap_usd:.4f}")
    if "denial-storm" not in DISABLED:
        d = sum(1 for r in results if r == "perm")
        if d >= DENY_N:
            trip("denial-storm", f"{d} permission denials in last {len(results)} tool results")
    if "error-storm" not in DISABLED and len(results) >= WINDOW:
        e = sum(1 for r in results if r != "ok")
        if e >= ERR_MIN and e / len(results) >= ERR_FRAC:
            trip("error-storm", f"{e}/{len(results)} tool results are errors")
    if "repeat-loop" not in DISABLED and len(calls) == REPEAT_K:
        top = max(calls, key=calls.count)
        if calls.count(top) >= REPEAT_N:
            trip("repeat-loop", f"identical call x{calls.count(top)} in last {REPEAT_K}: {top[0]}")
    if "gen-runaway" not in DISABLED:
        for fp, size, _ in gen_jsonls():
            if size > GEN_MB * 1024 * 1024:
                trip("gen-runaway", f"{os.path.basename(fp)} = {size/1048576:.1f} MB > GEN_MB={GEN_MB} (generator invocation runaway; bytes proxy until S1 token fields verified)")
    if "no-progress" not in DISABLED and total() >= next_ckpt:
        cur = fs_state()
        if prev_fs is not None and cur == prev_fs:
            stagnant += 1
            if stagnant >= PROG_CHECKS:
                trip("no-progress", f"{stagnant} x {PROG_TOK:,}-token checkpoints, zero movement in plan/ or refs")
        else:
            stagnant = 0
        prev_fs = cur
        next_ckpt += PROG_TOK

def feed(line):
    global cost_usd
    line = line.strip()
    if not line: return
    try: ev = json.loads(line)
    except Exception: return
    t = ev.get("type")
    msg = ev.get("message") or {}
    if t == "assistant":
        u, mid = msg.get("usage"), msg.get("id")
        if u and mid:
            per_msg[mid] = ((u.get("input_tokens") or 0)
                            + (u.get("cache_creation_input_tokens") or 0)
                            + (u.get("cache_read_input_tokens") or 0)
                            + (u.get("output_tokens") or 0))
            per_out[mid] = (u.get("output_tokens") or 0)
        for c in (msg.get("content") or []):
            if isinstance(c, dict) and c.get("type") == "tool_use":
                h = hashlib.md5(json.dumps(c.get("input"), sort_keys=True, default=str).encode()).hexdigest()
                calls.append((c.get("name"), h))
    elif t == "user":
        for c in (msg.get("content") or []):
            if isinstance(c, dict) and c.get("type") == "tool_result":
                blob = json.dumps(c.get("content", ""))
                if c.get("is_error"):
                    results.append("perm" if "Permission to use" in blob else "err")
                else:
                    results.append("ok")
    if t == "result":
        raw_cost = ev.get("total_cost_usd")
        if isinstance(raw_cost, (int, float)):
            cost_usd = float(raw_cost)

pos = 0
last_gen_mtime = 0.0
paused = False
while True:
    # ── OWNER OVERRIDE LANE (Sovereignty Principle; PAN-PAN / MAY DAY) ──
    # Honored ONLY if the file's owner-uid differs from this process's — OS proof
    # it was the pilot's hand, never the automation forging its own reprieve.
    ovr = os.path.join(os.path.dirname(os.path.abspath(owner)), "override.env")
    pause_want = paused
    try:
        if os.stat(ovr).st_uid != os.getuid():

            for line in open(ovr, errors="ignore"):
                line = line.strip()
                if not line or "=" not in line: continue
                k, v = line.split("=", 1)
                if   k == "OWNER_MAX_LOOP_TOKENS": cap = int(v);            note("PANPAN cap=%s" % v)
                elif k == "OWNER_STALL_S":         STALL_S = int(v);        note("PANPAN STALL_S=%s" % v)
                elif k == "OWNER_TOKENS_OUT":      cap_out = int(v);        note("PANPAN cap_out=%s" % v)
                elif k == "OWNER_DENY_N":          DENY_N = int(v);          note("PANPAN DENY_N=%s" % v)
                elif k == "OWNER_ERR_MIN":         ERR_MIN = int(v);        note("PANPAN ERR_MIN=%s" % v)
                elif k == "OWNER_MAX_BUDGET_USD": cap_usd = float(v);          note("PANPAN cap_usd=%s" % v)
                elif k == "OWNER_POLL_S":         POLL_S = max(0.05, float(v)); note("PANPAN POLL_S=%s" % v)
                elif k == "OWNER_HALT" and v == "1": trip("owner-halt", "MAY DAY — pilot halted the run")
                elif k == "OWNER_PAUSE":           pause_want = (v == "1")   # last line wins; L23
    except FileNotFoundError:
        pass
    # ── OWNER_PAUSE (L23): the breaker is the pause supervisor — freeze the tree,
    #    suspend liveness wires, keep the clocks honest; thaw on the pilot's word ──
    if pause_want and not paused:
        _sig_tree(pid, signal.SIGSTOP); paused = True
        note(f"{datetime.now(timezone.utc).isoformat()} · OWNER_PAUSE · {member}/{cid} · Conductor tree FROZEN (SIGSTOP); liveness wires suspended")
    elif paused and not pause_want:
        _sig_tree(pid, signal.SIGCONT); paused = False
        last_growth = time.time(); stagnant = 0; prev_fs = None
        note(f"{datetime.now(timezone.utc).isoformat()} · OWNER_PAUSE lifted · {member}/{cid} · Conductor THAWED (SIGCONT); liveness clocks reset")
    if paused:
        if alive(pid):
            last_growth = time.time()
            time.sleep(POLL_S)
            continue
        paused = False  # runner died while frozen (external kill) — fall through to drain/exit
    grew = False
    try:
        with open(stream, "r", errors="ignore") as f:
            f.seek(pos)
            for line in f:
                feed(line); grew = True
            pos = f.tell()
    except FileNotFoundError:
        pass
    gm = max((m for _, _, m in gen_jsonls()), default=0.0)
    if grew or gm > last_gen_mtime:
        last_growth = time.time()
    last_gen_mtime = max(last_gen_mtime, gm)
    check_wires()
    if "stall" not in DISABLED and alive(pid) and time.time() - last_growth > STALL_S:
        trip("stall", f"no stream growth for {int(time.time()-last_growth)} s (STALL_S={STALL_S})")
    if not alive(pid):
        try:
            with open(stream, "r", errors="ignore") as f:
                f.seek(pos)
                for line in f: feed(line)
        except FileNotFoundError:
            pass
        check_wires()
        sys.exit(0)
    time.sleep(POLL_S)
