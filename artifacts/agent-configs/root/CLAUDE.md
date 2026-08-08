# Working on Loopstrap

This file is for **developing this repository**. It is not loop operating
doctrine — how a run is conducted lives in `artifacts/instance/`, and none of it
is in force here.

**New here?** `.agents/README.md` is a three-file welcome mat: the standing of
everything under `artifacts/`, where things are, and the exact commands for the
usual jobs.

## What you are working on

`loopstrap_core` is the deterministic kernel, driven by versioned data in
`config/`. It is **deliberately unarmed**: role assignments and live
Role-Treatment certification receipts are future inputs, and launch fails closed
without them. Nothing here launches a model at anything.

The repository root is also the instance root today. Making Loopstrap a genuinely
installable app is in-flight work, and the open design question — what an
installed instance is *given* versus what is one deployment's own vocabulary — is
recorded in `proj/handoff/02-installable-app.md`.

## The rules

`CONTRIBUTING.md` holds all six under *Working in this tree*. The two that catch
people:

- **Reseal after every change.** `artifacts/instance/tools/seal-tree.py .`, then
  read the delta. The manifest is exhaustive — an unlisted file is an error.
- **Every control has a path from red to green** (`L48`). A check that refuses
  correct work is the defect, not the work. Fix it; never bypass it.

`/check` runs the seal, the gate and the battery in one step.

## Invariants you must not break while changing code

These are properties of the kernel, not instructions to a loop. Breaking one is a
defect even if every test still passes.

- **Frozen tests are not adjustable.** Six suites under `tests/acceptance`,
  `tests/active`, `tests/integration`, `tests/telemetry`, `tests/readiness` and
  `tests/certification` are pinned by hash. Never weaken one to make an
  implementation pass; a test-basis defect needs a recorded `REVISION-NNN.md`
  stating the defect before its replacement is frozen.
- **Telemetry is an observation mirror, never a source.** No control, replay,
  recovery, verification, acceptance or promotion path may read from
  `telemetry.sqlite3`. Do not add one. Credential-shaped structured data and
  unredacted harness streams stay prohibited.
- **Role-Treatments are never silently substituted.** A Role names a
  responsibility; a Role-Treatment binds it to an exact harness, provider/model
  route, reasoning control, wrapper and configuration. Harness and provider are
  independent identity fields.
- **Recursion is data.** No hard-coded task count or depth.
- **The executor is the sole promotion path.** Writes go to isolated disposable
  workspaces.

## `artifacts/` carries a standing, not an age

**Authority** is cited and enforced — `registers/`, `agent-configs/`,
`instance/tools/`; the battery fails if a cited register id is absent. **Method**
is transferable technique, never executed. **Record** is evidence of one past
run. An unmarked file that reads as a specification is the hazard; check the
standing before treating anything there as binding.

## This harness

Skills and slash commands are in `.claude/`. Serena is configured project
read-only, so it is for `find_symbol` and `find_referencing_symbols` rather than
editing. The commit hooks run a fail-closed publication check — if one refuses a
commit, read `.claude/skills/publication-check/SKILL.md` before working around it.
