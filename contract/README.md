# Development contract

Static coherence checks over this repository. They run in under a second and
reach a verdict before any suite starts.

## Two different uses of CUE

Loopstrap uses CUE twice, and the two must never be confused.

**Production.** `spec/cue/` holds the shipped contract — `#ProjectPackage`,
`#ContractGraph`, `#EvidenceRecord`, `#AcceptanceRequest` and the rest. The
kernel loads it at runtime through `loopstrap_core.specification.CUECompiler`,
against the binary pinned in `config/cue-tool.v1.json`. It is sealed, it is
frozen test input, and it contains no development expectation.

**Development.** `contract/` holds this package. It is never loaded by
`loopstrap_core`, never shipped, and uses its own package name (`contract`, not
`evidence` or `contracts`), so a development expectation cannot unify into the
production contract surface even by accident.

A file in one lane may be read by the other lane's tooling. Neither lane's
*definitions* may leak into the other's namespace.

## Authority

Each fact is obtained from whichever source actually owns it:

- **Python is authoritative about Python.** Every `FIELDS = {...}` attribute and
  every `_exact(data, <set>, "<label>")` call site is read with `ast`, never with
  a regular expression, so a reformat cannot change a fact.
- **CUE is authoritative about CUE.** Definition field names come from
  `cue eval -e '[for k, _ in #Def {k}]'` — the compiler's own answer, which
  already excludes hidden fields and optional fields.
- **The pairing is declared.** Which Python field set describes the same document
  as which CUE definition cannot be inferred; `EvidenceRecord` matching
  `#EvidenceRecord` is a naming coincidence and `"port contract"` matching
  `#Port` is not a name match at all. `declaration_schema_pairs.cue` records it,
  with a reason per pair, and `C-SCHEMA-002` fails if either side is renamed.

## What it proves, and what it does not

These invariants prove that two independently-written schema descriptions of the
same document agree on field names. They do not prove that a document validates,
that a subcommand succeeds, or that evidence is adjudicated correctly. Those are
behavioral claims and `tests/readiness/test_cli_bridge.py` owns them.

The defect this exists to catch shipped for a week behind a green battery:
`spec/cue/evidence.cue` required `treatment_id` while `loopstrap_core/evidence.py`
required `role_treatment_id`, and `EvidenceCompiler` ran both over one document.
No evidence record could satisfy both, so `acceptance-check` could not accept any
input. See `tests/readiness/REVISION-008.md`.

## Run it

```shell
bash artifacts/instance/tools/contract-check.sh
```

Exit 0 with `CONTRACT CLEAN`, or exit 1 listing every diagnostic as
`<id> <subject>: <reason>`. An empty diagnostic map is the pass condition; every
invariant yields a map of subject to reason rather than a boolean, so a failure
names the offender instead of reporting that something, somewhere, is wrong.

## Diagnostics

| id | meaning |
| --- | --- |
| `C-SCHEMA-001` | a declared pair disagrees on required field names |
| `C-SCHEMA-002` | a declared pair names a Python label or CUE definition that does not exist, or is ambiguous |
| `C-SCHEMA-003` | an extracted Python field set is neither paired nor declared unpaired |
| `C-SCHEMA-004` | an `_exact()` call site became unresolvable and is not waived |
