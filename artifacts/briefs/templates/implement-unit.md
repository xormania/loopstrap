# Work-unit brief — <UNIT-ID>

*Issued by the Conductor at dispatch; executed by the implementer role (`codex exec`). This file defines the
implementer's ENTIRE scope — nothing outside it is licensed. Template lineage D24; trio topology L7.*

## 1 · Identity
- Unit: `<UNIT-ID>`   ·   Member: `<member>`   ·   Branch: `unit/<UNIT-ID>`
- Brief hash: `<filled by steward at issue>`   ·   Config hash: `<installed-config manifest hash>`

## 2 · Objective
One paragraph. What exists when this unit is done that does not exist now.

## 3 · Contract clauses in scope — VERBATIM
> (Quote the exact clauses from artifacts/contracts/... — source path + section per quote.
>  The implementer works against these words, not a summary of them.)

## 4 · Deliverables
- Files / symbols expected (paths, names).
- Tests required (what must be exercised; the refusal⇒nothing-changed property where applicable).
- **The unit's adversarial tests** (paths listed here) must pass — they are basis for this unit, authored blind to your implementation (L7); their claims' **Intended API surface is unit basis at shape level** unless it contradicts a §3 clause — a contradiction, or a test you believe wrong, is a **Finding**, never an edit (L8).

## 5 · Acceptance
- The four judges green (cargo check · test · clippy -D warnings · fmt --check) — CI re-runs them.
- Fixtures listed here pass: `<fixture ids or "none yet — founding unit">`.
- No work product outside §3's clauses and §4's deliverables.

## 6 · Out of scope — the fence
Explicit list. Adjacent temptations named (the rationalizations section of your doctrine applies).

## 7 · Known hazards
Collision-map slice for this unit: terms likely to be misread, gotchas, sibling boundaries nearby.

## 8 · Claims report (required, as the PR body)
Sections, in order: **Did** · **Verified** (with judge output summary) · **Diagnostics** (first line machine-countable: `diag: found=N fixed=M files=K` or `diag: not-present`; prose after) · **Could not verify** ·
**Findings** (spec defects/ambiguities hit — each one halts scope creep, never patches around).

## 9 · Protocol reminders
Detailed, unattributed commits with trailers `Unit:`/`Pass:`/`Brief:`/`Config:` · push `unit/<UNIT-ID>`
only (cut from the campaign int branch; names from the cited `campaign.toml`, D40) · PR targets the int branch — main is the human's promotion line · run mode per
kickoff (integration is the Conductor's: stop at local commits + claims; you never push, never merge) ·
stop and refuse loudly on any precondition failure.
