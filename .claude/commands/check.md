---
description: Reseal, run the contract gate and the full battery, and report the deltas
---
Run the three checks this repository is built around, in order, and report what
moved. Stop at the first red and say what it was; do not continue past a failure
and do not attempt a fix until I have seen it.

1. `python3 artifacts/instance/tools/seal-tree.py .` — read the delta out loud.
   `UNCHANGED` is the expected result when nothing was edited. Anything added,
   removed or changed must be something I meant to do; name each one.
2. `python3 artifacts/instance/tools/verify-tree.py` — the tree must verify after
   sealing. If it does not, that is a real defect, not a chore.
3. `bash artifacts/instance/tools/contract-check.sh` — the gate. Report the
   invariant count against its budget and any diagnostics. Deferred findings are
   pre-existing; say so rather than presenting them as new.
4. `bash tests/battery.sh` — the full battery. Report the final line.

Then report, in four lines: seal delta, tree verification, gate line, battery
line. No prose beyond that unless something is red.

If the battery reports `sealed source: tree verification failed` and every
`verify-tree` error is an unlisted addition, that means files were added and the
seal was not regenerated — step 1 fixes it and there is nothing else wrong.

Do not weaken a check to make it pass. If a check refuses correct work, that is
`L48` and the check is the defect, not the work.
