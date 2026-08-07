# Development Process Method

**Status.** Standalone, project-neutral method document. Captures the methodology for specifying a development process as the third authoritative document of a contract-governed project: the document that carries every artifact and every change from draft through ratification, build, commissioning, and operation to archive. Everything here is method; nothing is project-specific.

**Intended use.** Hand-off material for standing up gated, agent-executed development — including continuous integration and commissioning — under a ratified lexicon and contract set, for a living design system whose lifecycle loop never terminates.

**Companions.** The *Collision-Resistant Lexicon Method* covers the lexicon; the *System Design Contract Method* covers the contract set. This method assumes both documents exist or are built in tandem. The three methods produce a project's three authoritative documents under one authority order: accountable-authority corrections → lexicon → ratified contract set → process document → process records.

---

## 1. Stance

A project's development process is specified as a **process document**: the third authoritative document, governing how artifacts and code move through a perpetual loop — draft → review → fix → ratify → build → conformance → commission → operate → amend → archive. In a living design system the loop never terminates: ratification is not an endpoint, and every amendment re-enters it.

The purpose is plain: every lifecycle transition passes a gate, is performed by a recorded act, and is reconstructable from records. From the process document alone, a reader must be able to answer: through which gates a given change must pass; which checks each gate runs and which findings block passage; which recorded act moves a change between stages and which authority performs it; and, for any live or archived state, which records reconstruct how it came to be. Any lifecycle transition the document leaves ungated, or gated without a recorded act, is a defect.

The process document holds process authority only. It defines no vocabulary and decides no system semantics: it enforces the lexicon and the contract set; it never decides design. It also lives entirely on the design-time side of the design-time / run-time boundary: it governs how the system is developed and commissioned, and it performs no run-time acts. A process rule that would bend a contract, or a pipeline convenience that would blur a term, is resolved upward by amendment to the governing document — never sideways by local workaround.

## 2. Position among the authoritative documents

- **Authority order.** Accountable-authority corrections → lexicon → ratified contract set → process document → process records. Conflicts resolve upward, always.
- **Process acts are contracted upstream.** The acts this document executes — commission, superseding commission, decommission, archive, the commission license (the accountable authority's recorded decision licensing a commission-family act), and any others the project reserves — are privileged acts: each is contracted in the contract set, with its authority in the component registry named by the ⟨act⟩ authority pattern (the commission authority, the archive authority), exactly one reserved verb, subject-locked. This method assumes those contracts exist or are drafted in tandem; it governs their execution, never their meaning.
- **The process document is itself an artifact.** Lexicon-conformant, gated through its own cycle, ratified by the accountable authority, changed only by its single amendment path, covered by the divergence register and the absorption sweep, never forked.
- **Records are the lowest tier.** Process records evidence what happened; they never define what should happen.

## 3. Vocabulary precondition

The process domain carries the project's highest-collision vocabulary. Deploy, release, publish, ship, commit, build, merge, rollback, version, environment, archive: these words pair the strongest outside priors — boundary fusion ("release"), authority relocation ("the pipeline committed") — with acute meta-collision, because to an LLM coding agent they are first-person operational verbs. Therefore: the lexicon dispositions the process-act family — through its normal admission test, with entries, rankings, and bans; in practice nearly every member ends banned-with-replacement, and the reserved acts are fresh verbs (commission, decommission) admitted on their aligned dominant priors — before or in tandem with the drafting of this document. No process document is drafted in undispositioned vocabulary.

## 4. The two coupled loops

The lifecycle runs as two loops joined at ratification:

- **The artifact loop** — draft → review (material issues only) → fix → ratify — carries documents: contracts, subsystem designs, prompts, this document itself. It is the gate cycle of the contract method, operationalized here.
- **The system loop** — build → conformance → commission → operate — carries the implemented system. It consumes only ratified artifacts.
- **Amendment** re-enters the artifact loop; **archive** receives superseded artifacts and decision-time evidence continuously from both loops.

Every stage transition passes through a gate — the gate form (§5) is the only transition mechanism — and commits by a recorded act of a named authority. There are no silent transitions anywhere in either loop.

## 5. Gates

A **gate** is a named checkpoint declaring, in fixed order: its entry criteria; the checks it runs; the finding tiers those checks can raise; the authority whose recorded act passes it; and the records it emits.

- **Outcomes follow the failure doctrine.** A malformed submission to a gate is a rejection — nothing advances, the gate keeps operating. A well-formed submission the gate authority declines is a denial — a successful execution, recorded, never an error. A gate-infrastructure failure is an abort — nothing advances, no partial records. On verification paths, an item the checks cannot process is a finding — never skipped, never quarantined.
- **No bypass.** Urgency creates no exception. If the project needs an expedited path, that path is itself a ratified gate sequence with its own records — never an unrecorded shortcut.
- **The mandatory minimum.** Every project defines at least: a **ratification gate** on artifacts (no unresolved status markers survive it); a **vocabulary conformance gate** running the lexicon's conformance checker with its tiered findings — hard-fail findings block, judgment findings are adjudicated and the adjudications recorded; an **implementation conformance gate** whose checks are derived from the contract set's preconditions, postconditions, and invariants — the contract set functioning as the enforcement surface it declares itself to be; and a **commission gate** verifying the relevant commission-family contract's preconditions, including the recorded commission license.
- **Portability.** In prompts and portable snippets, gates and findings travel in qualified form — process gate, verification finding — per the lexicon's register phrasing.

## 6. The pipeline: decide, enforce, assemble inputs

The decide/enforce/assemble split governs the pipeline itself:

- **The decider** — per the commission-license contract; whether the accountable authority decides per-change or through a ratified standing grant is a registry decision, carried as a drafting decision until ratified — decides over supplied inputs only: gate outcomes, conformance findings, receipts.
- **The enforcer** — the act's authority (for commission-family acts, the commission authority) — executes decisions exactly. A denied commission, or a commission with unsatisfied preconditions, simply does not happen.
- **The input assembler** — the pipeline — assembles decision inputs, runs checks, and records receipts. It never decides, and it is never the grammatical subject of a reserved process verb. "The pipeline commissioned the change" is this document's canonical violation.

Automation may verify preconditions and execute ratified outcomes; it may never originate a standing change.

## 7. Commission doctrine

- **Commission is the sole design-to-run crossing.** Run-time live standing changes only by a commission-family act — the one place whose effect crosses the design-time / run-time boundary. Every such change commits through its contract and is recorded through the recording path. No silent commissions; no unrecorded manual intervention — an out-of-band change to live standing is a boundary-crossing violation and a silent transition, the completeness defect.
- **A blocked commission is a denial.** Recorded as a successful policy outcome; never routed through error handling.
- **Three distinct acts.** A **commission** confers live standing; a **superseding commission** replaces what is live; a **decommission** removes live standing without replacement. None is an erasure — history retains every act — and none ever implies another, though two may commit atomically. The triple instantiates the contract method's distinct-acts doctrine: confer, replace across a boundary, remove — each with its own act, authority, and vocabulary.
- **Migration is split.** The process document governs execution — order, windows, sequencing. Migration meaning — compatibility invariants, deprecating an act, changing recorded semantics — is contract amendment, ratified before execution begins.
- **Live is defined upstream.** What counts as live standing is a contract-set definition; the process document schedules and executes transitions of that standing, and never redefines it.
- **Non-live targets.** Transitions of non-live run-time targets (staging-class targets) are recorded process acts with their own reserved vocabulary — never commission; whether any such target carries standing is a contract-set definition.

## 8. Operate doctrine

Operation is a governed stage, not an untracked afterlife. Run time crosses back into design time as recorded evidence only — findings, divergence detections, binding-trigger events — which may initiate the amendment path; nothing at run time alters a design-time artifact directly.

- **Binding triggers are monitored.** Every recorded binding trigger — deferred binding levels, conditional deferrals, contested-call reversal conditions — has a named monitor in the process. On trigger, the process function is detection and initiation: raise the parent amendment through the parent document's path. A binding trigger recorded but unmonitored is how a deferred level binds silently in production.
- **Divergence feeds the forensic instrument.** Runtime divergence detection routes to the verification/replay contract; blame is adjudicated from recorded evidence, never from live component state.
- **Incidents produce findings.** Anything replay or re-verification cannot process is a first-class finding into the artifact loop — never skipped, never quarantined.

## 9. Absorption sweep, operationalized

The process document operates the machinery of the absorption sweep:

- On any amendment to an authoritative document, it opens an absorption sweep: conformance and consistency checks over dependents, most-authoritative-first — the contract set first for lexicon amendments, then this document, then downstream artifacts — with all derived digests and crib materials regenerated.
- **Checker regeneration is part of the sweep.** The vocabulary checker's rules derive from the lexicon; the implementation-conformance checks derive from the contract set. An amendment to either regenerates its derived checks — a checker that lags its source is a fork in disguise.
- **Sweeps close.** Absorption is tracked in process records to completion; an amendment is not closed until its absorption sweep is.

## 10. Records

The process-records tier holds: gate outcomes; adjudications of judgment-tier findings; commission-license, commission, superseding-commission, decommission, and archive act records; receipts from the input assembler; absorption tracking; divergence resolutions.

- **Records are evidence.** They are append-only and attributable, they commit through the designated recording path, they are held by a named custodian in the component registry, and they serve the blame clauses of the contract set.
- **Evidence clearance applies.** Records that outlive or travel beyond their subject are safe to hold at lower trust — commitment-based, plaintext-free, disclosure-scoped. Leaking a record never leaks its subject.
- **Records are the lowest authority tier.** They evidence what happened; they never define what should.

## 11. Archive doctrine

The archive is evidence custody, not cold storage.

- **A named custodian** — the archive authority — holds decision-time evidence, the policy identity in force at each decision, and every superseded ratified artifact.
- **Custody properties.** Holdings are retrievable, immutable, and attributable. Superseded artifacts are archived, never deleted and never live: this is how never-fork coexists with history — exactly one live version, all predecessors in custody.
- **Historical verification depends on it.** "History is verified, not re-judged" is executable only while decision-time inputs and policy identity remain reconstructable from custody.
- **Retention is ratified.** Any retention limit is a decision ratified by the accountable authority with recorded rationale; a record expiring silently is a silent transition.
- **Evidence clearance applies to the archive's holdings in full.**

## 12. Agent execution discipline

- **Execution containment.** Where agent-executed work is partitioned into units of custody — repositories, workspaces — each partition is a **decision-containment cell**: the blast radius of one executing agent. Interior decisions never escalate implicitly; capabilities cross cell walls only as ratified interfaces referenced at pinned revisions; the sole path by which a cell-interior decision becomes standing law is the accountable authority's recorded dispositional act. Concurrency across cells is licensed by containment itself — bounded only by shared-state isolation in the execution environment and by each cell's ratified basis existing — and a family-wide ruling on cell interiors is justified only where boundary construction demands it, never by divergence-prevention alone. Where one cell's interior *is* the shared interface, containment cannot hold there by definition: that cell is built first, alone, and its output is dispositioned before any consumer binds to it.
- **Agents are clients.** They draft, build, propose, and submit through the same gates as any party. Their statements — build results, validation outputs, declared inputs — enter as recorded untrusted claims; nothing an agent produces changes standing without the designated authority's recorded act.
- **Work units stay chunked.** One work unit equals one gate stage of one artifact, or one execution of one contracted process act. Auditable units; no scope creep inside a stage.
- **Prompts are assembled, not adapted.** Agent-facing instructions are built from the lexicon's pasteable layers verbatim and delivered in the sandwich pattern: first-read anchors at the head; the task-local digest and the term cards for the reserved terms actually in use placed adjacent to the task at the end. Focused slices only — what the work unit needs, never the whole doctrine, never paraphrased.
- **Registers hold.** Design conversation stays plain; everything an agent consumes or produces as an artifact conforms.

## 13. Markers and deferrals

The marker system of the contract method applies unchanged: `[drafting decision — confirm]` for choices awaiting the accountable authority — authority placements for process acts characteristically enter this way — `[embedded resolution]` for inferences from ratified material, `[ratified]` once confirmed. No unresolved marker survives a ratification gate. Deferred process elements carry destination, authority, and trigger; conditional deferrals carry binding triggers, which §8 obliges the process to monitor.

## 14. Construction order

1. **Disposition the process vocabulary.** The lexicon's admission test and sweep run on the process-act family first (§3).
2. **Contract the process acts.** Place the process authorities in the component registry per the ⟨act⟩ authority pattern and draft the act-bearing contracts — commission, superseding commission, decommission, archive, commission license — in the contract set, placements carried as drafting decisions until ratified.
3. **Draft the doctrine:** the two loops, the gate form, failure-doctrine outcomes, the pipeline split, commission, operate, records, and archive doctrine.
4. **Enumerate the gates.** Each with entry criteria, checks, finding tiers, authority, and records; map every contracted process act to exactly one executing gate sequence.
5. **Mechanize.** Bind the vocabulary checker and the contract-derived implementation checks into the gates; establish regeneration of each on amendment to its source.
6. **Establish records and custody.** The records tier, the recording path, the archive paths, the custodian.
7. **Run the process closure check** (§15).
8. **Gate the document itself:** review → fix → ratify, one stage per work unit.

## 15. Closure check

- Every stage transition in both loops maps to exactly one gate and one recorded act with a named authority.
- Every contracted process act maps to exactly one gate sequence; every gate states its checks, authority, and records.
- Every record type has a custodian; every binding trigger has a monitor.
- Gates deliberately absent are named absent by design, with the deferral noted.
- Missing coverage, double coverage, an unmonitored binding trigger, or an ungated transition is a process defect.

## 16. Observed and anticipated failure modes

- Authority relocated onto automation — "the pipeline commissioned the change."
- Unrecorded manual intervention on live standing; silent commissions.
- A run-time occurrence altering a design-time artifact outside the amendment path — the reverse boundary crossing.
- Denial at a gate handled as an error path.
- A superseding commission or decommission treated as erasure — history rewritten instead of extended.
- Gates skipped under urgency; an "emergency" path that was never ratified.
- Checker drift — vocabulary or implementation checks not regenerated after their source amended.
- Absorption sweeps opened and never closed.
- Archive as deletion, or as mutable storage; retention expiring records silently.
- Binding triggers recorded but unmonitored — a deferred level binding silently in production.
- Process workarounds patching design flaws sideways instead of amendments routing upward.
- Agent output treated as a standing change without the authority's recorded act.

---

Everything above is method. Bind it to a project by dispositioning the process vocabulary, contracting the process acts, enumerating the gates and records, establishing custody, and gating the document itself to ratification. From that point the loop does not close — it cycles: the process document is the instrument by which a living design system remains one system.
