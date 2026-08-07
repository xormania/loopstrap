# LanguageServerFixture — Experience Spec

**Status:** DRAFT 1. Not ratified. 2026-07-30 01:38 UTC.
**Authority:** xor (accountable authority). Advisory-to-reviewer force; authored under the lexicon and system contracts.

Judgments the contracts cannot mechanize. The reviewer holds the work against these.

[X-1] A rejection diagnostic reads like a repair instruction: it names the offending input, the exact field or value, and the rule it violates, so the reader fixes the input without opening the fixture server's source.

[X-2] The transcript reads as a story of the server lifetime: one event per line, a stable field order, greppable identifiers, no wrapped or interleaved lines — a human should locate the scenario trigger in seconds.

[X-3] An adjudicated outcome leads with what matters: its side and its pinned identity first, the comparison detail after, so a reader never mistakes a self-check outcome for a subject outcome at a glance.

[X-4] Divergence detail earns its length: when an outcome is non-conforming, the emitted text shows the corpus-baseline value and the observed value adjacently, in wire positions, small enough to read whole.

[X-5] Every emitted message, diagnostic, and outcome uses the lexicon's vocabulary exactly; a reader who knows the lexicon never meets a synonym, and a reader who does not still meets one name per concept.

[X-6] The fixture corpus is pleasant to study: small files, meaningful identifiers including the non-ASCII ones, and structure a newcomer can hold in their head — it is the worked example of the fixture language, not a stress pile.

---

*LanguageServerFixture · Experience Spec · DRAFT 1 · 2026-07-30 01:38 UTC · not ratified*
