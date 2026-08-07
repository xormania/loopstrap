# Loopstrap test coverage and independence limits

This document describes observed receipts, not general confidence or percentage
coverage. A green battery means only that the declared witnesses passed on the
sealed source tree.

## Current sealed target

`tests/battery.sh` requires eleven independently receipted legs:

1. syntax and executable classification;
2. legacy machinery cases;
3. frozen core acceptance;
4. frozen active-surface acceptance;
5. frozen kernel integration;
6. frozen exhaustive telemetry;
7. frozen CUE and lifecycle readiness;
8. frozen harness certification;
9. wall sweep;
10. read-only consistency audit;
11. machinery/register-map reconciliation.

The target revision contains:

- 115 syntax-classified inputs: 46 shell, 68 Python, and one pinned binary;
- 105 protected machinery assertions in 11 cases, mapped 1:1 to 105 register rows;
- 45 frozen core tests covering 47 claims;
- 10 frozen active-surface tests covering 10 claims;
- 10 frozen integration tests covering 10 claims;
- 9 frozen telemetry tests covering 11 claims;
- 21 frozen readiness tests covering 21 claims;
- 26 frozen harness-certification tests covering 26 claims;
- 14 current consistency-audit observations;
- 84 isolated curated mutants in mutation-check v11.

The wall reports its own file and line counts at runtime so copied counts here do
not become a second, stale oracle.

## What each suite actually asserts

| Surface | Witness | Assertions actually made |
|---|---|---|
| Authority boundary | core acceptance | compact Conductor view rejects content-plane fields; authorizations bind run/cell/revision/role/treatment; write, Git, artifact, and promotion acts refuse; integration also proves a non-dispatch coordination act cannot start a harness |
| Workflow ordering | core acceptance | versioned phases/roles; obligation-mapped visible and holdout digests before planning; test-author context exclusion; recorded test-basis revision; pre-review before leaf/decomposition; readiness evidence; closure/reopen and nearest-ancestor routing |
| Recursive decomposition | core + integration | no fixed depth cap through eight nested cells; child IDs/owners/scope narrowing and exact obligation partition; overlapping ownership refuses; child execution, parent integration event, post-review, and closure run through the system facade |
| Specification and contract compilation | readiness | the exact CUE v0.17.0 executable is digest- and version-pinned; the three-document fixture compiles to canonical digest-bound bytes; Cell and composite Cell contract graphs validate references, ports, connections, responsibilities, guarantee support, and verification obligations |
| Unattended recursive driver | readiness | deterministic deepest-first Cell advancement; frozen tests and pre-review precede implementation; closed children precede integration; strict role-result schemas park malformed or missing work instead of guessing |
| Claims | core + integration | suspicion does not block; a reproduced verified claim does; evidence-backed resolution is required; approvals cannot outvote a counterexample; a verified claim blocks candidate promotion as well as closure |
| Role-Treatments and independence | core + active + integration + certification | complete Role-Treatment identity with independent harness and provider/model route; exact role routing with no fallback; owner enablement is separate from machine-derived certification; receipts bind the contract, full Role-Treatment identity, exact wrapper and executable bytes, all three certification layers, and primary evidence; different Role-Treatment and context lineage; strict JSON container/boolean schemas; selected first-run Role-Treatments remain owner-disabled and uncertified |
| Harness certification | certification | a shared versioned contract with distinct Codex, Claude Code, and Grok Build discovery surfaces; private unique neutral workspaces; explicit public/secret environment allowlists; machine-owned probe records; T0–T8 fresh-context inference evidence; mutation, verification, and restoration; exact external-state restoration |
| Harness process boundary | core + certification | argument vector, isolated cwd, allowlisted environment, explicit live opt-in, timeout, separate output caps, nonzero/empty/malformed/duplicate/stale/config-drift refusal, and exact request/effective/cache evidence; timeout, output overflow, nonzero process failure, and injected interruption all retain redacted partial streams without producing a completion |
| Harness trace retention | integration | structured returned artifacts and claims appear in content-addressed response evidence and the hash-chained completion event |
| Review provenance | integration | when review roles are configured, direct acceptance refuses; completed review jobs must bind the current cell/revision/role; result review receives the verified unpromoted candidate rather than the old source snapshot |
| Deterministic verification | integration | a frozen-digest mismatch refuses without advancing; matching visible and holdout commands run in the candidate workspace with argument vectors, time/output bounds, exit verdicts, latency, byte counts, and output digests; the report becomes verification evidence |
| Ledger and recovery | core + readiness | append-only sequence/hash chain; tamper, duplicate-ID conflict, credential-shaped evidence, and partial-tail detection; prefix quarantine; concurrent append total order; deterministic reservation identity; verified state checkpoints reconstruct the complete Cell graph, completed jobs, assignments, specification binding, and run controls; completed dispatches are reused |
| Artifacts/workspaces/promotion | core + integration + readiness | content-addressed immutable artifacts/snapshots; escape symlink/path refusal; isolated agent writes; executor permit; file-locked compare-and-swap; interrupted pointer replacement; stale competing promotion is refused and ledgered; failed/malformed work cannot promote |
| Evidence and acceptance | readiness | exact evidence bindings for specification, Cell revision, scope, treatment, producer, obligation, raw execution, and artifacts; independence refusal; distinct Cell/composite/root obligations; credential redaction before immutable raw-stream custody; stale, wrong-specification, incomplete, or finding-bearing acceptance refuses |
| Budget/economics seam | core + integration + certification | separate money/tokens/latency/compute/retries/risk/human-attention currencies; hard limits override marginal value; configurable shadow prices; negative, non-finite, mistyped, or unknown accounting inputs refuse; reported harness usage and latency are charged automatically once per dispatch and conflicting replay refuses |
| Exhaustive telemetry | telemetry + integration | standard-library SQLite remains a non-authoritative append-only mirror; complete ledger copies, independent collection order, UTC/monotonic/nanosecond timing, run/Cell/work-unit/attempt identity, parent/cause links, full Role-Treatment identity, process/verification traces, paths, arbitrary usage fields, explicit unavailable values, references, artifacts, snapshots, and deduplicated available bytes are retained; deletion rebuilds from authoritative stores without changing recovery |
| Corpus-decision seam | core acceptance | source hash/citation/time/proposition requirements; versioned sufficiency; conflict/insufficiency routing; only sufficient, interior, nonobservable implementation convention may auto-resolve |
| Active root | active acceptance | versioned workflow/Role-Treatment/Role files parse; six owner-assigned Role-Treatments remain disabled and uncertified; validation starts no model; ledger status verifies before replay; root docs point to the new kernel; launch fails closed before vendor lookup |
| Battery/audit | active + machinery + mutation | separate required receipts for all frozen suites, including telemetry and harness certification; audit checks source seal, six freezes, active configuration, kernel inventory, root staging, launcher refusal, and battery wiring; real audit is byte/mode read-only |
| Legacy utilities retained | machinery | landing (16 assertions), installer (13), breaker/mocks (19), docs gate (10), sovereign controls (14), custody (7), reset validation (4), wall behavior (14), status (6), audit read-only (2) |

The obsolete 12-assertion launcher happy-path case was retired. It tested a
single-runner control plane that is now intentionally unreachable. Launcher
coverage lives in frozen active acceptance and proves fail-closed behavior; no
table row claims that the new system can launch yet.

## Freeze and revision evidence

Core acceptance, active surface, kernel integration, exhaustive telemetry,
readiness, and harness-certification claim/test/map inputs have separate SHA-256
freeze manifests. Revision records remain visible because a frozen test can be
wrong or incomplete; changing a test basis is not represented as if the
original test had always said the new thing.

| Frozen suite | Revision records | Recorded basis history |
|---|---:|---|
| Core acceptance | 2 | `REVISION-001` introduced owner-controlled enablement plus external certification authority; `REVISION-002` bound the corrected Role/Role-Treatment ontology and wrapper-owned launch attestation. |
| Active surface | 3 | `REVISION-001` replaced self-asserted availability with disabled owner state; `REVISION-002` added the separate certification battery receipt; `REVISION-003` recorded all six owner assignments and the corrected Role-Treatment ontology. |
| Kernel integration | 5 | `REVISION-001` corrected the reviewer mock behavior; `REVISION-002` added the digest-mismatch oracle; `REVISION-003` migrated fixtures to Role-Treatments and launch attestations; `REVISION-004` added invalid economic-input refusals; `REVISION-005` added mock certification authority and removed the obsolete availability field. |
| Exhaustive telemetry | 0 | The preimplementation telemetry basis was frozen once and required no post-freeze test-basis correction. |
| Readiness | 7 | `REVISION-001` corrected duplicate exclusive responsibility in a valid fixture; `REVISION-002` kept responsibility mutations referentially valid; `REVISION-003` routed integration through its configured phase; `REVISION-004` supplied post-review before the stale-promotion witness; `REVISION-005` completed dispatch-path raw custody; `REVISION-006` added mock certification receipts; `REVISION-007` migrated fixtures to Role-Treatments and launch attestations. |
| Harness certification | 6 | `REVISION-001` corrected the neutral-workspace oracle; `REVISION-002` replaced synthetic conformance with a real Loopstrap Cell path; `REVISION-003` covered all four partial-custody refusal classes; `REVISION-004` added executable-drift, incomplete-conformance, and conflicting-usage oracles; `REVISION-005` proved durable completed-job checkpoint ordering; `REVISION-006` added the Role/Role-Treatment ontology and common wrapper contract. |

The integration suite began at 0/8 before implementation. The certification
suite began at 1/19. Telemetry has no `REVISION` file because its frozen basis
did not change after the initial preimplementation freeze.

## Mutation check v11

Mutation v11 first requires a green battery in a pristine copy and captures a
protected green machinery record. Every mutant runs in another copy. A machinery
product mutant must change its own `case|label` witness from PASS to FAIL or
ABSENT. Other mutants must put the named test/signature on the responsible
failing leg. An unapplied or multi-line mutation anchor is fatal. The source
hash/mode seal is reverified afterward.

The 84 mutants sample legacy utility guards, harness accounting, syntax, wall,
map and dispatcher wiring, core authority/workflow/workspace/ledger/harness/
budget/corpus behavior, all three test freezes, active configuration and
fail-closed launch, review provenance/candidate footing, decomposition
partitioning, integration events, test-basis binding, structured response
retention, budget-domain validation, CUE pinning, composite connection
compatibility, driver refusal, dispatch reuse, evidence independence and
revision binding, raw-stream redaction and dispatch custody, Role-Treatment
certification status and executable binding, receipt-gated routing, fresh
inference contexts, restoration, failed-stream custody, idempotent usage,
conformance verdicts, durable completion ordering, SQLite journaling,
append-only telemetry, credential refusal, explicit unavailable measurements,
artifact byte custody, process timing, attempt-start capture, all six freeze
manifests, and battery dispatch of telemetry, readiness, and certification.

This is a curated causal witness set, not a mutation score. Unsampled equivalent
mutants and shared-model blind spots remain possible.

## Known untested or incomplete surfaces

- The three governing documents are not present. In `config/roles.v1.json`, six
  Role assignments bind six selected Role-Treatments. All six Role-Treatments
  remain owner-disabled and uncertified, and `launch-loop.sh` is intentionally
  unarmed.
- No real Codex, Claude Code, or Grok Build adapter/CLI has been certified or run.
  Mock protocol behavior cannot establish vendor flag compatibility, model
  semantics, permission behavior, or spend reporting.
- The certification subsystem, common contract, vendor discovery adapters,
  mechanical/inference evaluators, and Loopstrap conformance project are
  mock-certified. Issuing live receipts still requires the installed,
  authenticated harnesses and owner-authorized live execution.
- The CUE project and contract schemas are proven against a deliberately small
  fixture, not the authoritative Math LSP package. Natural-language semantic
  adequacy and contradiction detection remain outside CUE.
- The recursive driver accepts strict structured role results and can bridge to
  configured harness dispatch, but the production prompt/result adapters and
  selected live treatments are not certified. Typed acceptance is available as
  a system and CLI gate; the driver does not yet manufacture acceptance evidence
  from vendor processes automatically.
- Recovery rebuilds verified checkpoints and completed work, but restart during
  an in-flight external process has not been certified against a live harness.
- Candidate compare-and-swap uses a filesystem lock, but the full system test
  exercises stale sibling promotion sequentially. Parallel merge, rebase, and
  higher-level integration policy remains undefined.
- Completed harness stdout/stderr is routed through credential redaction and
  immutable custody, and the resulting execution reference is carried in
  response evidence and completion events. Timeout, output overflow, process
  failure, and injected interruption retain safe partial streams. Encryption and
  retention duration remain owner decisions.
- Reported harness usage and latency are charged automatically and reconstructed
  idempotently on restart; unavailable vendor values remain explicitly
  unavailable. Cache lineage is recorded and checked, but there is no cache
  store or reuse policy.
- Telemetry retains every value available at the kernel boundary, including
  unknown vendor usage fields and available artifact/snapshot bytes. Provider
  internals, tool-call traces, prompt/context bytes, token categories, cache
  details, or pricing semantics that a harness does not expose remain explicit
  source gaps rather than inferred values.
- Corpus packets and sufficiency decisions are validated objects; retrieval from
  the greater computer-science corpus, freshness rules, source ranking, and
  offline fallback are not implemented.
- Disk-full, permission loss, real operating-system signal delivery,
  snapshot-store races, and general multi-process filesystem failure injection
  remain untested. Ledger appenders are the only kernel concurrency case.
- The retained reset destructive phases, setup clone/archive path, dashboards,
  watch loops, GitHub/Serena integration, breaker storm/stall wires, and
  cross-user override remain legacy-only or syntax-only as detailed by their
  machinery cases.
- Register-map checking proves an ID exists and a mapped machinery assertion ran
  once. It does not prove that the cited ruling semantically supports the
  assertion. Frozen claim maps have the same semantic-review limit.

## Independence limits

No self-authored layer is fully independent. Implementation, fixtures, claims,
assertions, mappings, mutation selection, and this prose can share one mistaken
model. Hash freezes establish temporal order and make revisions visible; they do
not make the author independent. Causal mutants kill sampled vacuity; they do not
prove that the sampled property is the right one.

The configured runtime independence rule is narrower and enforceable: a review
can require a different treatment and a different context lineage from the work
it attacks, with no silent fallback. That reduces correlated model/context
failure only after owner role assignments and live treatment certification. It
does not make this test system externally authored.

The genuinely external controls remain owner review of claim-to-evidence
mapping, clean-room use, periodic fresh-context adversarial review, multiple
model/harness treatments, and the Math LSP pilot against the future governing
documents. L44’s warning therefore remains active: green means “these declared
witnesses passed,” never “the author’s model is complete.”
