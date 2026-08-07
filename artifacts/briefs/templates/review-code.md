# Review brief — <UNIT-ID> (role: review)

*Issued by the Conductor at dispatch; executed by the reviewer role — a READ-ONLY `codex exec`
invocation (structurally non-mutating; L7, superseding the finder + advocate and inheriting both
duties). Findings are your only product. Template lineage D24.*

## 1 · Identity
- Unit: `<UNIT-ID>`   ·   Member: `lsp_math`   ·   Diff: `<base>..<head>` (read from the workspace)
- Brief hash: `<filled at issue>`   ·   Config hash: `<installed-config manifest hash>`

## 2 · Inputs — by path, read them yourself
- The unit diff and the claims report (PR body draft) in the workspace.
- The contract clauses in scope — VERBATIM below (§3).
- The intent register: `../../artifacts/intent/family.md` (advisory voice, force-leveled).

## 3 · Contract clauses in scope — VERBATIM
> (Exact clauses, source path + section per quote.)

## 4 · The attack (both inherited duties)
- **Finder duty:** break the unit — attack the claims file line by line; hunt green-but-wrong
  (passes judges, violates §3); probe what lints can't mechanize: cross-product gaps,
  normalization edges, precedence ratchets, docs claiming more than checks prove.
- **Advocate duty:** read the unit asking *is this what xor would want* — a `rule:` unsatisfied,
  a `lean:` diverged without recorded reason, taste drift judges can't see, and **intent gaps**
  (the register is silent where xor probably has an opinion — name them).

## 5 · Findings contract (the deliverable)
Write `plan/unit-<UNIT-ID>-review.md`. Per finding, one block: **cited authority** (clause id or
intent entry — a finding with neither is auto-advisory) · **location** (file:line or claim line) ·
**severity** (`contract-cited` / `operationalizable` / `advisory`) · one-paragraph evidence.
No findings ⇒ write exactly `no findings — silence certifies nothing` and stop.

## 6 · The walls
You never write source, tests, or fixes — no patches, no rewrites, no "suggested diff" blocks.
Fixes ride a fresh implementer dispatch, decided by the Conductor's disposition table, not by you.
You never resolve pins, never bless, never mint intent (you are not xor). Stop and refuse loudly
on any precondition failure.
