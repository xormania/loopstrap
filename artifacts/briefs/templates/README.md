# Briefs — the Conductor <-> generator interface

The working agreement (D24 as amended by D34): **the Conductor plans and authors briefs; the generator implements.** The brief file is
the entire interface between them — nothing scope-shaped travels any other way.

- Fable (planner role) authors work-unit briefs from the ratified corpus into
  artifacts/briefs/<unit-id>.md using implement-unit.md as the template. Contract clauses
  are QUOTED VERBATIM into the brief (sandwich rule: focused slices, never paraphrased).
- xor issues the brief: launches Codex cwd-pinned in repos/<member>/ pointing at the brief.
- Codex executes exactly the brief's scope. Its claims report lands as the PR BODY
  (never a committed file — reports are review-surface material, not tree material).
- Commit trailers (Unit:/Pass:/Brief:/Config:) + run records join everything after the fact.
- Steward sweep template: to author with the instance (§3.5).
