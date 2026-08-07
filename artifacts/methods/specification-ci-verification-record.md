# Specification CI — Citation Verification Record

**Status.** Adjudication register, project-neutral. Companion to `specification-ci-method.md` (v2): every empirical claim in that document traces to an entry here. Produced 2026-07-11 by verifying two independent research dossiers against primary sources via web retrieval; the dossiers were treated as claims throughout, never as authority. Those dossiers were working inputs only: this record supersedes them on every citation, and they do not travel with the packet. Verdicts only.

**Verdict classes.** VERIFIED (primary source retrieved and quoted/paraphrased faithfully) · CORRECTED (real source, dossier framing or dating wrong) · STALE (claim contradicted by newer verified evidence) · NOT FOUND (no primary source located — never cite) · PRACTICE-GROUNDED (established practitioner knowledge, plausibility-checked, not primary-verified in this pass).

---

## 1. Verified sources and what they ground

**V1 — Knight & Leveson, IEEE Transactions on Software Engineering, January 1986.** VERIFIED. Twenty-seven independently developed versions of the Launch Interceptor Program specification, one million test inputs; coincident failures far exceeded the independence assumption. Grounds: §2 reference tradition (N-version programming); the interpreter-axis caution.

**V2 — "N-Version Programming with Coding Agents," arXiv 2606.20158 (June 2026).** VERIFIED; resolves a dossier conflict — one dossier dated this 2024, which is wrong. Revisits Knight–Leveson with AI coding agents on the original Launch Interceptor specification: 48 admitted implementations, 1,000,000 randomized inputs, 429 coincident-failure cases where the independence model predicts 115.36 (≈3.7×). Common-mode failures trace to regions where the specification is particularly hard or ambiguous. Grounds: the §5 interpreter-axis reframe (divergence indicts, convergence certifies nothing) and the coincidence-clustering ambiguity-localization instrument.

**V3 — Bashir, Ferrari, Abbas, Strandberg, Haider, Saadatmand & Bohlin, "Requirements Ambiguity Detection and Explanation with LLMs: An Industrial Study," ICSME 2025 Industry Track (IEEE), pp. 620–631.** VERIFIED with CORRECTION. Three industrial datasets; 20.2% average classification improvement with ten in-context **demonstrations** (10-shot vs 0-shot). One dossier framed this as "injecting a project-specific lexicon" — it is not; lexicon-injection benefit remains an open empirical question. Grounds: LLM ambiguity detection as a viable probe-generation mechanism, nothing more.

**V4 — "Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models," arXiv 2606.19544 (June 2026).** VERIFIED. 21 judges, nine providers, ~541,000 judgments. Kappa deflation: raw agreement overstates chance-corrected discrimination by 33–41 points in all evaluated models. The consistency–bias paradox (§4.7 of the paper, the term is theirs): test–retest reliability above 0.99 coexisting with severe position bias (e.g., 0.992 / 0.192) — output stability is not decision correctness. **STALE correction to both dossiers:** the same study finds verbosity bias reduced to <0.011 across all 21 models, against the 20–40% reported in 2023 literature; do not cite verbosity dominance. Grounds: §1 generator/judge law and the §13 stochastic-judge failure mode.

**V5 — Verga et al., "Replacing Judges with Juries: Evaluating LLM Generations with a Panel of Diverse Models," arXiv 2404.18796 (April 2024).** VERIFIED. A panel of smaller models from disjoint families outperforms a single large judge, exhibits less intra-model bias, and is over seven times less expensive. Grounds: cross-family panel composition — adopted for *generation* diversity only, never for judging.

**V6 — "ConSol: Sequential Probability Ratio Testing to Find Consistent LLM Reasoning Paths Efficiently," arXiv 2503.17587 (March 2025).** VERIFIED. Wald's SPRT calibrated for LLM response distributions: early termination once evidence crosses a decision boundary, Type I error controlled. Grounds: §4.2 sequential sample bounding.

**V7 — Tip, Bell & Schäfer, "LLMorpheus: Mutation Testing using Large Language Models," arXiv 2404.09952; IEEE Transactions on Software Engineering 2025 (DOI 10.1109/TSE.2025.3562025).** VERIFIED. LLM-suggested mutants for source code. Grounds: mutation-by-LLM exists for *code*, which sharpens the claim that prose-specification mutation catalogs are a genuine gap.

**V8 — "SWE-Mutation: Can LLMs Generate Reliable Test Suites in Software Engineering?" arXiv 2605.22175 (May 2026).** VERIFIED. Benchmark evaluating LLM-generated test suites via systematically mutated solutions. Same role as V7.

**V9 — Orchid benchmark, "Assessing the Impact of Requirement Ambiguity on LLM-based Function-Level Code Generation," arXiv 2604.21505.** VERIFIED. When LLMs are explicitly asked to judge ambiguity, precision sits near 50% — clear requirements are frequently misclassified as ambiguous (over-detection); the benchmark's premise is that ambiguous requirements yield divergent generated implementations rather than refusals (silent collapse on the generation side). Grounds: §7's rule that undecidability is derived from verdict behavior, never self-reported — self-reports fail in both directions.

**V10 — Position-bias and inconsistency literature.** VERIFIED in the body via "Judging the Judges: A Systematic Study of Position Bias" (arXiv 2406.07791) and the survey "From Generation to Judgment" (arXiv 2411.16594), among others. Grounds: supporting evidence for §13.

## 2. Not found — never cite

- **"RAITG"** — no primary source located.
- **"Model-Bench" (2024 autoformalization)** — unverified; not located in this pass.
- The exact title **"Bias Mitigation in LLM-as-a-Judge (2025)"** — unverified as named; the underlying bias claims are grounded via V4/V10 instead.

## 3. Practice-grounded (not primary-verified in this pass)

Accepted on established practitioner knowledge, flagged for verification if ever load-bearing beyond current use: Krippendorff's alpha as the multi-rater standard for categorical verdicts with missing data; fuzz-corpus pinning discipline (OSS-Fuzz class); snapshot/BDD rubber-stamping as the documented death mode of expectation suites; toolchain rot (false-positive nagware) as the production failure of vocabulary-generated linting; Amazon's TLA+ experience reports (Newcombe et al., CACM 2015 lineage); metamorphic testing and statistical model checking as established disciplines.

## 4. Method note

The verification pass itself instantiated the method's own structure: two stochastically generated dossiers (same prompt, independent runs) served as the generation side; primary-source retrieval served as the deterministic side; the dossiers' divergences (the V2 date conflict, tooling-score disagreements) were precisely where verification effort was spent. Divergence indicted; it was right to.
