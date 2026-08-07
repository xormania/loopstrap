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
- `TELEMETRY.md` — observation boundary, schema, captured data, and current gaps
- `artifacts/` — legacy project material retained as evidence and for utilities
  still covered by tests

Each run writes an append-only `telemetry.sqlite3` alongside its authoritative
hash-chained ledger. The database copies every observable sanitized event,
timing, path, relationship, usage field, content reference, and available
digest-deduplicated artifact/snapshot byte sequence for later analysis. It is
never consulted for execution, replay, recovery, acceptance, or promotion.

Run `tests/battery.sh` for the deterministic battery. Live model execution is
never an implicit fallback and must be enabled only after explicit certification.
