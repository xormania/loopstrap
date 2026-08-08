# Loopstrap implementation surface

**New here?** `.agents/README.md` is a three-file welcome mat: the standing of
everything under `artifacts/`, where things are, and the exact commands for the
usual jobs.

This directory is the Loopstrap source root. The active deterministic kernel is
`loopstrap_core`; versioned runtime selections live under `config/`.

Work on Loopstrap itself is allowed here when the owner requests it. Preserve the
tests-first boundary:

1. verify the freezes under `tests/acceptance`, `tests/active`,
   `tests/integration`, `tests/telemetry`, `tests/readiness`, and
   `tests/certification`;
2. make implementation or integration changes;
3. run `tests/battery.sh` and `tests/mutation-check.sh`;
4. report any untested or live-only boundary explicitly.

The Conductor coordinates transitions and dispatch. It has no filesystem,
promotion, Git, or model-execution authority. Agents may write only to isolated
disposable workspaces; the deterministic executor is the sole promotion path.

`telemetry.sqlite3` is an append-only observation mirror, never an execution,
recovery, acceptance, or promotion source. Preserve every observable event,
timestamp, duration, path, process trace, relationship, usage value, explicit
unavailable value, content reference, and available byte copy. Large and
repeated bytes remain digest-deduplicated inside the mirror; credential-shaped
structured data and unredacted harness streams remain prohibited.

Files under `artifacts/` carry a standing rather than an age. **Authority** is
cited by an active check or versioned configuration and is binding. **Method**
is technique, never executed. **Record** is evidence of one past run and is
never runtime authority. Check which before relying on anything there. Roles name responsibilities; Role-Treatments bind those
responsibilities to an exact harness, provider/model route, native reasoning
control, wrapper, and configuration. The three governing design documents and
live Role-Treatment receipts are intentionally not present yet, so the system
must remain unarmed.
