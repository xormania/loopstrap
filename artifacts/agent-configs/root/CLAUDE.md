# Contributing to Loopstrap

What a contribution here must satisfy. This is not loop operating doctrine —
that lives in `artifacts/instance/` and is not in force here. It is not a guide
to the codebase either; `.agents/README.md` is, and it is three short files.

## What a change must satisfy

Seven things, each decidable by a command rather than by judgement.

| | |
|---|---|
| the tree reseals and verifies | `artifacts/instance/tools/seal-tree.py .` then `verify-tree.py` |
| the contract gate is clean | `artifacts/instance/tools/contract-check.sh` |
| the battery is green | `tests/battery.sh` |
| red before green | required for `loopstrap_core/`, `spec/`, `contract/`, `tests/` |
| the evidence matches CI's own run | the three fenced blocks in the pull request |
| nothing leaves that should not | `publication-check.py`; `ops/hooks/install.sh` makes it automatic |
| a check that refuses correct work is the defect | `L48` — fix the check, never bypass it |

```shell
python3 artifacts/instance/tools/ship.py     # runs the first three, fills the evidence blocks
```

`/check` runs the gates alone. Neither writes the argument sections; those are
yours.

## Frozen suites

Six suites are pinned by hash. Changing one requires a `REVISION-NNN.md` stating
the **defect**, not the diff, plus a regenerated manifest:

```shell
python3 artifacts/instance/tools/freeze-suite.py <suite>
```

## Two more rules with a cost attached

The contract gate holds **six invariants against a budget of six**. Adding one
costs a deletion or a deliberate cap raise, and the cap is sealed.

If your branch merges another and both touched the tree, regenerate the seal
rather than resolving `loopstrap.manifest` by hand — and regenerate the pull
request's evidence, because the counts move.

## This harness

Skills and slash commands are in `.claude/`. Serena is configured project
read-only: it is for `find_symbol` and `find_referencing_symbols`, not editing.
The commit hooks run a fail-closed publication check; if one refuses a commit,
read `.claude/skills/publication-check/SKILL.md` before working around it.
