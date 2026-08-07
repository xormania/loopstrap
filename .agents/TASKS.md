# How to do the usual jobs

Order matters in most of these. The commands are exact.

## Anything at all

```shell
python3 artifacts/instance/tools/seal-tree.py .     # after every change, read the delta
python3 artifacts/instance/tools/verify-tree.py     # must pass after sealing
bash artifacts/instance/tools/contract-check.sh     # the gate, ~0.4s
bash tests/battery.sh                               # the full battery, ~2min
```

`/check` runs all four in sequence and stops at the first red.

**Seal first, then run the battery.** Reversing them produces
`sealed source: tree verification failed`, which looks alarming and means only
that you added files and have not resealed.

## Change something under `tests/<suite>/`

Six suites are frozen: `acceptance`, `active`, `certification`, `integration`,
`readiness`, `telemetry`. Each is pinned by `FROZEN.sha256` with a strict
`claims.toml` / `map.tsv` bijection.

1. Write the test. Watch it **fail**, and check it fails for the reason you
   intend — a red for the wrong reason proves nothing.
2. Add the claim to `claims.toml` and the row to `map.tsv`. The bijection is
   strict; the suite runner refuses a mismatch before running anything.
3. Make it pass.
4. Write `REVISION-NNN.md` stating **the defect**, not the diff.
   `tests/readiness/REVISION-008.md` is the model.
5. Regenerate `FROZEN.sha256` for that suite, then reseal.

Adding a *file* to a suite also means adding it to `INVENTORY` in that suite's
`verify_freeze.py`.

## Add a battery case under `tests/cases/`

Every assertion label must appear verbatim in the case *and* have a row in
`tests/REGISTER-MAP.tsv` citing a register id that exists. The register map check
proves execution, cardinality and id existence, and it will tell you exactly
which of the three you got wrong.

## Add a check to the gate

Read `config/gate-budget.v1.json` first. It is **6 of 6**. Adding one means
deleting one or raising the cap deliberately, and the cap is sealed so the raise
shows in the seal delta. `gate-review.py` ranks the existing six by whether they
have ever fired.

An invariant earns its place by catching something real. Until then it is a guess
with a diagnostic code, which is what the previous twenty-nine were.

## Bump a pinned tool

```shell
python3 artifacts/instance/tools/pin-check.py --check
python3 artifacts/instance/tools/pin-check.py --update <tool>          # prints the new pin
python3 artifacts/instance/tools/pin-check.py --update <tool> --write  # applies it
```

For `cue` the pin is only half the job — the binary in `tools/cue/` has to be
fetched deliberately and the tree resealed. You are putting a new executable into
a sealed tree that the gate then runs.

## Open a pull request

Target `dev`. An agent may open a **draft** PR from `dev` to `main`; only the
owner marks it ready and merges (`L49`).

The template asks for three fenced blocks — seal delta, gate, battery — and CI
runs the same commands and compares. Paste real output; the counts are specific
to your diff, so it cannot be invented. Do not reformat it to look tidier.

Anything under `loopstrap_core/`, `spec/`, `contract/` or `tests/` also needs the
red-before-green section: the check failing before your change, and passing
after, both pasted.

## If a check refuses work you believe is correct

That is `L48` and the check is the defect. Do not reach for `--no-verify` and do
not weaken the check to pass. Establish the facts, fix the control, and add the
missing half of the pair to `tests/cases/controls-reachable.sh` — every control
must have a demonstrated path from red to green.

Three controls in this repository have shipped without one. The register entry
names them.

## Before anything leaves the machine

```shell
python3 artifacts/instance/tools/publication-check.py --file <message>
git diff --cached | python3 artifacts/instance/tools/publication-check.py --stdin
```

`bash ops/hooks/install.sh` makes it automatic on every commit. Fail-closed: no
denylist is exit 2, a blocked commit, never a passed one. The check cannot catch
a description that avoids every term — see
`.claude/skills/publication-check/SKILL.md` for the failure that has no string to
search for.
