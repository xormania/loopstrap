# Collision-Resistant Lexicon Method

**What this is.** A complete, self-contained method for developing a normative system lexicon: the single document that controls a project's vocabulary, naming, ontology boundaries, and reader behavior. The method was developed for systems whose specifications are written for — and largely built by — LLM coding agents, where a misread term becomes a defect in the built system. It assumes no prior context and names no source project; every term of art it uses is defined within it.

**When to apply it.** Use this method when three conditions hold: (a) the system's correctness depends on distinctions that ordinary technical English blurs; (b) the system's documents will be interpreted by readers — human or agent — carrying strong outside priors for its words; (c) a single **accountable authority** — one human, in whom final say vests and in whom accountability is assumed through their own recorded acts of ratification and correction — can hold final naming authority. The method's cost is real: every canonical term is a small specification. Apply it to authority-bearing vocabulary, not to all prose.

**Companions.** This method is one of three. The *System Design Contract Method* covers the contract set; the *Development Process Method* covers the process document that enforces both. The three methods produce a project's three authoritative documents — lexicon (vocabulary), contract set (design), process document (development process) — under one authority order: accountable-authority corrections → lexicon → ratified contract set → process document → process records. The lexicon supplies vocabulary to the other two documents; neither defines a term.

---

## 1. Stance and threat model

**Vocabulary is infrastructure.** In an agent-built system, the words of the specification are load-bearing. An agent that misreads a term does not produce a stylistic flaw; it produces wrong code, wrong data flow, or wrong authority placement. A term that can be misread is therefore a defect in the system, and collision resistance is an engineering requirement, not a documentation nicety.

**The threat is the dominant prior.** Readers — LLMs above all — resolve a word to its most common trained meaning, not to the meaning the author intended and not to the technically best meaning available. This resolution happens silently, is strongest under pressure (long context, complex tasks, paraphrase), and is invisible in the output until something built on the misreading fails. The lexicon's job is to make the intended reading the only available reading.

Design against these failure modes; every structure in this method exists to counter one or more of them:

1. **Authority relocation.** Prose hands a privileged act to the wrong grammatical subject ("the pipeline committed the change"), and the reader infers that component holds the authority — even when the sentence merely described a caller.
2. **Status laundering.** An adjective acquired through processing ("validated," "cleaned," "approved," "verified") is read as a change in standing that only a recorded act can produce.
3. **Boundary fusion.** One word covers two acts the system must keep apart ("release," "publish," "export"), and readers infer both acts happened when one did.
4. **Overload collapse.** A generic noun — state, record, log, object, output, evidence, identity, data — silently merges layers that have different authority.
5. **Import contamination.** A borrowed term drags its home semantics: consensus from ledger vocabulary, editability from version-control vocabulary, truth-force from legal vocabulary.
6. **Meta-collision.** A system term collides with the reader's own operational vocabulary. For LLM agents this is acute: "context," "agent," and "prompt" all have a first-person meaning to the reader that can overwhelm the system meaning. Where the governed scope includes the development process, the collision extends to the process verbs: "commit," "build," "merge," and "deploy" are first-person operations to a coding agent, and that reading can overwhelm the reserved meaning of the project's highest-authority acts.
7. **Morphological adjacency.** Two terms one edit or one morpheme apart get fused under pressure, or a compound phrase gets read as a related-looking reserved term.
8. **Premature naming.** Naming an undesigned area hardens a premature design; the name accretes assumptions before a decision was ever made.

---

## 2. The lexicon's authority model

Fix these properties of the document itself before writing entries. They are what make the lexicon enforceable rather than advisory.

- **Sole authority.** The lexicon is the only authoritative vocabulary document for the project. No other document, register, or source supplies vocabulary — the contract set and the process document included; both are conformant artifacts under the lexicon. If two documents can define a term, agents will pick whichever they saw last.
- **Everything normative.** Every line exists to shape reader interpretation or reader output. There is no background, commentary, or support material inside the lexicon; a sentence that binds nothing is deleted.
- **One amendment path.** Corrections by the accountable authority are the only way the lexicon changes. Until corrected, it controls — including over the accountable authority's earlier informal statements.
- **Internal references are navigational only.** Section cross-references point within the document; they never create a second authority layer or imply external sources.
- **Banned wording is shown only to ban it.** Text labeled as a violation appears exactly so readers can recognize and avoid it; it is never to be reused except to name it as banned. State this rule explicitly — otherwise the presence of an example legitimizes the wording.
- **Reading rules up front.** If the lexicon uses any bare shorthand internally (for economy), declare it in the header and state the qualified forms required in all outputs.
- **First-read anchors.** Place the five to seven most catastrophic rules in the header, so a reader who reads nothing else gets them.
- **Pasteability.** Design the agent-facing sections (rules, canonical entries, digests) to be pasted directly into prompts without editing. A lexicon that requires adaptation before use will be adapted wrongly.

---

## 3. Construction order

Build the lexicon in this order. Each step feeds the next; skipping ahead produces terms with no anchoring.

1. **Fix the authority registry.** Enumerate the closed list of system components that can hold authority — with one line each stating authority placement only. Every later `Authority:` field points here. If a concept's authority cannot be placed, the concept is not ready for a name.
2. **Enumerate the privileged acts.** List every act that changes system standing (creates, alters, or removes authoritative state). Assign each act exactly one verb and exactly one authority, and name each act's holder by the ⟨act⟩ authority pattern — the commission authority, the award authority — so the term alone carries the act it holds. Run the closure check: every act covered exactly once, every authority appearing, no verb shared.
3. **Fix the standing boundaries.** State the separations the system depends on (the distinctions that must never blur), each in one sentence, in one place. These are what the vocabulary exists to protect; list them so they can be referenced rather than re-derived. Where the governed scope includes the development process, the design-time / run-time boundary is mandatory (§8.2).
4. **Sweep for overloaded nouns.** Collect every generic noun the domain will force into prose. Decide for each: banned bare with qualified forms, or confined to fixed compounds.
5. **Hunt collisions.** For every candidate term, ask what the dominant prior is and what a reader holding it would do wrong. Record the results as the collision map (§8.3). Probing several LLMs cold — "what does X mean?" with no context — is a cheap, direct measurement of the prior. Where the governed scope includes the development process, the process-act family — deploy, release, publish, ship, commit, build, merge, rollback, version, environment, archive — is a mandatory sweep: it pairs the strongest outside priors (boundary fusion, authority relocation) with acute meta-collision for agent readers.
6. **Write canonical entries** (§6) for every reserved term, anti-definitions included.
7. **Rank the neighborhoods.** For each concept, adjudicate its near-synonyms explicitly (§8.6) so that when a writer reaches for a neighbor, the lexicon has already answered.
8. **Write behavior triggers** (§8.7): term families that switch a reader into a specific checking behavior.
9. **Write the pasteable rules and digests** (§8.8–8.9): the compressed layers for direct prompt use.
10. **Mechanize enforcement** (§10): encode what is mechanically checkable.
11. **Set the amendment procedure** (§11) before first use, not after first dispute.

**Scale guidance.** Roughly 40–60 canonical terms and 25–35 outright bans is the scale at which a lexicon of this kind has proven usable as a single document. Every entry must earn inclusion by authority-bearing weight; a lexicon that tries to govern all prose governs nothing.

---

## 4. Naming principles

These fifteen principles govern every term decision. They are the compressed form of the method; when in doubt, they adjudicate.

1. **Authority is named, not implied.** Every authority-bearing noun carries its authority in the name. The test is portability: terms get copied out of context into new prompts and must still signal authority placement standing alone. If a reader cannot tell from the term alone which authority holds the concept, the term is underqualified.
2. **One reserved term per privileged act.** No synonym rotation for acts that change standing. Synonym variety is a virtue in prose and a defect in a lexicon: every synonym is a fresh chance for a reader to import the wrong prior.
3. **Privileged verbs are subject-locked.** A reserved verb takes only the act's authority as grammatical subject. Everything else gets an explicitly non-authoritative verb set — propose, submit, request, claim, declare. A sentence that gives a reserved verb to the wrong subject is a violation regardless of intent, even when it accurately describes a caller of the real authority.
4. **Truth vocabulary is scarce by design.** "Truth," "authoritative," "source of truth" attach to exactly one designated source. Everything else carries an explicit non-authority marker: derived, proposed, claimed, advisory, rebuildable, non-authoritative.
5. **Epistemic status is part of the noun.** Name things by their standing in the system's lifecycle, not by their content type. A noun must never let a sentence skip a gate: "the tool's validated output" must be unwritable, forcing "the tool's validation claim, which, if accepted, …".
6. **Generic overloaded nouns are banned bare.** Enumerate them; require qualification everywhere; where a generic word is unavoidable, confine it to fixed compounds and allow it only inside those compounds. A bare form appears only where naming it is necessary to ban it.
7. **Acts that must stay distinct never share a word.** For each standing boundary, build pairwise-disjoint vocabulary sets, and ban outright any word that straddles two sets — even when the straddling word is common and convenient. Convenience is exactly how fusion spreads.
8. **Mechanism words must not smuggle authority.** Words naming mechanisms — proof, verification, hash, index, storage — may never be phrased as creating, validating, or gating authoritative state. Fix the dependency direction explicitly (which component defines the interface, which merely implements it), and state that validity never depends on the mechanism's availability.
9. **Imports are admitted on dominant meaning, not best meaning.** Adopt an outside term only if its most common usage — the reader's prior — already lands on the intended authority placement. A term with a correct niche meaning but a conflicting dominant meaning is rejected even when technically apt, because readers under pressure reach for the dominant meaning.
10. **Every reserved term ships with an anti-definition.** The entry states what the term is not, names the nearest collisions, and redirects to the correct term. The anti-definition is part of the entry, not commentary (§7).
11. **Do not coin into undesigned areas.** Maintain an explicit list of no-coin zones: areas where design is deliberately unsettled and no vocabulary may be minted. Fix the placeholder phrasing writers must use when prose touches such an area. Premature names harden premature designs.
12. **Qualification follows a fixed system.** Define a closed set of standard qualifying prefixes or modifiers. Ad-hoc intensifiers — "real," "actual," "final," "true" — are non-conforming: they signal the writer sensed ambiguity and patched it locally instead of using the reserved form.
13. **Acts, not adjectives, change status.** Standing changes only by recorded acts of the named authorities. No participle acquired through processing confers or changes standing, ever. This principle single-handedly blocks status laundering.
14. **Aliases are enumerated or banned.** Every canonical entry lists its allowed aliases exhaustively; a nearby term is licensed only by an explicit rank in the term rankings. An unlisted synonym is a violation, not a style choice.
15. **Capitalization marks proper names only.** Component proper names are capitalized; reserved terms are lowercase in ordinary prose. Capitalization never creates a semantic distinction — a rule that fails silently if left implicit.

---

## 5. Term admission and coining

Every candidate term — imported or coined — passes the same test. Failing any criterion means the term is not admitted.

1. **Dominant-meaning alignment.** Would the median reader's prior, cold, land on the intended authority placement? Measure rather than argue: check usage in primary literature and standards, and probe LLMs with the bare term.
2. **One term per concept.** Does a reserved term already cover the concept? Admitting a second name for a named act violates principle 2 no matter how apt the newcomer is.
3. **Form distance.** Is the candidate lexically and morphologically distant from every existing reserved term? Reject one-morpheme neighbors of reserved terms and compounds that read as variants of them. Adjacency is fusion waiting to happen.
4. **Anti-definition ready at coin time.** Can you state, now, what the term is not and what its nearest collision is? If not, the concept is not crisp enough to name.
5. **Fits the qualification system.** Does the term slot into the fixed prefix system, or does it demand ad-hoc qualification?

**Naming-gap escalation.** When a task requires referring to a capability or concept the lexicon does not name and the criteria are unmet: do not coin, do not borrow an outside term, do not revive rejected wording. Flag the naming gap to the accountable authority and proceed without naming it. This rule must be stated in the lexicon itself, because the pressure to coin arises mid-task, when the lexicon's author is not present.

**Contested candidates.** When two admissible candidates compete, or evidence about the dominant prior conflicts: gather primary-source usage, bank where sources converge, and adjudicate divergences against the sources rather than against preference. If judgment remains after evidence, choose the least-binding option and record the binding trigger — the specific future finding that would reverse the choice.

**Rejections are recorded.** A rejected term enters the forbidden table or an entry's anti-definition with its reason. Unrecorded rejections get re-litigated by every future writer who independently rediscovers the "obvious" word.

---

## 6. Anatomy of a canonical entry

Each reserved term gets one entry containing all of the following fields. The entry is the unit of specification; a term missing fields is a term half-defined.

- **Term.** The canonical form, exactly as it must be written.
- **Definition.** One to two sentences. Authority placement explicit (who performs or holds it); lifecycle position explicit (what standing it has, before and after which system lifecycle gate).
- **Authority.** A pointer into the authority registry.
- **Related.** Adjacent canonical terms, so readers land on neighbors deliberately rather than by drift.
- **Aliases.** The exhaustive list of allowed alternate forms, or none. Note register limits (e.g., a short form allowed in documentation after first use but not in prompts).
- **Not (the anti-definition).** Two to five items; construction rules in §7.
- **Collision.** The single strongest outside prior, stated as the misreading to defuse — not as etymology or history.
- **Register phrasing.** The required phrasing per output register (§9): the documentation form and the agent-prompt form, which often differ in explicitness. The prompt form may be a structured term card — a tagged block carrying definition, not, write-instead, and the subject rule — for verbatim injection.
- **Violation.** One banned sentence, shown only to ban it, paired with the corrected rewrite. The pair teaches the repair, not just the prohibition.

**Worked example** (invented domain — a grants system whose Grants Board is the sole authority for funded standing):

> **award** — The Board act that confers funded standing on a submission; the only act by which funded standing arises. *Authority:* Grants Board. *Related:* submission, panel recommendation, funded standing. *Aliases:* none. *Not:* a panel recommendation — panels recommend and reviewers score; only the Board awards. Not a disbursement — payment is a downstream act that changes no standing. Not an announcement — standing is conferred by the recorded act whether or not it is announced; write *award notice* for the communication. *Collision:* the prize-ceremony prior reads "award" as the announcement event; here it is the standing-conferring act. *Docs:* "awarded by the Board." *Prompts:* "only the Board awards; panels recommend, reviewers score." *Violation:* "The review panel awarded the grant" → write: "The panel recommended; the Board awards."

Every field is present, every "not" ends in a redirect, and the term is portable: "award" alone, in this system, names the Board's act and nothing else.

---

## 7. Writing anti-definitions

The anti-definition is the highest-leverage field in an entry, because it operates exactly where the reader's prior operates: at the moment of misreading. Five construction rules.

1. **Replacement, not omission.** Every "not" item ends with what to write instead. "Not a recommendation" is half a rule; "not a recommendation — write *panel recommendation (advisory)*" is executable. A ban without a replacement leaves the writer stranded mid-sentence, and stranded writers improvise.
2. **Order by danger.** Put the strongest, most likely misreading first. Readers skim; the first "not" is the one that lands.
3. **Name the neighbor.** Each item should point at the actual adjacent canonical term the misreading would land on, tying the anti-definition into the lexicon's structure rather than floating free.
4. **Keep the redirect executable.** A writer mid-sentence must be able to substitute the correct form immediately, without re-deriving the doctrine. If the redirect needs a paragraph of explanation, the entry's definition — not the anti-definition — is where that paragraph belongs.
5. **One prior per item; short scope.** Each "not" item names exactly one banned prior. No multi-exclusion sentences: negative scope stays short, and tokens are spent on the replacement's boundary, not on describing the forbidden concept.

The same replacement rule applies to every ban in the lexicon: a forbidden term always ships its replacement, or an explicit "say nothing."

---

## 8. Supporting structures

Canonical entries alone are not enough; readers fail in patterned ways that dedicated structures catch. Build each of the following.

### 8.1 Authority registry
The closed list of components, numbered or keyed, one line each, stating authority placement only. It answers exactly one question — where each authority is placed — and answers it once.

### 8.2 Standing boundary rules
The fixed separations, each stated once, marked as not-reopenable. Include here: the no-coin zone list with its placeholder phrasing, and the naming-gap escalation rule.

Where the governed scope includes the development process, one boundary is mandatory: **design time / run time** — developing the design versus the designed system in use. Exactly two crossings are sanctioned: the commission-family acts (design to run: the only acts that change run-time live standing) and recorded evidence (run to design: findings, divergence detections, binding-trigger events, which may initiate the amendment path and nothing else). Vocabulary is dispositioned per side; a term may span the boundary only by explicit declaration on a closed spanning list — the failure-outcome taxonomy is the canonical spanning set. Registry entries carry a side marker; an unsided entry fails the closure check.

### 8.3 Collision map
A table of hazard areas, built from step 5 of the construction order. Columns:

| Hazard area | Dangerous generic terms | Likely misinterpretation | Correct distinction | Recommended pattern |
|---|---|---|---|---|

Each row binds: apply the distinction, use the pattern, treat the listed misinterpretation as a violation to prevent. The map is organized by hazard, not by term, because a reader entering a hazard area needs all of its traps at once.

### 8.4 Qualification table
The bare-banned nouns: term | why bare use is unsafe | safe qualified forms. This is the fast path for the most frequent class of violation.

### 8.5 Forbidden vocabulary table
Outright bans: term | why dangerous | wrong inference invited | use instead. Note that "why dangerous" states what a reader will do, not what the author dislikes.

### 8.6 Term rankings
For each semantic neighborhood (the cluster of near-synonyms around a concept), rank every plausible term:

- **Preferred** — use.
- **Acceptable** — allowed, with the licensing condition stated (register, framing, or fixed compound).
- **Risky** — avoid; permitted only with the noted framing.
- **Reject** — never in system senses.

Each rank carries a note stating the behavioral reason only — what a reader holding the term's prior will do wrong — never taste. Rankings exist because writers under pressure reach for near-synonyms; giving every neighbor an explicit verdict removes the discretion through which drift enters, and makes "an unlisted synonym is a violation" enforceable.

### 8.7 Behavior triggers
Term families that switch a reader into a required checking behavior. The pattern: **Terms:** (the family) → **Required behavior:** (the check, and the rewrite if it fails). Typical triggers: any privileged verb → verify the grammatical subject is the act's authority; any mechanism noun → attach the non-authority marker before reasoning further; any transformation word → append the standing rider ("standing unchanged") unless the explicit act is present; any producer statement → classify as untrusted claim. Triggers convert the lexicon from a reference into a checklist that fires at the moment of writing.

### 8.8 Pasteable rules
The lexicon compressed into one-sentence enforceable rules, each self-contained, imperative, ordered by catastrophe. These are what actually gets pasted into most prompts; write them so that any one rule, alone, still binds correctly.

### 8.9 Digests and narration scaffold
Compressed layers for constrained prompt budgets: the top-N canonical terms; the avoid/always-qualify list; the top rules; the top collision risks. Include a **narration scaffold**: a canonical safe walkthrough of the system's highest-interdependence procedure, written in fully conformant language — with an explicit disclaimer that the scaffold names no new operation, carries no authority, and authorizes nothing. Writers imitate examples more reliably than they apply rules; the scaffold gives them the right example to imitate.

**Delivery pattern.** Header anchors are necessary but not sufficient: over long agentic sessions, rule adherence decays with distance from the rule. Digests are delivered in a sandwich — first-read anchors at the head; the task-local digest and the term cards for the reserved terms actually in use placed adjacent to the task at the end — and in focused slices: only what the work unit needs, verbatim, never paraphrased.

---

## 9. Register discipline

A lexicon that polices every conversation kills the design work it serves. Separate the registers explicitly.

- **Design conversation** (ideation, discussion with the accountable authority): plain language, unpoliced. Conformance here would tax thinking for no benefit.
- **Artifacts** (specifications, contracts, prompts, any document agents will consume): fully conformant. Conformance is applied as a translation pass at artifact production, not imposed on ideation.
- **Per-register phrasing in entries.** Documentation can rely on established context; agent prompts cannot, and their required phrasing is correspondingly more explicit and more self-contained. Entries state both.
- **The lexicon's own interior.** If the lexicon uses a bare shorthand internally for economy, its reading rules declare this and require the qualified forms in all outputs.

---

## 10. Enforcement

A lexicon without mechanical enforcement decays into aspiration. Build a conformance checker and make it a gate.

**Three finding tiers:**

- **BANNED** — hard fail; must be fixed before delivery. Forbidden terms, banned phrasings, banned compounds.
- **REVIEW** — flagged for judgment; the reviewer decides and records the decision. Risky terms, suspicious patterns near reserved verbs.
- **QUALIFY** — a bare overloaded noun; the qualified form is required.

**What is mechanizable:** forbidden-term matching; bare-noun detection; subject-lock checks at the pattern level (a reserved verb with a non-authority subject nearby); unlisted-alias detection; banned-compound detection. **What needs judgment:** whether a Risky term's framing condition is met; register fit; whether a REVIEW finding is a true violation. The checker narrows human attention; it does not replace it.

**Exemptions are explicit.** The checker never runs on the lexicon itself or on any document that quotes banned forms in order to ban them — such documents necessarily contain violations as specimens. List the exempt documents.

**Conformance is a gate, not a style guide.** Run the checker on every artifact before delivery; fix BANNED findings; adjudicate REVIEW and QUALIFY findings and record the adjudications in the artifact's change log. An artifact is not ratifiable with open BANNED findings.

---

## 11. Maintenance and amendment

- **Amendment path.** Corrections ratified by the accountable authority are the only mechanism of change. Proposals may come from anywhere; authority to amend does not.
- **Absorption sweep.** Every amendment triggers a conformance and consistency sweep over dependent artifacts, most-authoritative dependents first, and regeneration of all derived digests and crib materials. An unabsorbed amendment is a fork in disguise.
- **Divergence register.** When a source document and the lexicon disagree, resolve explicitly and record the resolution: which reading won, why, and what changed. Silent adaptation around a divergence guarantees its recurrence.
- **Closed and deferred markers.** Mark settled decisions closed and treat them as closed — do not reopen them in later drafting. Mark deliberately unsettled items deferred, with the condition under which they bind. Recorded binding triggers from contested calls (§5) live here.
- **Never fork.** Ratified versions replace superseded drafts. Two live versions of a vocabulary document is a collision generator aimed at your own project.

---

## 12. Quality checklists

**Per entry:**

1. Standing alone, out of all context, does the term signal its authority?
2. Is the dominant outside prior identified, and does the entry defuse that specific misreading?
3. Is the anti-definition present, ordered by danger, with every item ending in a redirect?
4. Is a violation example paired with its corrected rewrite?
5. Is the alias list exhaustive (or explicitly empty)?
6. Are both output registers covered?
7. Is the authority a registry pointer, not free text?
8. Is the entry free of commentary — does every sentence bind?

**Per document:**

1. Closure check: every privileged act has exactly one term and one authority; every act is covered exactly once; every authority appears.
2. Disjointness check: for every standing boundary, the vocabulary sets on each side share no word, and every straddling word is banned.
3. Every bare-banned noun appears in the qualification table with safe forms.
4. Every ban ships a replacement or an explicit "say nothing."
5. No-coin zones are enumerated, each with the fixed placeholder phrasing; the naming-gap escalation rule is stated.
6. First-read anchors, reading rules, and the pasteability design are present in the header.
7. The digest layers are consistent with the body — regenerated, not hand-drifted.
8. The enforcement tiers, checker exemptions, and amendment path are stated inside the document, not assumed.

A lexicon that passes both checklists is ready for first use. It is finished only in the sense that a gate is finished: it now controls what passes through it, and it is maintained by the amendment path for as long as the system it protects is alive.
