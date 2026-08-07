# Loopstrap agent contract

**New here?** `.agents/README.md` is a three-file welcome mat: the standing of
everything under `artifacts/`, where things are, and the exact commands for the
usual jobs.

The active implementation is `loopstrap_core`, driven by versioned data in
`config/`. Start by verifying the frozen, externally stated expectations in
`tests/acceptance`, `tests/active`, and `tests/integration`; never weaken those
tests to make an implementation pass. A test-basis defect requires a recorded
revision before its replacement is frozen.

A Role is a responsibility such as Planner or Implementer. A Role-Treatment is
the exact harness-specific realization assigned to that Role; harness and model
provider are independent identity fields. Record the Role, harness, provider
and resolved model, native reasoning control, orchestration mode, wrapper,
effective configuration, context lineage, prompt, and response evidence for
every invocation. Do not silently substitute a Role-Treatment. An adversarial
review that requires independence must use both a different Role-Treatment and
a different context lineage or the Cell parks.

The recursive workflow is data, not a hard-coded task count or depth. Every cell
begins from a contract, freezes obligation-mapped tests before planning, receives
a decomposition review before children or implementation, verifies results, and
receives an independent post-review before closure.

Mirror all observable runtime data to the run's append-only SQLite telemetry
store: full sanitized event copies, UTC and monotonic timing, process traces,
paths, causal and parent relationships, usage and unavailable fields, artifacts,
snapshots, and available content bytes. Telemetry is evidence for later analysis
only; no control, replay, recovery, verification, acceptance, or promotion
decision may read from it.

Material under `artifacts/` carries one of three standings, and age is not one
of them. **Authority** is cited and enforced — `registers/`, `agent-configs/`,
`instance/tools/`; the battery fails if a cited register id is absent.
**Method** is transferable technique that is never executed. **Record** is
evidence of one past run. None of it arms the current kernel, and an unmarked
file that reads as a specification is the hazard — check the standing before
treating anything there as binding. Until the governing documents and live
Role-Treatment certifications are supplied, launch must fail closed.
