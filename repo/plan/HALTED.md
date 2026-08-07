# HALTED — m · campaign c

Written by the TRIPWIRE BATTERY (D49/D52), not the loop. Sticky: only xor
removes this file. Failure class: **halt** — a wire tripped, human required.

## Condition
- wire tripped  : **stall**
- detail        : no stream growth for 2 s (STALL_S=2)
- tokens at trip: 0   (terminal cap was 999,999,999 [campaign] — this wire fired first)
- stream        : s.jsonl

## What happened to the run
Runner SIGTERM'd (SIGKILL after 10 s if needed). plan/ state and local commits
are intact (loss-proof); relaunch resumes from plan/backlog.md after xor arms.

## xor's act
Read the stream tail around the trip. Legitimate pattern → tune the wire's env
knob or TW_DISABLE it for the relaunch (knobs in this file's header), or re-rule
caps in the design lane (D47). Runaway confirmed → the stream is the evidence;
findings route as usual. Then remove this file and relaunch.
