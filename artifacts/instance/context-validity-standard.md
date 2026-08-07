# Context-Validity Working Standard — Fable's pre-seal checklist
*Living doc. Ratified 2026-07-20 under the Sovereignty arc. Fable runs the checklist
before EVERY courier seal that touches loop machinery. `preship-audit` (P20) is the
executable half — this doc is the human-readable half they share. xor's enforcement
ideas land in §4 as they're given.*

---

## §0 · Why this exists (the Context-Validity Principle — standing law)
> Loop work amplifies its inputs **5–10×**: an unverified assumption in the design is
> discovered only through an expensive unattended run. Therefore every fact a loop
> artifact depends on — a variable name, a file path, an exit code, a trace field, a
> base state, a CLI flag — is **verified against the actual source before it ships,
> never asserted from memory or pattern.** "Probably correct" is treated as *incorrect
> until proven.* Verification is always paid at design time, because the loop makes the
> alternative cost 5–10× more. Shortcuts are not faster here — they are debt at leverage.

The failure mode this defeats: *the expert who knows the step and skips it because it
felt safe.* Case studies from the 2026-07-19/20 night, all shipped then caught:
`cap_usd` referenced in the breaker where it lives in the launcher (silent no-op wire);
override injected at wrong indentation; variable names the wires never read; the
"pull_request-only" YAML edit that matched nothing; the reset header claiming clones
kill residue when they re-import it. Every one was "probably right." Every one would
have detonated at run scale.

---

## §1 · THE CHECKLIST (run before every seal)
Copy this block into the working notes each seal; tick every line or the seal doesn't ship.

### A · Symbol & reference validity (the wrote-from-memory killer)
- [ ] **Every variable a script references is grepped in the file that defines it** —
      no referent asserted from memory. (Case study: `cap_usd`.)
- [ ] Every file path a script reads/writes is confirmed to exist (or is a runtime
      output whose creator is named).
- [ ] Every `campaign.toml`/config key a script reads is confirmed present in the file.
- [ ] Every function/helper called is defined or sourced in scope.
- [ ] No hardcoded value that config now owns (paths, org, sha) — sourced, not baked.

### B · Execution validity (D65 held always, not when convenient)
- [ ] **Every changed seam executed against a real-shaped fixture** — reasoned-about ≠ tested.
- [ ] The fixture uses REAL shapes (actual stream/trace/ledger formats), not toy stubs
      that pass vacuously.
- [ ] Exit codes asserted, not assumed (script gates on the code it actually returns).
- [ ] The failure path is exercised, not just the happy path.

### C · External-fact validity (confirm against the tool, never remember)
- [ ] Every vendor fact (codex trace fields, CLI flags, exit codes, Claude Code parser
      grammar) confirmed against the actual tool/version — not training memory.
- [ ] Version pins current vs `machines.md`; drift is a re-verify event, not a shrug.
- [ ] No external behavior assumed from "how it usually works."

### D · Integrity validity (the machine-drift gate)
- [ ] Courier self-verifies: payload matches its own `lsp_math.manifest`.
- [ ] Landing pins recompute clean (or self-heal-and-log per D80, walling only on corruption).
- [ ] `audit-consistency` green; every touched script `bash -n` / `ast.parse` **inside the zip**.

### E · Honesty validity (no claim exceeds mechanism)
- [ ] Every claim in the response is backed by a receipt shown this turn — no "sealed"
      before the edit landed, no "proven" without the run.
- [ ] Assumption words — *I believe / should be / typically / probably* — treated as
      STOP signals: each one marks unverified context; verify before proceeding.
- [ ] Costs/failures of this seal stated plainly (the standing rule with xor).

---

## §2 · The stop-signal reflex
In loop design these phrases mean *"I am about to assert unverified context"* — the
next action is to verify, never to proceed: **"I believe…", "should be…", "typically…",
"probably…", "I think it's called…", "from memory…", "usually works…"**. Grep it,
run it, or confirm it against the tool. Then proceed.

---

## §3 · `preship-audit` — the executable half (P20)
Structure over promise: the seal should REFUSE if the standard isn't met, so rigor
doesn't depend on Fable remembering. Planned checks (mechanizing §1 where a machine can):
- **A (symbols):** parse each `ops/`+root script for `$VARS` and referenced paths;
  fail if a referent doesn't resolve in its expected file/scope.
- **B (execution):** require a fixture-run marker per changed seam this seal.
- **D (integrity):** manifest self-check · `bash -n`/`ast.parse` all · audit green — inside the zip.
- **E (honesty):** grep the artifact set for stop-signal words in comments/claims; flag for review.
*Build gated on P20 = yes. Fails the seal loud; names the unmet check.*

---

## §3b · The failure-pattern catalog (our CI's test corpus)
`preship-audit` is design-lane CI; a CI is only as strong as its test suite. The suite
is **`artifacts/instance/failure-patterns.md`** — ten documented ways loop-context
validity breaks (FP-01…FP-10), nine from live specimens this build. Each pattern is a
check; 🔴 blocks the seal, 🟡 warns. New failures are catalogued there first, then wired.

## §4 · xor's enforcement mechanisms
*(reserved — xor's ideas land here as given; this section drives `preship-audit`'s spec)*
- _pending_

---

*Change record: 2026-07-20 — v1 drafted (Fable), under the Context-Validity Principle.*
