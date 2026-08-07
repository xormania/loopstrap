# System Design Contract Method

**Status.** Standalone, project-neutral method document. Captures the full methodology and accumulated insights for specifying a software system as a hierarchy of design contracts, ratified before implementation. Self-contained as method; binding it to a project pairs it with its companion methods (below).

**Intended use.** Hand-off material for starting contract-first design in a new project. Everything here is method; nothing is project-specific. Where an example appears, it illustrates a pattern, never a requirement.

**Companions.** The abstract-syntactic level of this method is served by a controlled system lexicon. A separate project-neutral document, the *Collision-Resistant Lexicon Method*, covers lexicon construction; this document assumes such a lexicon exists or is built in tandem. A third companion, the *Development Process Method*, covers the process document that enforces the ratified contract set — gates, conformance, build, commissioning, operation, and archive. Process acts (for example commission, superseding commission, decommission, archive, and the commission license) are contracted here, in the contract set, and executed there. The three methods produce a project's three authoritative documents under one authority order: accountable-authority corrections → lexicon → ratified contract set → process document → process records.

---

## 1. Stance

A system is designed as a **top-level contract set**: a small, closed set of contracts among architectural parties, bound together by a tier of global invariants and a body of shared doctrine. The contract set is produced and ratified before implementation and serves as the design basis; subsystem designs refine it; implementation — human or agent — targets it.

The purpose is decidability. From the contract set alone, a reader must be able to answer: which component may perform which operation; what each party owes before an operation and is owed after; where every authority lives; who is at fault when something breaks and which recorded evidence settles it. Anything undecidable at the set's own level of abstraction is either explicitly deferred — with destination, authority, and trigger — or is a defect.

When the implementers include AI agents, the contract set doubles as an enforcement surface: vocabulary is a binding level of the specification (§4, §5), not documentation style.

## 2. Reference tradition

The method is disciplined application of established contract theory one level up — from code interfaces to system architecture:

- **Hoare logic** — preconditions and postconditions as the specification primitive.
- **Meyer, Design by Contract** — client/supplier structure; obligations and benefits; a violated precondition blames the client, a violated postcondition blames the supplier; no defensive redundancy inside a contract's scope.
- **Beugnard et al., four contract levels** — syntactic, behavioral, synchronization, quality of service; used here to declare which levels the top-level set binds and which it defers (§4).
- **Findler–Felleisen blame assignment** — precise blame, generalized here into architectural blame clauses adjudicated by recorded evidence (§7).
- **Behavioral subtyping (Liskov–Wing)** — the refinement rules sub-contracts must obey (§9).

No new theory is asserted. The contribution is the discipline: vocabulary control, evidence-based blame, and closure proofs added because the readers and implementers include agents.

## 3. Contract form

Every top-level contract states, in fixed order:

1. **Parties.** A client and a supplier, each an architectural component named in a component registry. Verification and definitional contracts may instead name one supplier against several sources or consumers. Party names are reserved vocabulary.
2. **Act(s).** The reserved operation(s) this contract holds. Each act appears in exactly one contract (§10).
3. **Preconditions.** Client obligations, each verifiable from the submission and recorded state — never from good faith or live component internals.
4. **Guarantees.** Supplier postconditions: what becomes true, and what is recorded. Every state transition a guarantee produces is recorded through the designated recording contract — no silent transitions.
5. **Contract-local invariants.** Only where genuinely local. Global invariants are cited by identifier, never restated (§6).
6. **Synchronization.** Atomicity and ordering clauses, only where they are doctrine at this level.
7. **Blame and evidence.** Which party is at fault for which violation class, and which recorded evidence adjudicates it.
8. **Markers.** Closed items (settled; may not be reopened) and deferred items (destination, authority, trigger; binding trigger where the deferral is conditional).

## 4. Binding levels

The shared doctrine declares explicitly which specification levels the top-level set binds:

- **Abstract syntactic** — bound. Operation names, party names, and conceptual inputs are the controlled lexicon's reserved vocabulary. Concrete syntactic material — wire formats, encodings, field lists — is deferred to subsystem design.
- **Behavioral** — bound. Preconditions, postconditions, invariants; totality and determinism where stated.
- **Synchronization** — bound where atomicity or ordering is doctrine; otherwise silent.
- **Quality of service** — deferred. Quantitative extra-functional properties (latency, throughput, availability, resource bounds) belong to subsystem design.

Every deferred level carries a **recorded binding trigger** — the event that forces it to bind by parent amendment. The canonical one: QoS binds the moment any top-level guarantee materially depends on a quantitative bound. The binding trigger exists to catch silent binding: without it, a guarantee quietly acquires a dependency on a number nobody ratified.

Declaring what is deliberately unbound is as load-bearing as declaring what is bound.

## 5. Vocabulary as a binding level

The lexicon is authoritative over the contract set. A vocabulary conflict resolves in the lexicon's favor and the contract is amended. Four lexicon rules bind contract prose directly:

- **One reserved term per act.** No synonym rotation for reserved operations. Synonym variety is a virtue in prose and a defect in a specification consumed by agents — every synonym is a fresh chance to import a wrong prior.
- **Subject-locked verbs.** A reserved verb takes only the act's authority as grammatical subject; every other party proposes, claims, requests, or submits. A sentence handing a reserved verb to a non-authority is a violation regardless of intent, even when it describes a caller of the authority.
- **Acts, not adjectives.** No processing adjective ("validated," "verified," "approved") ever changes a status; only a recorded act does. Contracts are written so no sentence lets a reader skip the act.
- **Named authority.** Authority-significant nouns carry their authority in the name, because clauses get copied out of context and must still signal authority placement standing alone.

## 6. Tier 0 — global invariants

A numbered tier of system invariants binds every contract at every level. Three prohibitions protect it: no contract may **weaken** an invariant, **restate it divergently**, or **locally re-derive** it. Restatement is the observed failure mode — paraphrase drifts, and the drifted copy gets cited.

Discipline for the tier itself:

- Contracts cite invariants by identifier only.
- Keep the tier small and orthogonal: each invariant fixes one authority placement or one prohibition. Composite invariants get split.
- The tier is where the **distinct-acts doctrine** lives: operations that outside vocabulary habitually fuses — for example, lowering an item's status, moving it across a boundary, and removing it from the system — each get their own act, authority, and an invariant forbidding any one to imply another, even when two may commit atomically (§13.4).

Where the governed scope includes the development process, the tier also carries the **design-time / run-time boundary**: the separation between developing the design and the designed system in use. Two invariants protect it — run-time live standing changes only by a commission-family act, and no run-time occurrence changes a design-time artifact except through the amendment path. Component-registry entries are marked by side; the failure taxonomy (§7) spans the boundary by explicit declaration; every other straddling word is banned.

## 7. Shared doctrine

Cross-cutting rules are stated once, above the contracts, and bind uniformly. Four are mandatory.

**Failure doctrine.** A uniform outcome taxonomy across the whole set:

1. **Rejection** — a malformed submission or client precondition breach is rejected outright: nothing commits, no state changes, the receiver keeps operating. Totality is achieved by recognize-and-reject, never by defining behavior for garbage.
2. **Denial** — a well-formed request that the decision authority denies is a **successful contract execution**, not a failure: no act proceeds, and the decision is recorded. Conflating denial with failure pollutes error handling with policy outcomes.
3. **Abort** — a supplier failure means the transaction does not commit: there are no partially recorded effects.
4. **Finding** — on verification paths, which commit nothing, an item that replay or re-verification cannot process is a first-class finding — never skipped, never quarantined.

**Fallback rule.** Rescue or retry inside a supplier is permitted under one constraint: it preserves the contract's guarantees — specifically determinism on decision and replay paths. No retry may introduce unrecorded transient inputs into any computation that affects recorded facts or decisions.

**Blame doctrine.** Blame is assigned from recorded evidence only — facts, receipts, commitments — never from live component state. One contract, the verification/replay contract, is designated the **forensic instrument**: its replay, re-verification, and divergence detection serve every blame clause in the set. Live-state blame is unfalsifiable; recorded-evidence blame is decidable after the fact.

**Accountability doctrine.** Authority is placed; accountability is assumed. Authority — the exclusive right to perform a reserved act — is placed in components (and held by the accountable authority for its own acts) through recorded acts. Accountability — where the buck stops — belongs to the **accountable authority** alone: one human, singular, non-delegable, assumed through that human's recorded acts (ratification, correction, the commission license), never held as static standing. No component is ever accountable; a component can carry blame, adjudicated from recorded evidence, but never accountability. Prose that assigns accountability to a component or an agent is a violation of the same class as status laundering.

## 8. Contract kinds

Not every architectural relationship is an act-bearing contract. The working taxonomy:

- **Act-bearing contracts** — hold one or more reserved operations; carry the full clause form.
- **Mechanism contracts** — no act; they fix an interface direction and its guarantees. Canonical pattern: the truth-holding component defines hooks; the mechanism implements them — never the reverse — and validity is never gated on mechanism availability.
- **Read-path contracts** — derived, rebuildable views; non-authoritative; carry an explicit consumer obligation (outputs never on decision paths).
- **Byte/storage-path clause sets** — deliberately thin: a handful of clauses, not a full contract, with a recorded **elevation condition** (promote to a full contract only if lifecycle semantics come to require owned facts).
- **Verification-path contracts** — replay and re-verification; commit nothing; hold the forensic role.
- **Definitional (model) contracts** — a shared identity or type model every other contract's vocabulary references; violations are typing errors, caught in review and by divergence detection where they surface at runtime.

Choosing the thinnest adequate kind is itself a design decision. Over-promoting a byte path to a full contract manufactures authority that should not exist.

## 9. Refinement discipline

Sub-contracts refine top-level contracts under behavioral-subtyping rules:

- A sub-contract **may tighten** its supplier's guarantees.
- It may **never** strengthen preconditions on the other party, weaken a parent postcondition, or weaken, restate divergently, or re-derive a Tier 0 invariant.
- A flaw discovered during subdivision is fixed by **explicit parent amendment before downward work resumes** — never by a compensating workaround in the child. The parent's gate reopens for the amendment; the child waits.

## 10. Coverage and closure check

The contract set ends with a closure check — a deliverable section, not an editorial nicety:

- Every reserved operation maps to exactly one holding contract: the act-to-contract map is enumerated exhaustively.
- Every component in the registry appears as an authority or a party. Components that are **deliberately authority-free** — a pure proposer, a pure decider — are listed as parties only; the check proves the asymmetry is intentional.
- Where the design-time / run-time boundary binds (§6), every registry entry carries its side marker; an unsided entry is a defect.
- Contracts deliberately absent are named as absent by design, with the deferral noted.
- Missing coverage, double coverage, or an unplaced component is a design defect.

## 11. Relation to prior documents

When a contract set supersedes earlier scope or requirements material:

- **Divergence register** (appendix): every deliberate divergence from the prior document, enumerated and resolved with rationale. Divergence is legitimate; silent divergence is not.
- **Absorption map** (appendix): each prior informal invariant or rule mapped, item by item, to the numbered invariant or contract clause that absorbed it. The map is the proof nothing was dropped.
- The authority order among documents is stated once, explicitly: accountable-authority corrections → lexicon → ratified contract set → process document → process records. Ratified artifacts replace superseded drafts; forking is prohibited.

## 12. Markers and deferral discipline

- **Status markers.** Drafts carry `[drafting decision — confirm]` for choices awaiting the accountable authority, `[embedded resolution]` for inferences drawn from already-ratified material, and `[ratified]` once confirmed. No unresolved marker survives a ratification gate.
- **Closed vs deferred.** Closed items may not be reopened. Deferred items always carry a destination (which subsystem design), an authority, and a trigger; conditional deferrals carry recorded binding triggers (§4). Nothing defers into the void.
- **No-coin zones.** Areas where design is deliberately absent get no vocabulary at all: write the placeholder and stop. Premature names harden premature designs — coining a term for an undesigned area is a design act in disguise. Naming gaps are flagged to the accountable authority, never patched with borrowed or improvised terms.

## 13. Doctrine patterns

The accumulated structural insights, generalized. Each earned its place by preventing a real class of drift.

1. **One act, one authority.** Every reserved operation belongs to exactly one contract and one authority. Synonyms and double placement are both defects.
2. **Subject-locked verbs.** The grammar of the specification enforces the authority model (§5).
3. **Acts, not adjectives.** No status ever changes because processing happened; it changes because a recorded act says so.
4. **Atomic yet distinct.** Two semantically distinct facts may commit in one transaction for atomicity; they are always written, recorded, and reasoned about as two facts. Transactional convenience is never semantic merger.
5. **Distinct acts for fusable concepts.** Where outside vocabulary habitually fuses operations, give each its own act, authority, and vocabulary, plus an invariant forbidding one to imply another.
6. **Determinism as the verification anchor.** State determinism and totality — identical recorded inputs yield identical results; termination on any finite input — exactly where later verification depends on reconstruction. Determinism clauses are not quality aspirations; they are what makes historical re-verification possible.
7. **Completeness: no silent transitions.** Every accepted or enforced transition is recorded; recording flows one way into the recording contract.
8. **Decide / enforce / assemble-inputs split.** The decider decides over supplied inputs only and never inspects the underlying content; the enforcer executes outcomes exactly — a denied or obligation-unsatisfied act simply does not happen; the input assembler constructs decision inputs and records receipts but never decides. Collapsing any two of the three is the commonest architectural drift; the contract set names all three parties precisely to keep them apart.
9. **Evidence is lower-clearance than its subject.** Receipts, evidence bundles, and any artifact that outlives or travels beyond its subject must be safe to hold at lower trust: commitment-based, plaintext-free, disclosure-scoped. Design evidence so that leaking the evidence never leaks the subject.
10. **Direction-fixed mechanisms.** The truth-holder defines integrity hooks; mechanisms implement them, never the reverse; validity never depends on mechanism availability. Mechanisms evidence truth; they never gate it.
11. **Claims are recorded, never believed.** Producer statements — declared inputs, validation results, relationship statements — enter as recorded untrusted claims. Recording settles that the claim was made, never its accuracy; no semantic or consistency checking is smuggled into acceptance. A claim gains force only through an explicit, authorized act that consumes it.
12. **Conservative defaults with named recovery.** Safety-relevant propagation over-approximates, computed over what the system itself granted or observed — never over what producers declared. Precision is recovered only through named acts (narrower grants; an explicit authorized lowering), never by trusting declarations. Omission attacks die structurally, not through better auditing of declarations.
13. **Denial is not failure.** Policy outcomes are successful executions (§7).
14. **Authority-free parties are load-bearing.** Making a party contractually present but authority-free is a design statement; the closure check certifies it.
15. **History is verified, not re-judged.** Verification of a past decision reconstructs its inputs deterministically and checks them against the evidence recorded at decision time, under the policy identity then in force. Current policy is never treated as historical truth.

## 14. Adjudication of contested design questions

When a design question is genuinely contested, it is resolved by process, not by deference:

1. Build a research-grounded position from the primary literature.
2. Bank cross-source convergence — what independent traditions agree on.
3. Check disputes against existing ratified artifacts; a settled decision is not reopened by a new argument.
4. Adjudicate citations against primary sources: verify the cited text actually supports the claim made for it.
5. Residual judgment falls to the **reversibility rule**: choose the least-binding option and record its binding trigger.
6. The accountable authority ratifies.

Consensus tone, convention, and model deference are all rejected as resolution grounds.

## 15. Process discipline

- **Gate cycle.** Draft → review (material issues only) → fix → ratify. Ratified decisions are closed.
- **Chunking.** One work unit equals one gate stage of one contract — three stages per contract (draft, review, ratify; fixing is the response to review findings inside the review stage). The chunk size keeps units auditable and prevents scope creep inside a stage.
- **Two registers.** Design conversation runs in plain language; produced artifacts conform to the lexicon. Conflating the registers introduces drift in both directions.
- **Amendment ripple.** Any amendment to an authoritative document (lexicon, invariant tier, process document) triggers an absorption sweep over affected artifacts, most-authoritative-first.
- **Mechanized conformance.** Artifact conformance is checked by script with the lexicon's tiered findings (BANNED / REVIEW / QUALIFY), never by feel; findings are fixed or explicitly judged and logged.
- **Operationalization.** The disciplines in this section are doctrine; their operational specification — gate definitions, pipeline structure, records, commission and archive execution — is the province of the process document (companion method: *Development Process Method*).

## 16. Construction order

1. Establish the component registry and place authority: which components exist, which hold which operations, which are deliberately authority-free.
2. Fix the reserved vocabulary (lexicon), or build it in tandem — the abstract syntactic level comes first.
3. Draft the Tier 0 invariant set.
4. Draft the shared doctrine: contract form, binding levels with binding triggers, failure taxonomy, fallback rule, blame doctrine, accountability doctrine, refinement discipline.
5. Draft the contracts: act-bearing first (they force the authority questions), then mechanism, read-path, byte-path, verification, and definitional contracts.
6. Run the closure check.
7. Write the divergence register and absorption map against any prior documents.
8. Gate the set: review → fix → ratify, one stage per work unit.

## 17. Observed failure modes

The specific ways this goes wrong, from experience:

- Locally restated invariants drifting from the original — the drifted copy gets cited.
- Synonym rotation on reserved operations — each synonym imports a foreign prior.
- Blame argued from live component state — unfalsifiable; evidence must be recorded.
- Atomic co-commit read as semantic merger — "the two happened together, so they are one thing."
- Denial handled as an error path.
- A deferred level binding silently — a guarantee quietly depends on a quantitative bound nobody ratified.
- Fixing a parent flaw with a child workaround instead of a parent amendment.
- Reopening ratified decisions under fresh enthusiasm.
- Coining vocabulary into undesigned areas.
- Over-promoting thin clause sets into full contracts, manufacturing authority.

---

Everything above is method. Bind it to a project by producing the component registry, the lexicon, the invariant tier, the shared doctrine, and the contracts — in that order — and gating each through review to ratification.
