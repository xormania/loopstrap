# Contributing

Target `dev`. `dev` → `main` is a **promotion**, not a review: every commit
reaching `dev` already carried its own evidence, so the body requirement is
skipped on that route. The battery, the contract gate and the seal still run.
Merged only by the owner.

Cross-repository pull requests are rejected. The battery runs committed tools —
including a 24MB digest-pinned CUE binary — against a hash-and-mode sealed tree,
so a fork is not a useful unit of review here. Ask for a branch.

## Before you open anything

Three commands. Run them from a clean checkout of your branch and keep the
output; the pull request template asks you to paste it, and CI runs the same
three and compares.

```shell
python3 artifacts/instance/tools/seal-tree.py .        # 1. re-seal, and say what moved
bash artifacts/instance/tools/contract-check.sh        # 2. static contract gate (~0.4s)
bash tests/battery.sh                                  # 3. the full battery
```

The comparison is the whole filter. If you ran the commands, the output is in
your terminal. If you did not, you cannot invent it — the seal delta and the
counts are specific to your diff. That is deliberate, and it is aimed at drive-by
contributions that describe work rather than do it.

Do not reformat the pasted output to look tidier. Whitespace is normalized;
edited content is not.

## If you maintain a denylist

```shell
bash ops/hooks/install.sh      # points core.hooksPath at ops/hooks
```

Two hooks then run on every commit: the message and the added lines of the
staged diff are checked against a private denylist of terms that must not leave
the machine. Optional, and only useful if you have such a list — the check is
**fail-closed**, so enabling the hooks without a denylist blocks every commit.
That is the intended behaviour: *could not check* and *checked and clean* are
different answers.

The list itself is never committed, because the list is the disclosure. See
`skills/dev/publication-check/SKILL.md` for the failure it cannot catch.

## The tree is sealed

Every file is covered by `loopstrap.manifest` with its hash and mode. Change
anything and you must re-seal:

```shell
python3 artifacts/instance/tools/seal-tree.py .
python3 artifacts/instance/tools/verify-tree.py .      # must print TREE VERIFIED
```

Sealing is loud on purpose. It names every path added, removed or changed. If
that list surprises you, stop and read it before committing — an unexpected entry
is the seal telling you something you did not intend.

Sealed does not mean immutable. It means a change cannot happen quietly.

## Show it failing first

Any change under `loopstrap_core/`, `spec/`, `contract/` or `tests/` must show
the check failing before it passes, with both commands and both outputs in the
pull request.

This is not ceremony. `spec/cue/evidence.cue` and `loopstrap_core/evidence.py`
disagreed on one field name for a week behind a green battery, and
`acceptance-check` could not accept any input at all in that time — because 115
refusal-shaped assertions were watching, and a command that refuses everything
still refuses the malformed ones. A test that has never been observed to fail has
not been shown to test anything. See `tests/readiness/REVISION-008.md`.

## Frozen suites

`tests/*/FROZEN.sha256` seals each suite's inputs so a test cannot be quietly
edited into passing. Changing one is allowed and is expected to be narrated:

1. Make the change, and add or update the claim in `claims.toml` and the row in
   `map.tsv` — the runner enforces a strict bijection between tests and claims.
2. Add the file to `INVENTORY` in that suite's `verify_freeze.py`.
3. Write `REVISION-NNN.md`: **Defect** (what was wrong), **Correction** (what
   changed), and whether any claim or expected verdict changed. Follow the shape
   of the existing ones.
4. Regenerate `FROZEN.sha256` from the inventory, then re-seal.

## What gets a pull request rejected

- Pasted output that does not match CI's run of the same command
- A weakened check used to make something pass
- A new test with no observed failing state
- A frozen suite changed without a `REVISION-NNN.md`
- Template placeholders left in the body

## Configuration is data

Vendor names, argv, model routes and seal exclusions live in `config/*.json`, not
in Python. `contract/` holds development-time invariants that check the config
set agrees with itself and with the kernel; it is a separate CUE package from the
shipped contract in `spec/cue/` and must stay that way.

If you find yourself adding a vendor name to a `.py` file, the abstraction you
want probably already exists.
