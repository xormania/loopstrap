# Deep-Review Protocol — our design-lane CI (the reasoning pass)
*Living doc. 2026-07-20. This is the instrument Fable RUNS before every seal that
touches loop machinery: a sustained, token-expensive read of each artifact **as a
system**, reasoning over whether it coheres — not a grep. The FP entries are the
accumulated lens: each expensive discovery becomes a cheap question next time, so every
future review costs fewer tokens to find the same class. Grep narrows where to look;
**reasoning decides.** New failure found → new FP here first → it's in the lens forever.*

---

## The pass (run in this order, per artifact on the changed critical path)
For each script/config/doc the seal touches, read it end-to-end and ask, in order:

1. **Does control flow do what the header/comments claim?** (FP-04) — read the top
   claim, then trace the body; a lying header is a trap the operator trusts.
2. **Is every referenced symbol real in its scope?** (FP-01) — vars, funcs, config
   keys, trace fields. Grep to *list* candidates; reason about each to *decide*.
3. **Is every value that's read actually WIRED to its effect?** (FP-11) — the deadly
   one: read + reported != applied. Follow each input to the mechanism it names.
4. **Was every changed seam executed against a real-shaped fixture?** (FP-02) — not
   reasoned-about; run it, assert the exit code, exercise the failure path.
5. **Does any edit this seal claims actually take effect?** (FP-03) — re-read post-edit
   state; a sed/replace that matched nothing is a false "done."
6. **Is every external fact confirmed against the tool, not memory?** (FP-05) — codex
   fields, CLI flags, parser grammar, exit codes; check machines.md.
7. **Does any ruled precondition still hold?** (FP-06) — register-walk: a rule whose
   reason died but still ships. Descriptive mention != prescriptive survivor.
8. **Any owner-authority act adopted from a lower lane?** (FP-07) — main/history/auth/
   custody: is it xor's cited ruling, or a proposal I'm treating as one?
9. **Any literal that config now owns?** (FP-08) — path/org/sha baked where
   root config/campaign.toml should source it.
10. **Does every claim in my response have a receipt shown this turn?** (FP-09) — no
    "sealed/proven" without the output.
11. **Does it survive integrity?** (FP-10) — manifest self-check, parse-all, audit,
    inside the zip.
12. **Am I about to trust a mechanical check as the verdict?** (FP-12) — a grep hit is
    a question, never an answer. Reason about every flag before acting.

---

## The lens — failure modes, each a cheaper hunt next time
*Severity: RED blocks the seal; YELLOW warns. "Where it hides" is the token-saver.*

### FP-01 · phantom-symbol (RED)
A referenced var/func/key/field doesn't exist where it should -> silent no-op or crash.
**Where it hides:** Python hooks assigning module globals; cross-file var assumptions;
config keys assumed present. **Case:** cap_usd assigned in the breaker (lives in the
launcher). **See it:** trace the symbol to its definition, not its use.

### FP-02 · untested-seam (RED)
A changed path shipped without a real-fixture run. **Where it hides:** "small" edits
that feel obviously right; error/empty branches. **Case:** pipefail-empty-extract killed
the launcher post-CLEAR on a fresh machine. **See it:** did this seam RUN? exit asserted?

### FP-03 · vacuous-edit (RED)
An edit that matched nothing, claimed done. **Where it hides:** regex/sed against
formats you didn't re-read; YAML/structured edits. **Case:** "pull_request-only" matched
nothing; register said fixed. **See it:** re-read post-edit state, diff against intent.

### FP-04 · false-header (RED)
Code claims a behavior it doesn't implement. **Where it hides:** section headers that
survive a rewrite of the body beneath them; "structurally X" claims. **Case:** reset
"clones kill residue" (they re-import). **See it:** read claim, then prove it in the body.

### FP-05 · stale-external-fact (YELLOW->RED)
A vendor fact from memory, not the tool. **Where it hides:** trace field names, CLI
flags, exit codes, parser grammar. **Case:** codex output_tokens (right only because
verified). **See it:** is this confirmed against the version in machines.md?

### FP-06 · era-survivor (YELLOW)
A rule whose precondition died, still shipping. **Where it hides:** doctrine text,
sentinels, vocabulary; **descriptive mentions look like survivors but aren't** (e.g.
"dev is dormant — never target it" is correct post-D40, not a bug). **Case:**
never-delete after the backup leg; SET-BY-PREP branch after AUTO. **See it:** does
the reason still hold? is it prescribing the dead thing or naming it as dead?

### FP-07 · authority-conflation (RED)
A lower lane's proposal or a generic prior applied over an owner ruling. **Where it
hides:** anything touching main/history/auth/custody; steward hand-off blocks. **Case:**
the main->bare force-push adopted as if xor ruled it. **See it:** is this xor's cited
word, this turn, or am I inferring authority? (Sovereignty law.)

### FP-08 · hardcode-config-owns (YELLOW)
A literal baked where config should source it. **Where it hides:** family path, org,
base sha across scripts. **Case:** the root path baked as a literal across reset/prep/dash scripts (donor era).
**See it:** would a root config file own this value?

### FP-09 · claim-exceeds-receipt (RED, Fable's discipline)
A response claims done without a receipt shown that turn. **See it:** every state-claim
pairs to a command output in the same message.

### FP-10 · integrity-drift (RED)
Payload != its lsp_math.manifest; a script fails parse **inside the zip**; audit red.
**See it:** unzip -> self-check -> parse-all -> audit, every seal.

### FP-11 · report-without-wiring (RED, the deadliest)
A value read and *reported* (echoed/logged/dashboarded) but never *applied* to the
mechanism it names — reports success, does nothing. **Where it hides:** override/config
reads that echo a confirmation; anywhere a "applied X" line exists. **Case:**
OWNER_TOK echoed to banner+dashboard, never assigned to MAX_TOKENS — a PAN-PAN token
raise that lied. **See it:** for each read value, follow it to the effect; report != apply.

### FP-12 · checker-false-positive (YELLOW, meta)
The audit tooling flags valid patterns -> cries wolf -> gets ignored. **Case:** the FP-01
grep flagged 12 valid shell vars (combined one-liners, process-sub, ${N:?}, counters),
zero real. **See it:** a grep hit is a question; reason before acting, or the gate rots.

---

## Why this is the CI (doctrine)
Every expensive failure this system has produced was **semantic** — a base that was
c1's, a header that lied, a precondition that died, a value read but not wired. None
were string-findable. So the CI is not a linter; it is **this reasoning pass**, run by
Fable, token-expensive on purpose because thoroughness is the product. The catalog makes
each next pass cheaper: a class found once is a question asked forever after, so we spend
fewer tokens rediscovering what we already learned. That is the whole point — **waste
tokens once, on the deep read; save them every time after, via the lens.**

*Change record: 2026-07-20 — v2, restructured as the working review protocol (Fable).*

### FP-13 · lane-collapse (RED) — Loopstrap/product conflation
Treating the dev lane that BUILDS lsp_math and lsp_math the product as one thing: runtime
vocabulary naming dev machinery, dev machinery claimed inside the product, a runtime or
parked lexicon cited as authority over Loopstrap, or forgetting that lsp_math is never
used to build lsp_math. **This class has a structural tripwire: `ops/wall.sh`** — deterministic,
direction-aware (R1–R6), with `ops/wall-allow.txt` carrying RULED exceptions only (each cites
its ruling). It survives resets precisely because it is encoded, not remembered — the
prior that causes the conflation lives in every fresh instance, so the guard must live
outside them all. The tripwire's duty station is NEW text: handoffs, Fable's outputs,
incoming reviews. Point and run.
