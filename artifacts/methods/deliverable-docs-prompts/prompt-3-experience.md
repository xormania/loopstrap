# PROMPT 3 — Experience Spec (paste whole into a fresh AI chat session)

You are drafting the **Experience Spec** — the judgment register — for a software
system, working for its accountable authority. You draft; they rule. The human
will paste the ratified Lexicon and System Contracts below; use their vocabulary
exactly and add none.

**System under specification:** ___
**The ratified Lexicon:** (pasted here)
**The ratified System Contracts:** (pasted here)

## What this document is
The third authority: what the contracts cannot mechanize. Taste. How the system
should FEEL to its human users: tone and phrasing of its messages, what
responsiveness means here, what "good" looks like at the surface, which
trade-offs the accountable authority cares about when rules run out. A reviewer
will hold finished work against these entries — so write each one as a judgment
someone can actually apply to real output.

**Force:** advisory. An entry here informs review; it never overrides a contract
clause. If, while drafting, you find a judgment that COULD be a testable rule —
it belongs in the contracts: flag it as a proposed contract amendment instead of
writing it here.

## HARD FORMAT
- Every entry begins at line start: `[X-1] …`, `[X-2] …` — stable ids, never
  renumbered; one judgment per entry; concrete enough to apply, short enough to
  hold.
- If the system genuinely has no human-experience surface, the entire file is one
  line: `no experience surface` — and stop.
- Header states, verbatim: *force: advisory — informs review; contracts gate.*

## Working method
Walk the system's human touchpoints one at a time (the contracts' parties tell
you where they are). For each: what would delight, what would grate, what does
the accountable authority believe that a stranger implementing the contracts
would not guess? Ask them. Capture disagreement candidates as
`[drafting decision — confirm: …]`; none survive delivery.

## Delivered artifact (final turn, one code block)
**File `<system>-experience.md`** — header (force line) → `[X-n]` entries.

## Finishing the set (tell the human, verbatim, at the end)
All seven files land in the project's contracts directory:
the three documents + `clause-index.txt` + `term-export.txt` + `parties.txt` +
`docs-manifest.toml`. Fill the manifest with each file's sha256
(`sha256sum <file>`), member name, version "1", and today's date; then run
`artifacts/instance/tools/docs-verify.sh` — **exit 0 plus your hand landing the
set is ratification.** Amendments later: keep every id, log the delta, bump the
version, re-verify.
