# LanguageServerFixture — System Contracts

**Status:** DRAFT 2. Not ratified. 2026-07-30 01:38 UTC.
**Authority:** xor (accountable authority). This draft binds nothing until ratified.
**Authored under:** `LanguageServerFixture-lexicon-DRAFT3-20260730T0109Z.md` (sha256 `07ce37c6…c397fc`). The lexicon is authoritative over this document; a vocabulary conflict is resolved by amending this document, never the lexicon.
**File identity:** this document lands as `fixture_langserv-contracts.md`; the identifier appears in the filename only, per the lexicon's naming rule.

---

## Parties

Aligned with the lexicon's authority registry (§1). Authority-free parties are named as such deliberately.

| Party | Registry | Standing |
|---|---|---|
| accountable authority | AR-1 | sole holder of ratification |
| corpus baseline | AR-2 | truth-holder; act-free |
| fixture server | AR-3 | run-time emitter; no authority over correctness |
| launch harness | AR-4 | assembles; decides nothing |
| assertion suite | AR-5 | decides; enforces nothing |
| transcript | AR-6 | authority-free evidence |
| subject under test | AR-7 | authority-free by design |
| CI gate | AR-8 | enforces; decides nothing |

---

## Tier 0 — invariants

Each invariant is one placement or one prohibition. Contracts cite these by id and never restate them.

[INV-1] The expectation record reaches the assertion suite and nothing else. No component that produces measured behaviour may read, import, derive from, or share a module or build product with the expectation record.

[INV-2] Under the determinism guarantee, an identical pinned scenario, identical corpus baseline, and identical protocol input sequence produce identical logical emissions in identical order on every supported operating system.

[INV-3] A self-check outcome and a subject outcome never fuse. A subject finding exists only after the FO-6 exclusion — baseline defect, fixture defect, launch-harness defect, assertion-suite defect — is complete and stated in the adjudicated outcome.

[INV-4] The launch harness assembles, the assertion suite adjudicates, the CI gate enforces. No component performs two of the three.

[INV-5] The fixture language is wired by test-only routing exclusively. Support registration is forbidden.

[INV-6] No component opens a network connection during a server lifetime or an adjudication.

[INV-7] Every server lifetime operates in an isolated workspace created for it. No user or production workspace is read as corpus input or mutated.

[INV-8] Invalid, missing, contradictory, or vacuous inputs terminate the operation explicitly before any standing effect. Nothing substitutes a silent default, and no adjudication is conforming for lack of applicable expectations or observed behaviour.

[INV-9] Every adjudicated outcome identifies the exact corpus baseline, pinned scenario, fixture-server build, and platform it was produced against.

[INV-10] The transcript is non-authoritative evidence. Neither its availability nor its content gates the validity of any outcome or confers standing on anything.

---

## Contracts

Act-bearing contracts first, one act per contract; structural contracts follow. Every clause is self-contained and binds alone.

### Contract 1 — ratify

Parties: accountable authority; corpus baseline.

[C-RAT-1] The accountable authority MUST be the sole party that ratifies the lexicon, a corpus baseline, or an amendment to either; no review, merge, check, or agent act confers standing.

[C-RAT-2] Ratification of a corpus baseline MUST take as its object exactly one pairing of a fixture corpus and its expectation record; ratifying either half alone produces no baseline.

[C-RAT-3] Current explicit direction from the accountable authority supersedes every ratified document immediately; the durable text changes only when that direction is incorporated and ratified as an amendment.

[C-RAT-4] A standing change produced by ratification MUST be all-or-nothing: either the amended pairing holds in full, or the prior ratified state persists unchanged; no intermediate standing exists.

[C-RAT-5] Blame and evidence: a standing claim that lacks a ratification by the accountable authority is an assertion-suite defect if adjudicated upon, and the adjudicated outcome's pinned identity (INV-9) is the evidence that decides which baseline actually held.

Markers: closed.

### Contract 2 — pin

Parties: launch harness; fixture server.

[C-PIN-1] The launch harness MUST pin exactly one scenario per server lifetime, before the first protocol message of that lifetime, and the pinned scenario MUST NOT change for the lifetime's duration.

[C-PIN-2] A pinned scenario MUST be exactly one of: the baseline scenario; a perturbation scenario naming one admitted protocol-permitted perturbation — an injected delay, an exact notification burst, response reordering that preserves correctness, or an error-response substitution — at a stated method and invocation ordinal; or a fault scenario naming one injected fault — withholding, an abort, or a malformed emission — at a stated method and invocation ordinal.

[C-PIN-3] Every pinned scenario MUST state its response-shape parameter — hierarchical or flat — for symbol emissions.

[C-PIN-4] Precondition: the launch harness MUST NOT pin a scenario unless the scenario input passes structural validation and names a ratified corpus baseline; an invalid or unratified reference terminates the operation per INV-8.

[C-PIN-5] Blame and evidence: scenario leakage across server lifetimes or a mid-lifetime scenario change is a launch-harness defect; the pinned identity of each adjudicated outcome (INV-9) together with the transcript's recorded scenario identity evidences which scenario governed.

Markers: closed.

### Contract 3 — launch

Parties: launch harness; fixture server; subject under test.

[C-LAU-1] The launch harness MUST be the sole creator of a server lifetime, and MUST create it as a real external process speaking the Language Server Protocol over standard input and output as the minimum integration path.

[C-LAU-2] The launch harness MUST create a fresh isolated workspace for each server lifetime (INV-7) and MUST launch a fresh server lifetime for every non-baseline scenario adjudication.

[C-LAU-3] Precondition: launch requires a pinned scenario reference, a ratified corpus baseline reference, and declared launch inputs — command, arguments, environment, workspace root; the launch harness MUST supply these explicitly and MUST NOT rely on ambient machine state.

[C-LAU-4] Guarantee: on launch the launch harness MUST make the pinned identity — corpus baseline, scenario, fixture-server build, platform — available to the adjudication that consumes the lifetime (INV-9).

[C-LAU-5] Blame and evidence: a lifetime created outside the launch harness, or launched against unvalidated inputs, is a launch-harness defect; the recorded launch inputs and the transcript's opening lines evidence the actual construction.

Markers: closed.

### Contract 4 — emit

Parties: fixture server; subject under test.

[C-EMIT-1] The fixture server MUST emit only framed protocol messages — protocol responses, protocol error responses, and protocol notifications — and every emission's content MUST derive from parsed fixture declarations, the ratified corpus baseline, and the pinned scenario, never from file names or paths alone.

[C-EMIT-2] The fixture server MUST answer every processed protocol request with exactly one protocol response or protocol error response, in arrival order, except where the pinned scenario states an admitted perturbation or injected fault governing that request.

[C-EMIT-3] Under the baseline scenario, every processed request MUST be answered with the result the corpus baseline fixes, well-formed, in arrival order, within the configured bound (deferred, D-3).

[C-EMIT-4] Under a perturbation scenario the fixture server MUST produce exactly the stated protocol-permitted perturbation — the stated delay before emitting, the exact notification burst while the identified request is outstanding, the stated correctness-preserving response order, or the stated error-response substitution — and nothing else non-baseline.

[C-EMIT-5] Symbol emissions MUST use the shape the pinned scenario's response-shape parameter states, and every wire position emitted MUST be a zero-based line and zero-based UTF-16 code-unit offset under the ratified position-encoding invariant.

[C-EMIT-6] The fixture server MUST distinguish protocol requests, protocol notifications, and cancellation on receipt, MUST emit nothing in reply to a protocol notification, and MUST maintain document state and document versions exactly as the subject under test's synchronization messages supply them.

[C-EMIT-7] The fixture server MUST advertise exactly the capability set the pinned scenario states, during initialization, and MUST select or fall back to UTF-16 position encoding there.

[C-EMIT-8] Blame and evidence: an emission that diverges from the corpus baseline and pinned scenario is a fixture defect; an emission the scenario states is conforming instrument behaviour; the transcript's ordered emission lines against the pinned identity evidence which occurred.

Markers: closed.

### Contract 5 — withhold

Parties: fixture server; subject under test.

[C-WTH-1] The fixture server MUST withhold — permanently decline to emit a response for — exactly the protocol request the pinned fault scenario identifies by method and invocation ordinal, and no other.

[C-WTH-2] Withholding MUST leave the identified request's response obligation unsatisfied for the remainder of the server lifetime; it is conforming instrument behaviour and intentionally protocol-non-conforming, and the fixture server MUST otherwise continue conforming emission.

[C-WTH-3] Blame and evidence: a withheld response no fault scenario states is a fixture defect; a subject under test that does not bound its wait is adjudicated on the subject side; the transcript's scenario-trigger line and the absence of the response emission evidence the withholding.

Markers: closed.

### Contract 6 — abort

Parties: fixture server.

[C-ABT-1] The fixture server MUST abort — end its own server lifetime mid-request — only when the pinned fault scenario states it, at the stated method and invocation ordinal, leaving the outstanding request's response obligation unsatisfied.

[C-ABT-2] An unplanned Rust panic or process end is a fixture defect, never scenario behaviour; the pinned scenario is the only source of a conforming abort.

[C-ABT-3] Blame and evidence: the transcript's final recorded lines, the pinned scenario, and the exit status collected at reap evidence whether an abort was stated or a fixture defect occurred.

Markers: closed.

### Contract 7 — retire

Parties: fixture server; subject under test.

[C-RET-1] The fixture server MUST retire only after the protocol shutdown sequence completes: the subject under test sends the shutdown request, the fixture server emits the shutdown response, and the subject under test sends the exit notification.

[C-RET-2] Where the pinned fault scenario states that a shutdown obligation is intentionally left unsatisfied, remaining running is conforming instrument behaviour, and the launch harness's external termination obligation (C-TRX-1) governs the lifetime's end.

[C-RET-3] Blame and evidence: a process end before the exit notification that no scenario states is a fixture defect; the transcript's shutdown-sequence lines evidence the actual order.

Markers: closed.

### Contract 8 — terminate externally

Parties: launch harness; fixture server.

[C-TRX-1] The launch harness MUST terminate externally every server lifetime still running when its consuming adjudication's observation is complete, and MUST NOT leave a running child process behind any completed adjudication.

[C-TRX-2] External termination MUST originate outside the child process and MUST be recorded with the lifetime's pinned identity in the adjudicated outcome that consumed the lifetime.

[C-TRX-3] Blame and evidence: a still-running child after its adjudication completes is a launch-harness defect; the reaped exit status and the adjudicated outcome's stated lifecycle evidence the termination path.

Markers: closed.

### Contract 9 — reap

Parties: launch harness.

[C-REAP-1] The launch harness MUST reap every exited child process — wait for it, collect its exit status, and permit operating-system resource release — for every server lifetime it launched, on every outcome path.

[C-REAP-2] Reaping MUST NOT be applied to a running server lifetime; the launch harness MUST first establish that the lifetime ended — by retire, abort, or external termination — and then reap.

[C-REAP-3] Blame and evidence: an unreaped exited child is a launch-harness defect; the collected exit status is the evidence and is carried into the adjudicated outcome's pinned identity.

Markers: closed.

### Contract 10 — record

Parties: fixture server; transcript.

[C-REC-1] The fixture server MUST record — append one line to the transcript for — each lifecycle event, each received protocol message, each emission, and each scenario trigger, in the order they occur within the server lifetime.

[C-REC-2] The transcript MUST be line-delimited, ordered, and append-only within its server lifetime, and MUST carry the lifetime's pinned identity in its opening lines.

[C-REC-3] The fixture server MUST NOT take the expectation record as any operation's object or input (INV-1); recording concerns the transcript only.

[C-REC-4] Blame and evidence: a transcript gap or reordering is a fixture defect, but per INV-10 no outcome's validity depends on the transcript; adjudication proceeds on observed behaviour with the transcript as evidence only.

Markers: closed.

### Contract 11 — adjudicate

Parties: assertion suite; corpus baseline; subject under test; fixture server.

[C-ADJ-1] The assertion suite MUST be the sole reader of the expectation record (INV-1) and MUST adjudicate every outcome against the ratified corpus baseline and the pinned scenario only.

[C-ADJ-2] Every adjudicated outcome MUST declare its side — self-check or subject — and MUST state its pinned identity (INV-9); a self-check outcome is dispositioned instrument-side and never becomes a subject finding (INV-3).

[C-ADJ-3] The assertion suite MUST distinguish, as separate adjudicated outcome classes: conforming; non-conforming; inapplicable because the pinned scenario's capability set does not advertise the exercised feature; invalid per INV-8; and instrument-side operational defect — a launch-harness defect or an assertion-suite defect — none of which is a subject outcome.

[C-ADJ-4] The assertion suite MUST NOT derive, regenerate, or amend any expectation from observed output; a disagreement between the expectation record and the fixture corpus text is adjudicated a baseline defect and routed to amendment and re-ratification.

[C-ADJ-5] A subject finding MUST state a complete FO-6 exclusion: the recorded evidence excluding baseline defect, fixture defect, launch-harness defect, and assertion-suite defect, in that order, before attribution to the subject under test.

[C-ADJ-6] An FO-4 exclusion MUST cite a conforming suite-assurance adjudication of the same comparison class, produced in the same adjudication run against the same assertion-suite build; the assertion suite's unsupported self-attestation excludes nothing, and an FO-4 exclusion the cited evidence cannot support routes to the accountable authority for resolution.

[C-ADJ-7] The assertion suite MUST NOT launch, pin, configure, terminate, reap, or enforce (INV-4), and MUST treat every statement sourced from the subject under test as an untrusted claim, never as a fact about the corpus.

[C-ADJ-8] Blame and evidence: a wrong comparison, a wrong side attribution, or an FO-6 exclusion the cited evidence does not support is an assertion-suite defect; the adjudicated outcome's stated evidence, the transcript, and the suite-assurance adjudications decide it.

Markers: deferred → D-7 (persistent outcome form).

### Contract 12 — enforce

Parties: CI gate; assertion suite.

[C-ENF-1] The CI gate MUST execute adjudicated outcomes exactly as adjudicated and MUST NOT decide, reinterpret, downgrade, or waive any outcome (INV-4).

[C-ENF-2] The CI gate MUST execute the full adjudication set on every supported operating system (D-4), including the suite-assurance adjudications and a reproduction adjudication under INV-2, and MUST treat a missing adjudication as non-conforming, never as conforming by absence (INV-8).

[C-ENF-3] Blame and evidence: an enforced consequence that diverges from the adjudicated outcome set is a CI-gate violation of this contract, evidenced by the outcome set's pinned identities against the enforced result.

Markers: closed.

### Contract 13 — corpus baseline (structural)

Parties: corpus baseline; accountable authority.

[C-CB-1] The corpus baseline is the ratified pairing of a fixture corpus and its expectation record, and is the sole authority for the meaning of fixture-language source in this system.

[C-CB-2] The fixture corpus MUST be hand-authored, exact, and checked in; every byte is load-bearing, and it MUST contain non-ASCII identifiers so that a collapsed position-encoding unit produces a visible divergence rather than a silent conforming outcome.

[C-CB-3] The expectation record MUST be hand-authored and MUST enumerate the fixture corpus's complete symbol graph: every fixture declaration with its kind, corpus declaration path, name range, and declaration range, and every defining occurrence and referencing occurrence, all in wire positions.

[C-CB-4] The expectation record MUST be stored apart from every fixture-server input, sharing no file, module, derivation, or build product with them (INV-1).

[C-CB-5] A fixture-corpus edit without a matching expectation-record amendment and a fresh ratification produces no corpus baseline; the prior ratified baseline persists (C-RAT-4).

[C-CB-6] Structural validation MUST reject a corpus baseline candidate that is missing either half, internally contradictory, or vacuous — enumerating no fixture declaration or no occurrence — before any adjudication consumes it (INV-8).

Markers: closed.

### Contract 14 — fixture-server standing conduct (structural)

Parties: fixture server.

[C-FS-1] The fixture server MUST reject loudly — terminate with an explicit diagnostic and a non-zero exit status, before serving — any scenario or corpus input that is missing, structurally invalid, of an unsupported format version, or contradictory (INV-8); it MUST NOT substitute defaults.

[C-FS-2] The fixture server MUST NOT open network connections (INV-6), MUST NOT read outside its supplied corpus inputs and isolated workspace, and MUST NOT read the expectation record (INV-1).

[C-FS-3] For a pinned fixture-server build, pinned scenario, pinned corpus baseline, and identical inbound protocol sequence, the fixture server MUST produce identical logical emissions in identical order on every supported operating system (INV-2); platform-specific process detail may be recorded separately and MUST NOT change the logical result.

[C-FS-4] The fixture server MUST expose in the transcript's opening lines the identities of the corpus baseline, scenario, and its own build, sufficient to identify which pinned inputs governed the lifetime (INV-9).

[C-FS-5] The fixture language the fixture server parses exists only to generate a fully enumerable symbol graph; the fixture server MUST NOT implement evaluation, typing, proof, or computation semantics for it.

Markers: deferred → D-1, D-2 (the fixture language's name, extension, and assertion keyword are the accountable authority's to set before corpus ratification).

### Contract 15 — subject relation (structural)

Parties: subject under test; launch harness; assertion suite.

[C-SUT-1] The subject under test — Serena together with SolidLSP — holds no authority in this system; nothing it emits is expected, correct, or authoritative, and every claim sourced from it is adjudicated against the corpus baseline.

[C-SUT-2] In a subject adjudication the subject under test MUST reach the fixture server through its real language-server integration path under test-only routing (INV-5); a bypass that feeds the subject synthetic emissions adjudicates nothing about the integration.

[C-SUT-3] The instrument owes the subject under test conforming protocol behaviour exactly as the pinned scenario states it — including its stated perturbations and injected faults — and owes it nothing else; a subject timeout is the subject's act and is adjudicated subject-side.

Markers: closed.

---

## Failure doctrine

Uniform across every contract, in the lexicon's vocabulary.

[C-DOC-1] Rejection: a malformed or invalid submission — scenario, corpus baseline candidate, launch input, or adjudication input — terminates the operation explicitly before any standing effect (INV-8); nothing commits.

[C-DOC-2] Recorded non-applicability: a well-formed exercise of a feature the pinned scenario's capability set does not advertise is adjudicated inapplicable — a successful, recorded outcome class — never an error and never conforming by default.

[C-DOC-3] All-or-nothing standing: every standing transition is complete or absent (C-RAT-4, C-CB-5); no operation leaves partial standing.

[C-DOC-4] Finding path: every observed non-conformance is dispositioned through the failure-outcome taxonomy, FO-1 through FO-5, under the FO-6 exclusion order; no path skips it.

---

## Closure check

Act coverage — each authority-restricted act of the lexicon's §2 appears in exactly one contract: ratify → Contract 1; pin → Contract 2; launch → Contract 3; emit → Contract 4; withhold → Contract 5; abort → Contract 6; retire → Contract 7; terminate externally → Contract 8; reap → Contract 9; record → Contract 10; adjudicate → Contract 11; enforce → Contract 12.

Party coverage — every party owns or appears in at least one contract: accountable authority (1, 13); corpus baseline (1, 11, 13); fixture server (2–7, 10, 14); launch harness (2, 3, 8, 9, 15); assertion suite (11, 12, 15); transcript (10); subject under test (3–5, 7, 11, 15); CI gate (12).

Deliberate absences — the corpus baseline, transcript, and subject under test bear no act, matching the lexicon's §2 closure: meaning does not act, evidence does not act, and the measured party holds no authority.

Every deferral below carries destination, authority, and trigger; an unplaced component or act is a defect of this document.

---

## Deferrals

| ID | Deferred | Destination | Authority | Binding trigger |
|---|---|---|---|---|
| D-1 | The fixture language's proper name and file extension (NC-1, NC-2) | lexicon amendment + this document | accountable authority | before corpus-baseline ratification |
| D-2 | The fixture-language assertion keyword (F-27 gap) | lexicon amendment + fixture corpus | accountable authority | before corpus-baseline ratification |
| D-3 | Configured-bound values — delays, waits, startup budgets (NC-4) | scenario data + amendment here | accountable authority | the first guarantee that materially depends on a numeric bound |
| D-4 | The supported operating-system set | amendment to C-ENF-2 | accountable authority | before the CI gate first enforces a cross-platform reproduction adjudication |
| D-5 | A framing-fault scenario — invalid message framing as distinct from an impermissible payload | lexicon + this document | accountable authority | a scenario requiring invalid framing is proposed |
| D-6 | A stale-work scenario over earlier document versions | lexicon + this document | accountable authority | stale work enters scope with the exact version relation stated |
| D-7 | The persistent form of adjudicated outcomes and their stated evidence | this document + tooling under it | accountable authority | before the CI gate's enforcement is switched on |

---

## Resolutions

No unresolved markers remain. C-ADJ-6, the FO-4 exclusion mechanism, is resolved under the accountable authority's direction of 2026-07-30 to proceed with recorded defaults; its term **suite-assurance adjudication** is admitted by the lexicon (Draft 4, 7F). The accountable authority's later explicit direction supersedes any default here immediately (C-RAT-3).

---

*LanguageServerFixture · System Contracts · DRAFT 2 · 2026-07-30 01:38 UTC · authored under Lexicon DRAFT 4 · not ratified*
