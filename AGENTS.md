# Working on Loopstrap

This file is for **developing this repository**. It is not loop operating
doctrine — how a run is conducted lives in `artifacts/instance/`, and none of it
is in force here.

**New here?** `.agents/README.md` is a three-file welcome mat: the standing of
everything under `artifacts/`, where things are, and the exact commands for the
usual jobs.

## What you are working on

This directory is the Loopstrap source root. `loopstrap_core` is the deterministic
kernel; versioned selections live under `config/`. It is **deliberately unarmed**
— the governing design documents and live Role-Treatment receipts are not present
yet, so the system must stay that way and launch fails closed.

Work on Loopstrap itself is allowed here when the owner requests it.

## The order of work

1. Verify the freezes under `tests/acceptance`, `tests/active`,
   `tests/integration`, `tests/telemetry`, `tests/readiness` and
   `tests/certification`.
2. Make the change.
3. Reseal — `artifacts/instance/tools/seal-tree.py .` — and read the delta. The
   manifest is exhaustive; an unlisted file is an error, not an omission.
4. Run `tests/battery.sh`, and `tests/mutation-check.sh` when the change touches
   a detector.
5. Report any untested or live-only boundary explicitly.

`CONTRIBUTING.md` holds the full six rules. The one worth repeating: **every
control has a path from red to green** (`L48`) — a check that refuses correct
work is the defect, not the work.

## Invariants you must not break while changing code

Properties of the kernel, not instructions to a loop. Breaking one is a defect
even if every test still passes.

- **Frozen tests are not adjustable.** Never weaken one to make an implementation
  pass; a test-basis defect needs a recorded `REVISION-NNN.md` stating the defect
  before its replacement is frozen.
- **Telemetry is an observation mirror, never a source.** `telemetry.sqlite3` is
  append-only and no execution, recovery, acceptance or promotion path may read
  from it. Credential-shaped structured data and unredacted harness streams stay
  prohibited; repeated bytes stay digest-deduplicated.
- **Role-Treatments are never silently substituted.** Roles name
  responsibilities; a Role-Treatment binds one to an exact harness,
  provider/model route, reasoning control, wrapper and configuration.
- **Coordination holds no authority.** Whatever coordinates transitions and
  dispatch has no filesystem, promotion, git or model-execution authority. Agents
  write only to isolated disposable workspaces, and the deterministic executor is
  the sole promotion path.

## `artifacts/` carries a standing, not an age

**Authority** is cited by an active check or versioned configuration and is
binding. **Method** is technique, never executed. **Record** is evidence of one
past run and is never runtime authority. Check which before relying on anything
there — an unmarked file that reads as a specification is the hazard.

## This harness

`.codex/config.toml` carries the project configuration and loads once the
repository is trusted. There are no slash commands on this surface; the commands
under `.claude/commands/` are read by harnesses that support them. The commit
hooks run a fail-closed publication check — if one refuses a commit, read
`.claude/skills/publication-check/SKILL.md` before working around it.
