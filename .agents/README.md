# Start here

A welcome mat, not doctrine. Three short files, and the most useful thing in
them is what *not* to read.

- **`MAP.md`** — every top-level directory, one line each, marked live or legacy.
- **`TASKS.md`** — the half-dozen jobs you will actually be asked to do, with the
  exact commands and the order they go in.

Vendor-neutral on purpose: Claude Code, codex and grok all work in this tree, and
this is the one orientation surface rather than three.

## What this repository is

Loopstrap is a tests-first, evidence-producing agentic workflow kernel. It builds
software from a system contract, and it is **deliberately unarmed** — the
deterministic core, the mock-harness path and the failure behaviour are testable
now; owner-selected role assignments and live certification receipts are future
inputs. Nothing here launches a model at anything.

The repository root is also the *instance* root. There is no separate deployment
checkout: `AGENTS.md`, `CLAUDE.md` and `README.md` at the root are held
byte-identical to their staged copies by the consistency audit, and the runtime
directories (`repos/`, `.worktrees/`, `xor/`, `scratch/`) exist only once it is
running and are never committed. Making it a genuinely installable app is
in-flight work, not a finished property.

## The first thing to know

`artifacts/` is 4,273 lines of markdown across 71 files, and roughly half is
cited by nothing that runs. That does not make it *legacy* — age was never the
property that mattered. What matters is **standing**, and there are three:

| standing | where | your rule |
|---|---|---|
| **authority** | `registers/`, `agent-configs/`, `instance/tools/` | obey it. The battery fails if a cited register id does not exist |
| **method** | `artifacts/methods/` — 1,089 lines of transferable technique | learn from it. Never executed, deliberately kept |
| **record** | `campaigns/`, `briefs/`, `reports/`, `intent/`, `prompts/` | evidence of one past run. Do not mistake it for current |

The hazard is not old files. It is an **unmarked** file that reads as a
specification when it is not — `artifacts/contracts/` is 956 lines of exactly
that shape for a member whose spec has not ratified. Check the standing before
you treat anything under `artifacts/` as binding.

This is the repository's own rule, from `artifacts/methods/`: *epistemic status
is part of the noun — name things by their standing in the lifecycle, not by
their content type.*

## The five rules

They live in `CONTRIBUTING.md` under *Working in this tree*, and they are short.
The one that catches everyone first:

> **Reseal after every change.** `loopstrap.manifest` lists every file with a
> sha256 and a mode, and it is exhaustive — an unlisted file is an error, not an
> omission.

If the battery reports `sealed source: tree verification failed` and every
`verify-tree` error is an unlisted addition, that is all it is. Run
`python3 artifacts/instance/tools/seal-tree.py .` and read the delta.

The one that matters most:

> **Every control has a path from red to green** (`L48`). A check that refuses
> correct work is the defect, not the work. It gets fixed, never bypassed.

## Before you touch anything

```shell
bash tests/battery.sh
```

Two minutes, and it tells you whether the tree was already green when you
arrived. Knowing that is worth more than the two minutes, because the alternative
is discovering it after your own change and not knowing which of you broke it.

`/check` runs the seal, the gate and the battery in sequence if your harness
supports slash commands.
