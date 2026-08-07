# Loopstrap telemetry mirror

Each run owns `telemetry.sqlite3` beside its authoritative `events.jsonl`.
SQLite is an append-only observation mirror for later empirical analysis. The
kernel never reads it to reconstruct state or decide execution, verification,
acceptance, recovery, or promotion.

## Capture rule

Preserve every observable value before reduction. Unknown or unavailable values
remain explicit observations; they are never replaced with zero. Derived
metrics, cost models, routing policies, and optimization formulas remain outside
the collector so they can change without rewriting historical evidence.

The mirror currently captures:

- every complete ledger record in ledger sequence and hash-chain order;
- independent collection order, UTC capture time, source time, source sequence,
  source hash, and monotonic time where the producing boundary exposes it;
- run, Cell, work-unit, attempt, Role, and Role-Treatment dimensions;
- explicit parent and cause event relationships;
- exact effective and static Role-Treatment copies, including harness,
  provider/model route, reasoning control, orchestration, wrapper,
  configuration, capabilities, and command identity;
- harness request bindings, prompt/context references, cache lineage, execution
  bounds, effective environment keys, and live-execution flags;
- process argument vector, working directory, PID, environment-value digests,
  UTC start/end, monotonic start/end, nanosecond duration, return code,
  termination class, stream sizes, and stream digests;
- every reported usage field, including previously unknown vendor fields, plus
  an explicit unavailable row for each expected field the harness did not
  report;
- verification command receipts, exit verdicts, stream byte counts and digests,
  per-command timing, aggregate timing, workspace path, and report reference;
- every digest-shaped reference and every path exposed by payload or context,
  with point-in-time existence, type, mode, size, and modification time;
- available artifact bytes, redacted raw-execution bytes, snapshot manifests,
  and individual snapshot file bytes, content-deduplicated by SHA-256.

Structured credential-shaped payloads are rejected. Harness stdout and stderr
enter the mirror only after the existing raw-execution custodian redacts them
and stores the sanitized artifact.

## Schema

| Table | Observation |
| --- | --- |
| `telemetry_events` | Canonical raw event/context copies, all ordering and identity dimensions |
| `telemetry_relationships` | Parent and causal edges |
| `telemetry_measurements` | Observed/unavailable usage, cost, timing, and verification values |
| `telemetry_role_treatments` | Deduplicated effective/static treatment identities |
| `telemetry_event_treatments` | Event-to-treatment relationships |
| `telemetry_references` | Event JSON path to content reference |
| `telemetry_reference_observations` | Captured/unavailable reference observations |
| `telemetry_paths` | Point-in-time path metadata |
| `telemetry_blobs` | Deduplicated available bytes |
| `telemetry_blob_sources` | Every observed source path and event for a blob |
| `telemetry_snapshots` | Snapshot manifests and capture paths |
| `telemetry_snapshot_entries` | Per-path snapshot inventory and file-blob relationships |

Every data table has update/delete refusal triggers. Event rows are digest-bound,
blob bytes are rehashed during verification, snapshot manifests are checked
against their snapshot references, and each run's collection sequence must be
gap-free.

## Present observability limits

Loopstrap can retain only what the harness or deterministic boundary exposes.
Provider-internal reasoning, cache behavior, tool calls, token categories, and
pricing details remain unavailable when the selected harness does not report
them. Prompt and context bytes are copied when their references resolve to
available artifacts; otherwise the exact reference and unavailable observation
remain. These are data-source gaps, not zero-valued measurements.
