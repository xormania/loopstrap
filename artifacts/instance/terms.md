# terms.md — the dev-lane working glossary (L18)

**Scope wall, first:** these are Loopstrap's working terms. This file is NEVER the
lsp_math lexicon — the product lexicon lives in `contracts/` once ratified and governs
runtime vocabulary; cross-lane text uses qualified forms. Nothing here preempts it.

## Stations and mechanisms
- **Fable** — the persona/engine class (this project's Claude design intelligence); a
  class, not a station. When station matters, name the station.
- **design session** — Fable + xor drafting and ruling law (off-box; no hands anywhere).
- **steward** — **xor's interface to the system (L21)**: the one root-scoped Claude Code
  session, staffed by Fable, owned by xor. Write set `reports/ · briefs/ · campaigns/`;
  runs the arm-gate; dispatches prep handoffs + the Conductor launch (L20). Self-orients
  at wake (L38): status sweep + sitrep before xor's first word. Standing acts run
  without xor present; owner acts execute through the session at xor's explicit
  word — ask-gate click = the hand (L37) — never initiated.
  Hands ungated inside the user (L40); repo-editing abstained by doctrine for record-truth, detectable in git + owner-records. Never the Conductor, never a branch-creator.
- **Conductor** *(ruled 2026-07-22, L19; formerly "the loop")* — one Claude Code session
  running a member's campaign in that member's repo, per lane (L16); conducts, never
  composes (L5) — named for its verb. NEVER the LSP server's runtime cycle (the
  catalogued lane collision). Legacy `loop` token survives ONLY in mechanical
  identifiers (`launch-loop.sh`, `lsp_math-loop.lock`, ledger `loop_usd`, historic
  standup docs) — identifiers name artifacts, not the station.
- **generator** — the mechanism: one bounded zero-credential `codex exec` INVOCATION,
  loop-dispatched.
- **test-writer / implementer / reviewer** — the trio ROLES (L7) a generator invocation
  is prompted into (`role=` test|code|review; `retro` at close).
- **planner** — the plan HANDOFF: a bounded fresh-context Claude Code invocation at
  prep (L12). Not the steward inline (superseded L11), not a codex role (retired L10c).
- **plan review** — the adversarial Claude Code handoff attacking worksheets at prep.
- **the two channels (L42)** — conversation governs the steward (xor's word sovereign,
  warn-comply-record; only promote and breaker-uid are physics refusals); **signals
  govern the flight** — the headless Conductor + breaker, which cannot hear words.
- **PAN-PAN** — xor's urgency signal (`ops/sovereign.sh panpan`): steer a running
  campaign via `override.env` (budget, thresholds, cadence); the run keeps flying;
  the breaker adopts within one poll.
- **MAYDAY** — xor's distress signal (`ops/sovereign.sh mayday`): positive control —
  member-planted walls off (root carries none, L40/L42), pause/halt choice, and
  **total authority (L22): anything may change by xor's hand, including
  authoritative docs**; no protocol gates it, no agent flags it as
  drift. MAYDAY offers pause/halt/walls-only at declaration (L23). Stand-down = walls on + the MAYDAY reconciliation.
- **pause / resume** — sovereign freeze of the Conductor tree mid-flight (L23): the
  breaker supervises via `OWNER_PAUSE` (forgery-proof uid lane), suspends liveness
  wires, resets clocks at thaw; zero context loss. Pause ≠ halt: no breaker file,
  no re-arm ceremony — resume is one command.
- **arm-gate** — the pre-ARM verification battery (L13); the ruled name — "smoke test" is informal and carries donor-campaign baggage; prefer arm-gate in dev-lane text.
- **judges** — the deterministic tool set (cargo four · fixtures · join-key), local + CI.
- **xor** — the owner: arm · rule · ratify · promote. (xormania / xor-machine /
  math-lsp are accounts, not personas.)

## Word discipline
- **invocation** = codex, loop-dispatched, in-run · **handoff** = Claude Code,
  steward-dispatched, at prep.
- "review" unqualified is banned in dev-lane text: say **reviewer**, **plan review**,
  or **promotion review**.

## Scales (each a cell at its scale — L17)
split-child ⊂ unit (one trio cycle) ⊂ lane (execution partition, worktree-backed,
clause-seam disjoint) ⊂ segment (docs-derived partition owning clauses; source of
lanes, not identical to them) ⊂ member (repo-scale cell) ⊂ estate.
**campaign** = the managed run of one member (many sessions, possibly many lanes); **the run** = a campaign's execution — post-L19, bare "loop" is never used for the cycle (say the run, the cycle, or the campaign);
**session** = one Claude Code process lifetime; **cell** = the abstract contract-bounded
black box at any scale.

- **brief-atomicity** — a dispatched unit completes against its dispatched (hashed)
  basis; amendments bind from the next dispatch (L24).
- **compiled context** — the delivery layer of a deliverable's docs (L27): anchors,
  term cards, digests, scaffold — compiled from the ratified triad, regenerated on
  every amendment, delivered verbatim in the brief sandwich.
- **the ripple** — the completed-work re-verification act (L24) — the dev-lane form
  of the method's *absorption sweep*; both regenerate every derived layer: doc delta → changed
  clause ids → the trace (clause→segment→unit→fixtures) → test role re-derives
  fixtures blind vs the new text → green = survival evidenced, red = rework units.

- **the triad** — a deliverable's prose doc set (L26): lexicon (meaning) · system
  contracts (behavior) · experience spec (judgment; advisory-to-reviewer force).
- **docs-manifest** — the plug connector (L26): hashes + law lines + judge bindings;
  its presence + verification licenses the member.

## Instruments
kickoff (campaign-scope, hash-cites every input) ≠ backlog (accepted unit-granular
plan) ≠ worksheet (plan handoff's draft, pre-disposition) ≠ brief (per-role, per-unit
sandwich). breaker (`plan/HALTED.md`, sticky) ≠ arm-gate (pre-ARM battery) ≠ wall
(structural denial).

## The lane split (THE WALL, vocabulary form)
Dev-lane words: brief · backlog · kickoff · courier · steward · loop · lane · unit.
Product words: each member's reserved terms, per ITS lexicon (none authored yet).
Cross-lane text qualifies (final forms belong to each deliverable's lexicon — unauthored for lsp_math; until then, qualified forms by discipline). **The document classes never cross (L25):** the lexicon + contract set describe the DELIVERABLE (per member, its launch key); Loopstrap itself is governed by this dev-lane corpus and the register — two senses of "product," never conflated: Loopstrap is the product of the endeavor (L15); the member is the product of Loopstrap.
