# Loopstrap

Loopstrap is a tests-first, evidence-producing agentic workflow kernel for
designing and building software from a system contract.

The current implementation is deliberately unarmed. Its deterministic core,
mock-harness path, harness-certification subsystem, and failure behavior are
testable now; owner-selected role assignments, governing documents, and live
Role-Treatment certification receipts remain future inputs.

Key paths:

- `loopstrap_core/` — authority, workflow, evidence ledger, workspace,
  CUE specification/contract compilation, recursive driver, harness, evidence
  acceptance, recovery, budget, corpus, execution kernel, and non-authoritative
  SQLite observation mirror
- `config/` — versioned workflow, Role-Treatment registry, owner role bindings,
  and certification contract
- `.loopstrap/roles/` — role authority and responsibility doctrine loaded by
  the harness-specific Role-Treatments
- `spec/cue/` — reusable project, Cell/composite, and evidence schemas
- `tools/cue/` — exact version- and digest-pinned CUE executable
- `tests/acceptance/` — frozen behavioral claims for the core
- `tests/active/` — frozen claims for the active root and configuration surface
- `tests/integration/` — frozen cross-component and recursive execution claims
- `tests/telemetry/` — frozen exhaustive-observation, ordering, relationship,
  path/process trace, unavailable-value, and byte-copy claims
- `tests/readiness/` — frozen CUE, contract, driver, recovery, and evidence claims
- `tests/certification/` — frozen Role-Treatment identity, native wrapper,
  mechanical/inference method, and Loopstrap conformance claims
- `tests/battery.sh` — deterministic change detector
- `tests/mutation-check.sh` — sampled causal checks against detector blindness
- `tests/cases/` — battery cases, each assertion mapped to a register ruling
- `TELEMETRY.md` — observation boundary, schema, captured data, and current gaps

The tree is sealed. `loopstrap.manifest` and `loopstrap.modes` list every file
with a sha256 and a mode, and the listing is *exhaustive* — an unlisted file is an
error, not an omission. Regenerate with
`artifacts/instance/tools/seal-tree.py` after any change and read the delta; never
edit either by hand, and never hand-resolve a merge conflict in them.

- `artifacts/instance/tools/` — the working toolchain: the seal, the contract
  gate, the publication check, the pin checker, the consistency audit
- `ops/` — operator scripts and the git hooks. `setup.sh` and `launch-loop.sh`
  stay at the root because they are what a person runs first
- `contract/` — CUE package `contract`: the gate's invariants and the facts they
  read. Dev-lane CUE, distinct from the production schemas in `spec/cue/`
- `.agents/` — orientation for any agent working here, vendor-neutral
- `.claude/`, `.codex/` — harness surfaces. Skills, commands, settings for Claude
  Code, which grok also reads; a single adapter for codex
- `.serena/` — symbolic navigation, project read-only
- `artifacts/` — material carrying one of three standings: **authority** (cited
  and enforced), **method** (transferable technique, never executed), and
  **record** (evidence of one past run). Age is not a standing; check which
  before treating anything there as binding

Each run writes an append-only `telemetry.sqlite3` alongside its authoritative
hash-chained ledger. The database copies every observable sanitized event,
timing, path, relationship, usage field, content reference, and available
digest-deduplicated artifact/snapshot byte sequence for later analysis. It is
never consulted for execution, replay, recovery, acceptance, or promotion.

Run `tests/battery.sh` for the deterministic battery. Live model execution is
never an implicit fallback and must be enabled only after explicit certification.
