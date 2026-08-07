---
name: lane-classification
description: Decide whether an artifact belongs to the development lane or the production lane. Use before adding any file to contract/, spec/cue/, skills/, config/ or tests/, and whenever a check seems to belong in two places at once.
---

# Which lane does this belong to?

Loopstrap keeps two lanes apart. Getting the line wrong is the most expensive
mistake available here, because a lane violation is invisible until something
that should have been impossible happens.

```
production        what loopstrap BUILDS with, and ships
  spec/cue/       #ProjectPackage, #ContractGraph, #EvidenceRecord …
  config/         role treatments, harness profiles, workflow
  loopstrap_core/ the kernel

development       what loopstrap is BUILT with, and never ships
  contract/       C-SCHEMA, C-CONFIG, C-CLI, C-SERENA invariants
  probe/          vendor interrogation
  .claude/skills/  this file
  tests/          the battery
```

## The test

Ask these in order. The first one that answers, answers.

**1. Would this be wrong in a different repository?**
A rule about `loopstrap_core`'s exact-field sets is meaningless elsewhere —
development. A definition of what a well-formed project contract looks like is
true anywhere — production.

**2. Does a product-building agent get *worse* for reading it?**
Not just "does it need it" — worse. Context spent on loopstrap's seal mechanics
is context not spent on the thing being built, and it invites an agent to reason
about machinery it cannot see. If reading it is a net negative, it is development.

**3. Does it name loopstrap's own machinery?**
`seal-tree.py`, `FROZEN.sha256`, `C-CONFIG-001`, `probe/run.sh` — development.
A production artifact can name `#CellContract` because that is the vocabulary it
hands to whoever is building.

**4. Would it survive loopstrap being replaced?**
The contract language survives; the thing that checks loopstrap's own config does
not.

## The subtlety that catches people

**An artifact's lane and its checker's lane can differ.**

`config/serena.v1.json` is production — it binds roles that run in the loop.
`contract/invariant_serena.cue` is development — it checks that production config
for contradictions. The config ships; the check never does.

So "what lane is this file?" is two questions, and answering only the first is
how a development expectation ends up in a shipped package. State both:

> `config/harness-cli.v1.json` is production data, checked by development
> invariants in `contract/invariant_harness_cli.cue`.

## Worked cases from this repository

| artifact | lane | why |
| --- | --- | --- |
| `spec/cue/contracts.cue` | production | defines what any project's contract graph must look like |
| `contract/invariant_schema.cue` | development | checks *this* kernel's Python against *this* kernel's CUE |
| `contract/schema_harness_surface.cue` | development | describes a probe deliverable, which is loopstrap-internal |
| `config/serena.v1.json` | production | binds roles the loop dispatches |
| `probe/` | development | interrogates vendors to populate loopstrap's own config |
| `tests/readiness/` | development | witnesses loopstrap's behaviour |
| `.loopstrap/roles/*.md` | production | tells a dispatched role who it is |

## Two failures this test would have prevented

**A test oracle in the production package.** A CUE file asserting expected values
for one test case was written with `package evidence` — the same package as the
shipped schema. Separate file, shared namespace: a development expectation could
unify into the production contract surface. Test 1 catches it (the expectation is
meaningless in another repo); the fix was its own package name.

**A config read by something that travels.** Seal exclusions were moved into
`config/seal.v1.json` and read at runtime by `verify-tree.py` — which `ops/land.sh`
ships alone inside a courier, to a tree carrying no config. The battery caught it
as 14 register-map violations. Test 4 catches it earlier: the verifier must
survive being separated from this repository, so it cannot depend on this
repository's files. The fix was to compile the config into the tool.

## When it is genuinely both

It is not. If something seems to belong to both lanes, it is two things that have
not been separated yet. Split it, name the halves, and state each one's lane —
that separation is usually the actual work.

## Check yourself

```shell
# The development package is `contract`, singular. Production uses `contracts`,
# `evidence`, `project`. Anchor the match — an unanchored grep for
# "^package contract" matches "package contracts" and reports the legitimate
# production file, which is how this check first went wrong.
grep -l '^package contract$' spec/cue/*.cue       # must find nothing

# production must not reference development machinery
grep -rn 'contract/\|probe/\|FROZEN' spec/cue/ loopstrap_core/   # must find nothing
```

Both are cheap enough to run whenever the question comes up. Note the anchor:
a check that reports a false positive on the first honest file gets ignored by
the second week, which makes it worse than no check.
