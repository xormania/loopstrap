# metrics.md — the ROI capture dictionary (ruled file, D51)

Purpose (xor, 2026-07-19): *"We don't know much — data is king… capture the
data so we know where the marginal rate of return is 0."* This file is the
schema: every signal the instrument captures, at what grain, where it lives,
how it joins, and which marginal question it exists to answer. Capture is
total and cheap now; analysis comes after data exists (D51 — the report lens
builds against real records, never against an imagined format). If a signal
is not in this dictionary, it is not relied upon; if a needed signal is
missing, that is a finding, and this file gains a row before any analysis
pretends otherwise.

## Grains and join keys

Everything joins on the I2 spine: **Unit · Pass · Brief-hash · Config-hash**
(commit trailers ↔ pass records ↔ claims ↔ traces), plus `session_id`
(loop stream), `cid`, `run`, and ISO timestamps (pass records ↔ stream slices).

## Cost signals (spend)

**Ledger line format (current, D50→D58):** `<iso> run= member= cid= loop_tokens=
loop_out= gen_tokens= gen_out= loop_usd= wall_s= merges= rc= stream=
[reconciled=1]` — `loop_out`/`gen_out` are the OUTPUT columns (repo walls);
`stream=` keys the crash-orphan reconcile; earlier register texts describe the
format's ancestors and are history, not spec.

**Three ledgered quantities (D54/D57):** per beast, PROCESSED (family/campaign walls) and **OUTPUT** (repo walls — xor's expensive currency) stay distinct columns;  Claude (loop) and Codex (generator) are
separate beasts — separate vendors, billing, and rate limits. Every table keeps
them in separate columns; any blended total is a defect.

| signal | grain | home | notes |
|---|---|---|---|
| loop processed tokens | run / turn | stream JSONL (`usage` per message id) + ledger `loop_tokens=` (breaker `--tally`, single truth) | in + cache_c + cache_r + out; per-pass attribution via timestamp slicing against pass `start=`/`end=` |
| loop cost USD | run | stream `total_cost_usd` → ledger `loop_usd=` | exact, vendor-reported |
| generator tokens per CHUNK | chunk | derivable: groupby(chunk(unit_id)) over invocation JSONLs — **zero new capture; the serial schedule is the calibration experiment (D55)** | the per-chunk cost curve that seeds `codex_chunk` derivation |
| generator tokens | invocation (unit×pass) | `plan/unit-<id>-pass-<n>.jsonl` (`turn.completed`) → ledger `gen_tokens=` best-effort | **field map verifies at first S1** — until then ledger may read `NA`; the JSONLs hold the raw truth regardless |
| generator wall time | pass | pass record `gen_s=` | loop-clocked |
| judge wall time | pass | pass record `judges_s=` + per-pass judge logs | loop-clocked; logs hold per-judge detail |
| run wall time | run | ledger `wall_s=` | launcher-clocked |
| serena quiescence cost | invocation | derivable from generator JSONL timing; first-run verify item | not separately clocked yet — becomes a row if S1 shows it matters |
| gen-runaway trips | invocation | breaker + owner records | a single Codex invocation past GEN_MB — the generator's own early wire (bytes proxy → token-parse after S1) |
| halts / tripwire events | event | `plan/HALTED.md` + owner-records lines | each names its wire (tokens · stall · denial-storm · error-storm · repeat-loop · no-progress) and its wall — **which failure mode burns money, and how early it announces** |

**First field calibration (smoke-1, 2026-07-19):** one clean unit end-to-end ≈ **$4–5 with CI green**; ~40–50% of the $10 run went to CI-wait wake cycles (→ R3 ruling pending). Generator field map verified; `gen_out` ledgers real from D67 on.

## Output signals (return)

| signal | grain | home | marginal question it answers |
|---|---|---|---|
| verdicts per judge | pass | pass record + judge logs + CI | did this pass buy green? |
| disposition | pass | pass record | merged / redo / delayed — the pass's fate |
| diff size | pass | pass record `diff=` (files/+/−) | tokens per landed line; where extra passes stop moving code |
| commit count | pass | pass record `commits=` | granularity health |
| diagnostics yield | pass | claims `diag: found=N fixed=M files=K` | what the Serena step buys pre-judge — its own ROI curve |
| findings raised | pass / unit | pass record count + `plan/findings.md` | when a pass's value was a refusal or a spec catch |
| passes-to-green | unit | derivable (records) | the core unit-cost curve; calibrates future **pass budgets** (the plan-level budget currency — D50 talk, ratified) |
| merges landed | run | ledger `merges=` | run-grain numerator |
| clause coverage | unit ↔ clause | c2 backlog Tier-1 map × unit records | ROI per contract clause — the deepest denominator |
| finder/advocate yield | invocation | their JSONLs + findings | is adversarial review paying its token bill? |
| survived human review | unit | sweep records (xor's Q2 column) | the only verdict above green |

## Analysis posture (ratified with D51)

- **Walls protect; reports govern.** Two enforcement tiers only (campaign D49,
  family D50 — currently LIBERAL by xor's guidance). Chunk/unit/pass budgets
  are **pass-denominated plans** and measured outcomes, never token walls.
- The zero-marginal search is empirical: curves come from joining cost×output
  at each grain above. First lens: `budget-report` (post-smoke, real records).
- Capture failures are findings, not shrugs: a pass record missing an ROI
  field is a conformance item the moment it is seen.
