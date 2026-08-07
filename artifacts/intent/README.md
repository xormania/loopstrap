# Intent — Your Overview (what to add, where it goes)

*A thinking doc for xor. The mechanism is instance §15; this is the map for filling it. One line here prevents one minted DEFAULT there — that's the whole economy.*

---

## 1 · What an entry is

Your voice, one to a few lines, plain speech, force-leveled:

- **`lean:`** — guidance. Agents resolve silence *along it*; diverging is legal with a recorded reason. Cheap to write because it's cheap to be wrong in.
- **`rule:`** — a gate. No divergence path; conflicts halt. Micro-basis without the ceremony.

Precedence never changes: **ratified basis > rule > lean > conservative default.**

**The force-level test, one question:** *if an agent violates this and the work is otherwise perfect, do I reject it?* Yes → `rule:`. No → `lean:`. If you're writing many rules on one theme, that's a spec asking to be authored — write the rules now, expect them to graduate.

## 2 · Where things go — the placement map

| You're thinking… | It goes in… |
|---|---|
| "Everyone, always" | `intent/family.md` |
| "Just this member's cell" | `intent/<member>.md` (create on first need — e.g. `intent/lsp_math.md` before c2) |
| "Just this run" (priorities, tempo, what winning means this campaign) | the campaign **rider** (`campaigns/<id>/`), not the register — time-boxed intent doesn't belong in a standing file |
| "This must be family law forever, formally" | that's **basis** (FR entry / spec clause) — write it as `rule:` today for speed; it promotes at a sweep |
| "How the deliverable should *feel*" | the member's **experience spec** when it exists; until then, family-floor `lean:`s that will seed it |

Scope test in one line: *who should feel this?* Family = every cell, every campaign. Member = one cell. Rider = one run.

## 3 · The six types — with the questions to ask yourself

**T1 · Engineering posture** *(family; member files override)* — how code gets built where specs are silent. Ask yourself: Dependencies — pull a crate readily, or std-lib-first and justify every add? Abstraction — concrete-now or generalize-early? Error texture beyond the failure vocabulary — how much context in messages? `unsafe` / macros / clever generics — tolerated, discouraged, banned? Test density beyond what judges force? Doc/comment voice — sparse and precise, or narrative?
*Examples:* `lean: std-lib-first; a new dependency needs one sentence of justification in the claims file.` · `rule: no unsafe blocks anywhere in family code.`

**T2 · Experience floor** *(family leans until a member's experience spec exists)* — the feel every surface shares. Ask: Output on success — silent, one line, or chatty? Color/formatting defaults? Error shape — remedy-first? never a stack trace? Help text voice? What must machine-readable output never do?
*Example:* `lean: errors lead with the remedy line; internals never appear unless a debug flag asks.`

**T3 · Decision-meta** *(family — highest leverage per line)* — how agents should decide *when deciding*. Ask: When two readings both fit, narrower or more capable? What does "conservative" mean to me — minimal surface? maximal validation? refuse-early? When should an agent prefer halting over a lean-guided mint (how expensive is my attention vs. a wrong guess)? How much should it invest making silence *visible* (naming the gap in claims) vs. just resolving it?
*Example:* `lean: when two readings fit, take the one with the smaller public surface.`

**T4 · Boundary rules** *(the `rule:` class — few, absolute)* — reject-on-sight regardless of correctness. Ask: What would I revert even if green? Network touches? License/version fields? Dependency provenance? Anything that writes outside its cell?
*Examples:* `rule: nothing phones home — no telemetry, no update checks, no network unless the spec grants it.` · `rule: license and version fields change only by my explicit act.`

**T5 · Priorities** *(family default; per-campaign rider for the rest)* — when goods conflict and nothing ranks them. Ask: Speed vs. thoroughness, which yields? Coverage vs. shipping? What wins in c2, a production-shaped regeneration — and what does it displace? What's worth a failed pass; what isn't?
*Example (family):* `lean: when in doubt, thoroughness over speed — an extra pass is cheaper than a wrong calcified surface.`

**T6 · Trajectory** *(family)* — where this is going, so near choices bend toward far goals. Already seeded: publishable-by-construction, composition-over-coupling, custody-over-deletion. Ask: What else do I know about the destination that agents can't infer? Parallel-by-containment as the end-state? The someday-public posture shaping naming and README quality *now*? Windows/containment/deferred features — anything near-term work shouldn't foreclose?

## 4 · Writing entries that work

- **Phrase so divergence is detectable.** The advocate checks entries; "make it good" checks nothing. Bad: `lean: keep it simple.` Good: `lean: prefer one obvious type over a trait hierarchy until a second implementor actually exists.`
- **One thought per entry.** Compound entries get half-followed and the trace can't say which half.
- **Date every line** *(YYYY-MM-DD)*; append-only — supersede by new entry, never edit the old.
- **Don't front-load.** Write the dozen you already feel strongly about. The system generates the rest of your list: every trace that reads `none-applicable` and every advocate **intent-gap** finding is literally "xor, opinion wanted here." Answering those beats guessing today.

## 5 · The payoff loop (why one line is worth it)

Kickoff cites your files → a silence resolves *along your line* instead of maximally-conservative → the trace records followed/diverged-because → the advocate flags where you were silent but probably care → the sweep promotes winners into real basis and strikes losers. The register stays small because it keeps graduating — it's not a document you maintain, it's a conversation the system keeps starting for you.

## 6 · Coffee questionnaire — the starter dozen

T1: dependency appetite? · unsafe stance? · abstraction timing? · test density beyond judges?
T3: narrower-or-capable? · your definition of "conservative"? · halt-vs-guess threshold?
T4: your two or three reject-on-sight absolutes?
T5: what wins in c2 — and what's worth a failed pass?
T2: success-output volume? · error shape?
T6: one thing the destination knows that today's work shouldn't foreclose?

Answer any subset in plain speech — in chat is fine; the channel turns it into proposal `001`.
