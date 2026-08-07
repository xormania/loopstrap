# Specification CI Method

**Status.** Standalone, project-neutral method document. "Specification CI" is a working label, not a ratified name. Captures the methodology for continuous, cumulative validation of a project's authoritative documents — lexicon, contract set, process document — by stochastic probe generation judged against deterministic oracles.

**Revision.** v2 (2026-07-11): amended after an independent prior-art research round and a primary-source citation-verification pass. Every empirical claim below carries a verified source.

**Intended use.** Hand-off material for instantiating this capability on any project governed by the companion methods. Everything here is method; nothing is project-specific. Where an example appears, it illustrates a pattern, never a requirement.

**Companions.** Presupposes artifacts produced by the *Collision-Resistant Lexicon Method*, the *System Design Contract Method*, and the *Development Process Method*: a ratified document set committed to decidability, a mechanical conformance checker, a gated amendment path, and a failure-outcome taxonomy. The oracle must exist before the harness.

---

## 1. Stance

The authoritative documents are placed under continuous integration: they are the system under test, every amendment is a change event, and a defined suite runs on change. The inversion that makes this new: **model instances are the test harness and the documents are what is being tested.** Conventional evaluation points models at fixed material to grade the model; this method points models at fixed documents to grade the documents.

One law is load-bearing throughout: **the stochastic side only generates; the deterministic side only judges.** Probes, phrasings, scenarios, and interpretations may be sampled; verdicts are computed from the ratified documents and mechanical rules. A stochastic judge is a defect, not a variant.

The purpose is cumulativity. Without this method, a design's validation lives in whoever last walked its arguments — re-derived from memory, session by session, and lost between them. Under it, every validation ever performed is pinned, replayable, and re-run on every change.

## 2. Reference tradition

Disciplined assembly of existing practice; no new theory:

- **Property-based testing** (QuickCheck lineage) — random inputs judged by invariant assertions.
- **Fuzz-corpus discipline** — an interesting random failure is frozen into the corpus and becomes a deterministic regression test forever.
- **Mutation testing** — score a suite by injecting known defects and measuring what it catches.
- **Statistical model checking** — properties verified as rates over sampled runs where exhaustive checking is unavailable.
- **Metamorphic testing** — verification via relations that must hold across transformed inputs where direct oracles are partial; the register axis (§5) is one such relation.
- **N-version programming** (Knight–Leveson 1986; replicated with LLM coding agents at scale, 2026) — independent implementations of one specification fail in correlated ways; the governing caution for the interpreter axis (§5).
- **CI matrix builds** — one artifact validated across an axis product, on every change, gating merge.
- **Model evaluation harnesses** — inverted, per §1.

The contribution is the assembly: the system under test is a document set, the input generator is a language model, and the oracle is the document set's own ratified decision function.

## 3. Preconditions

The method presupposes, and does not substitute for:

1. **A decidability-committed document set.** The contract method already requires that anything undecidable at a document's own level of abstraction is either explicitly deferred or a defect. That commitment is what makes the documents an oracle.
2. **A mechanical conformance checker** with tiered severities, generated from or maintained against the ratified documents.
3. **A gated amendment path.** Suite verdicts bind at this gate; expected-verdict changes pass through it (§8).
4. **A failure-outcome taxonomy** (rejection / denial / abort / finding) into which suite verdicts map (§7).

## 4. Test kinds

### 4.1 Deterministic fixtures and workflows

The first suite is extracted, not written. A mature lexicon already contains it as prose: every *violation → correct form* pair, every collision-map row (dangerous term, expected misreading, required distinction), every anti-definition is a unit fixture — input, expected failure, expected pass. Contract clauses contribute scenario fixtures: preconditions that must reject, denials that must not be failures, invariants that must hold across any act sequence the documents permit. Fixtures are **generated from the ratified documents by script, never hand-copied**; a hand-copied fixture is drift waiting to be cited.

Deterministic workflows run without any model in the loop: conformance lint, fixture execution, marker checks (no unresolved decision marker survives a gate), cross-document consistency (§5), and pinned-probe replay (§4.3).

### 4.2 Stochastic unit tests

Anatomy: **one seed → N sampled generations → one deterministic assertion.** Simplicity is the design, not a concession — a unit probes one term, one boundary, or one act at a time.

Illustrative patterns:

- *Status-wash probe.* Seed: a few sentences about delivering a transformed artifact to an outsider. Assertion: every sample either carries the required status rider or trips the checker's banned tier. Catches vocabulary that lets processing imply permission.
- *Subject-lock probe.* Seed: one sentence describing plumbing completing work that enters the governed system. Assertion: no reserved verb appears with a non-owning subject.
- *Convergence probe.* Seed: a boundary question posed to a cross-family panel of interpreters given only the ratified documents. Assertion: chance-corrected agreement (Krippendorff's alpha) on the documented answer against a declared threshold — read under the §5 interpreter-axis rules: disagreement indicts the documents; agreement alone certifies little.

Stochastic verdicts are **rates, not booleans.** Each test declares its threshold, and threshold policy is owned like flaky-test policy in conventional CI: recorded, owner-set, never silently loosened. Sample counts are bounded sequentially rather than fixed: Wald's SPRT — already applied to LLM response sampling (ConSol, 2025) — stops sampling the moment the evidence crosses a decision boundary, holding declared error rates while minimizing cost.

### 4.3 Pinning — the corpus lifecycle

Any sampled probe that fails interestingly — reveals an undecidable area, a cross-document divergence, an absurd verdict, a convergence collapse — is **frozen verbatim into the pinned corpus** with its expected verdict. Stochastic generation grows the suite; deterministic replay executes it. The corpus is append-only in practice: pins are retired only through the amendment gate, with the retirement recorded. Pins are stored whole: no minimization pass exists — shrinking a natural-language failing case without destroying its semantic intent is an open problem — so a pin is the verbatim probe, never a reduced one.

## 5. The matrix

One probe, validated across an axis product. The axes:

- **Document-layer axis.** The same term or scenario judged against each authoritative layer — lexicon, contract set, process document — with verdicts compared. Catches the canonical drift failure: a word banned in one layer surviving in another, an invariant restated divergently downstream.
- **Contract axis.** A scenario decided from each contract that touches it; disagreement between contracts on one scenario is a finding.
- **Version axis.** The pinned corpus replayed against document version N and N+1 on every amendment; verdict deltas are the amendment's measured blast radius, and the absorption sweep is not closed until the matrix is green.
- **Interpreter axis.** The same probe across a panel of interpreters drawn from disjoint model families — the environment matrix where the environment is the reader's priors. The evidence forces a reframe: this axis is a **defect detector, never a quality certifier.** Independent implementations of one specification fail in correlated ways (Knight–Leveson 1986; replicated with LLM coding agents in 2026 — coincident failures roughly 3.7× the independence prediction), because interpreters share training priors: unanimous agreement may be shared prior, not clarity. So **divergence is a strong signal** (the documents or the probe are defective) while **convergence is weak evidence.** Two instruments fall out: the disagreement rate flags ambiguity, and the *clustering of coincident wrong verdicts localizes it* — the replication traced common-mode failures to exactly the specification's hard and ambiguous regions. Agreement is measured chance-corrected (Krippendorff's alpha, which tolerates missing verdicts), never as raw percent; panel family-composition and residual correlation are reported with every run.
- **Register axis.** The same scenario phrased plainly and phrased conformantly; both must decide alike. Catches rules that only work when the reader already speaks the lexicon. This is a metamorphic relation — verdict invariance under meaning-preserving rephrasing — and inherits that discipline: the relation, not any individual verdict, is the oracle.

## 6. The pipeline

Trigger: any diff to an authoritative document, and any candidate artifact at a gate.

Stages, in order: conformance lint → fixture units → pinned-corpus replay → cross-layer and version matrix → stochastic units (budgeted) → report.

Binding: **a red suite blocks the ratification gate.** The absorption sweep acquires teeth — an amendment is not closed until dependents regenerate and the matrix passes. Expedited paths, if any, are themselves ratified gates, never bypasses.

**Reference composition.** Verified against current tooling, no single product satisfies all four infrastructure constraints, so the pipeline composes: a CI matrix runner for triggering and orchestration; a file-first eval harness confined strictly to generation (assertions live outside it); a policy-as-code engine as the file-resident deterministic oracle; and approval pauses implemented as native version-control review gates rather than engine-resident waits. The last choice also dissolves the apparent conflict between stateless engines and human-in-the-loop pauses — the ratification gate is a review approval anyway. Every layer stays individually swappable.

## 7. Verdicts

Suite outcomes map into the failure taxonomy rather than inventing a parallel one:

- **Pass** — the documents decide the probe, and as expected.
- **Rejection** — malformed probe; nothing scored; the probe is fixed or discarded.
- **Finding** — the load-bearing class: an *undecidable* probe (the documents cannot decide it at their own level and no deferral covers it), a cross-layer divergence, a convergence collapse, or a decided-but-absurd verdict. Findings are never skipped and never silently quarantined; they route to the owner as design work.
- **Regression** — a previously pinned expectation now violated. Distinguish *drift* (unintended; fix the documents) from *intended change* (the amendment meant it; update the expectation through the gate, §8).

Denial-analogues — probes the documents decide as "no" — are passes when "no" is the expectation. A prohibition working is a success.

Undecidability is always **derived from verdict behavior** — extraction failure, cross-layer divergence, panel disagreement — never taken from an interpreter's self-report. The evidence is bilateral: generating unprompted, models silently collapse ambiguity into a single assumption instead of flagging it; asked explicitly to judge ambiguity, they over-detect, misclassifying clear material at high rates (precision near 50% in benchmark studies). Self-reports fail in both directions; only behavior counts.

## 8. Amendment interaction

Amendments legitimately flip expected verdicts. Two rules keep the suite honest without ossifying the documents:

1. **Expectations change only through the amendment gate.** The diff that amends a document carries the expectation updates it implies; both ratify together. No test is edited to green outside the gate. And the gate is built to resist rubber-stamping — the documented death of snapshot and BDD suites, where one-flag updates get approved blind and regressions become baselines. An expectation update therefore ships as its own reviewable artifact: the semantic diff of verdict changes, itemized, with per-item disposition required. Bulk approval is not an operation the gate offers.
2. **Derived material is regenerated, never patched.** Fixtures, checker rules, and compiled digests regenerate from the ratified documents as part of every sweep. Hand-maintained derivatives are the drift channel this method exists to close.

## 9. Mutation scoring

The suite itself is tested. The companion methods' **observed-failure-modes catalogs are the mutation operator list**: inject a locally restated invariant that drifts, a synonym rotation on a reserved operation, a denial handled as an error, a coin in a designated no-vocabulary zone, a weakened postcondition in a child — into a copy of the documents — and run the suite. Every uncaught mutation is a hole, and the kill rate is the suite's quality score. One screen is mandatory first: **equivalent-mutant detection.** Natural-language mutation readily produces semantically identical rephrasings, and counting an unkilled equivalent as a hole corrupts the score. A mutant enters the kill-rate denominator only after screening for semantic distinctness, and the screen itself is versioned like any fixture. Hard-won failure lists become executable.

## 10. Metrics

- **Decidability coverage** — fraction of sampled probes the document set decides at its own level (deferred areas counted separately, not as failures).
- **Disagreement and coincidence maps** — interpreter-axis outputs per term and boundary: chance-corrected agreement (Krippendorff's alpha) with panel family-composition reported, plus the clustering of coincident wrong verdicts as an ambiguity-localization map. Divergence indicts; convergence alone certifies nothing (§5).
- **Mutation kill rate** — §9.
- **Amendment blast radius** — verdict deltas per amendment on the version axis.
- **Finding inventory** — open undecidable probes; the design backlog, measured.

## 11. What this method is not

- Not implementation testing; the system under test is the specification corpus. Implementation conformance is a separate, later layer that may reuse the fixtures.
- Not model evaluation; interpreter scores grade the documents' communicability, never the models.
- Not a substitute for review or ratification; the suite gates, humans ratify. A green matrix is a precondition of judgment, not a replacement for it.
- Not a measure of design *worth*. It measures soundness, decidability, consistency, and communicability; whether the design is worth building stays a human question.

## 12. Adoption order

1. Version the authoritative documents; wire the conformance checker as the lint stage.
2. Extract fixtures from the ratified lexicon and contracts by script; run them; fix what extraction alone reveals.
3. Pin every finding already discovered by hand as the corpus's founding entries.
4. Stand up the document-layer and version axes — boolean, model-free, immediately decisive.
5. Add stochastic units with recorded thresholds; add the interpreter axis.
6. Score the suite by mutation; close the holes.
7. Bind the suite to the amendment gate; from then on, the sweep closes only green.

## 13. Observed failure modes

- A stochastic judge — sampled verdicts, or a model grading its own generations. The §1 law exists because this fails silently, and measurably: large-scale judge evaluations show chance-corrected agreement running 33–41 points below raw agreement, systematic position bias, and the consistency–bias paradox — test–retest reliability above 0.99 coexisting with severe position bias, because stability of outputs is not correctness of the decision process. No reliability metric rescues a stochastic judge.
- Ossification — expectations frozen so hard that legitimate amendments fight the suite; prevented by §8's gate-coupled updates.
- Hand-drifted fixtures — derivatives edited instead of regenerated; the drifted copy gets cited.
- Toolchain rot — rules generated from a growing vocabulary overlap combinatorially until false positives become nagware and humans bypass the check; the documented production killer of vocabulary-derived linting. Generated rule sets therefore carry a precision budget: false-positive rate is tracked against a threshold, and rule generation is tuned to it.
- Threshold decay — convergence thresholds loosened quietly until the axis measures nothing.
- Prompt-shaped convergence — seeds engineered until interpreters agree, grading the seed instead of the documents. Seeds are versioned and reviewed like any fixture.
- Green-worship — treating a passing matrix as design validation. §11 is the boundary: the suite proves the documents decide; it never proves the decisions are wise.

---

Everything above is method. Bind it to a project by wiring its conformance checker, extracting its fixtures, pinning its known findings, standing up the matrix, and coupling the suite to its amendment gate — in that order.
