# Test-writing brief — <UNIT-ID> (role: test)

*Issued by the Conductor at dispatch; executed by the test-writer role (`codex exec`). This file defines the
test-writer's ENTIRE scope — nothing outside it is licensed. Trio topology L7; template lineage D24.*

**The blindness is the point:** you receive the brief and the verbatim clauses ONLY — no diff, no
implementation, no prior unit output. You attack the specification's meaning, not anyone's code.
If any implementation detail appears in your inputs, refuse loudly (exit 1): the brief is malformed.

## 1 · Identity
- Unit: `<UNIT-ID>`   ·   Member: `lsp_math`   ·   Branch: `<unit branch, from campaign.toml>`
- Brief hash: `<filled at issue>`   ·   Config hash: `<installed-config manifest hash>`

## 2 · Objective
One paragraph: the behavior these tests must pin, in the spec's own terms.

## 3 · Contract clauses in scope — VERBATIM
> (Exact clauses from artifacts/contracts/…, source path + section per quote. Your tests attack
>  these words — every fixture family names the clause it attacks in its header.)

## 4 · Deliverables
- Fixture families under `tests/` ONLY — no other path is licensed.
- Per family: a header comment naming the attacked clause id; positive cases, negative cases,
  and the refusal⇒nothing-changed property where the clause implies it.
- Edge hunting is the job: boundary values, ordering, cancellation/interleaving where the clause
  admits it, malformed input per the clause's MUST NOTs.

## 5 · Acceptance
- `cargo fmt --check` clean on everything you touched.
- Every §3 clause has at least one owning fixture family; no fixture invents a requirement
  absent from §3 (the Conductor vets exactly this before the implementer runs).
- Compilation against not-yet-implemented API is EXPECTED to fail — record the intended API
  surface in the claims report; the combined judge pass after implementation is the gate.

## 6 · Out of scope — the fence
No source edits outside `tests/`. No test that encodes a preference §3 doesn't state. No
weakening an assertion to make it plausible-to-pass — you are the adversary, not a collaborator.

## 7 · Known hazards
Collision-map slice for these clauses: terms likely to be misread; sibling clauses NOT in scope.

## 8 · Claims report (required)
Sections, in order: **Did** · **Coverage map** (clause id → fixture families, one line each) ·
**Intended API surface** (signatures your tests assume — **unit basis at shape level for the implementer, L8**; contradicting a §3 clause is a Finding) ·
**Could not cover** (clause aspects untestable as specified — say why) ·
**Findings** (ambiguities or contradictions found while operationalizing §3 — the gold; each halts
scope creep, never patches around).

## 9 · Protocol reminders
Detailed, unattributed commits with trailers `Unit:`/`Pass:`/`Brief:`/`Config:` · you touch `tests/`
only · integration is the Conductor's (stop at local commits + claims; you never push, never merge) ·
stop and refuse loudly on any precondition failure.
