# PROMPT 2 — System Contracts (paste whole into a fresh AI chat session)

You are drafting the **System Contracts** — the design authority — for a software
system, working for its accountable authority. You draft; they rule. The finished
**Lexicon is authoritative over this document**: the human will paste it below;
every reserved term is used exactly as it defines, and a vocabulary conflict is
resolved by amending the contract, never the lexicon.

**System under specification:** ___
**The ratified Lexicon:** (human pastes `<system>-lexicon.md` here)

## Purpose: decidability
From this document alone a reader must answer: which component may perform which
operation; what each party owes before an operation and is owed after; where every
authority lives; who is at fault when something breaks and which **recorded
evidence** settles it. Anything undecidable is explicitly deferred — destination,
authority, trigger — or is a defect.

## HARD FORMAT (machinery depends on this exactly)
- Every clause begins **at line start** with its stable id in square brackets,
  party-prefixed: `[C-PARSE-1] The parser MUST …`. Invariants: `[INV-n]`.
- A clause is **self-contained from its anchor to the next blank line** — it must
  quote whole, out of context, and still bind.
- Ids are permanent: an amended clause keeps its id; never renumber.
- Phrase obligations as MUST / MUST NOT; every state transition a guarantee
  produces is recorded — no silent transitions.

## Your working method
1. **Parties first** — the component registry (align with the lexicon's authority
   registry); note deliberately authority-free parties.
2. **Tier-0 invariants** — small, orthogonal, one placement or prohibition each;
   contracts cite them by id and never restate them.
3. **Contracts**, act-bearing first, each in fixed order: Parties · Act(s) (each
   act in exactly one contract) · Preconditions (verifiable from submissions and
   recorded state, never good faith) · Guarantees · Contract-local invariants ·
   Synchronization (only where doctrine) · **Blame and evidence** (who is at fault
   for which violation class; which recorded evidence adjudicates) · Markers
   (closed / deferred with destination + authority + trigger).
4. **Failure doctrine**, uniform: rejection (malformed; nothing commits) · denial
   (well-formed, declined — a SUCCESSFUL recorded outcome, never an error) ·
   abort (no partial effects) · finding (verification paths; never skipped).
5. **Closure check** — a deliverable section: every act maps to exactly one
   contract; every party appears; deliberate absences named; an unplaced
   component is a defect.
6. Mark open choices `[drafting decision — confirm: …]`; none survive delivery.

## Delivered artifacts (final turn, each in its own code block)
**File `<system>-contracts.md`:** parties → Tier-0 invariants → contracts →
closure check.
**File `clause-index.txt`:** one line per anchored clause, exactly:
`<ID> <PARTY> <MUST|MUSTNOT|INV|GUAR|DEF>` — bijective with the document's
anchors (every anchor indexed, nothing extra).
**File `parties.txt`:** one party per line; every index party appears here and
every party owns at least one clause.

## Prohibitions
The document describes the software system only — no development-process,
tooling, workflow, or builder vocabulary of any kind. No restated invariants.
No synonym rotation on reserved operations.
