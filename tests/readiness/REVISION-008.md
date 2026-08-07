# Readiness test-basis revision 008

## Defect

The operator CLI is the kernel's entire external surface, and three of its five
subcommands cross the CUE-to-Python bridge: `spec-check` through
`SpecificationCompiler`, `plan-check` through `ContractCompiler`, and
`acceptance-check` through `EvidenceCompiler`. No test in any frozen suite
invoked any of them, and `EvidenceCompiler` had no reference in `tests/` at all.
Every suite constructed records with `EvidenceRecord.from_dict`, which exercises
only the Python half of a two-language schema.

Behind that gap, `spec/cue/evidence.cue` required `treatment_id` inside a
`close()` while `loopstrap_core/evidence.py` required `role_treatment_id` in an
exact-field-set check, and `EvidenceCompiler` ran both over the same document.
The intersection was empty: no evidence record could satisfy both validators, so
`acceptance-check` could not return `accepted: true` for any input. Only a
request carrying zero evidence succeeded, and it can only ever report
`accepted: false`. The 11-leg battery was green throughout.

The suites contained 115 refusal-shaped assertions. None of them could observe
this failure, because a command that refuses every input still refuses the
malformed ones. **A suite that only proves refusals cannot detect universal
refusal.**

## Correction

`test_cli_bridge.py` adds four positive witnesses driving `loopstrap_core.cli`
directly, in process, so no PATH or interpreter discovery enters the verdict:

- `spec-check` compiles the existing frozen project fixture and returns a
  well-formed specification digest.
- `plan-check` validates a new two-cell contract graph, including the connection
  whose source and target port schemas must agree.
- `acceptance-check` returns `accepted: true` for evidence that satisfies its
  obligation. Asserting the return code alone would have caught this particular
  divergence; asserting `accepted` also catches a command that exits cleanly and
  still never accepts anything.
- The emitted record is vetted against `spec/cue/evidence.cue` itself — the
  shipped production schema rather than a test-owned restatement, which could
  drift from the contract and agree with a wrong implementation — and its exact
  key set is asserted separately, because CUE unification treats an absent list
  field and an empty list as the same value while the ledger hashes them to
  different digests.

Two fixtures are added: `fixtures/contract-graph.json` and
`fixtures/acceptance-request.json`. Both are deliberately abstract rather than
mirroring the current architecture, so a change to the real decomposition does
not churn a frozen input.

Verified causally rather than by a green run: restoring the shipped
`treatment_id` spelling in `spec/cue/evidence.cue` fails two of the four tests,
and restoring the corrected spelling returns them to passing.

No existing claim, fixture, or expected verdict changed. Four claims are added,
`READY-CLI-01` through `READY-CLI-04`.
