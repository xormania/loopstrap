<!--
Target `dev`. dev -> main is opened the same way and merged only by the owner.

Read CONTRIBUTING.md first. The three fenced blocks below are checked
mechanically against CI's own run of the same commands. They are not a
formality: if you did not run the tools, you cannot fill them in, and CI will
say so with the exact mismatch.

Everything outside those blocks is for a human. Write it in your own words.
-->

## What this changes, and why

<!-- One paragraph. What was wrong or missing, and what the change does about it.
     If you cannot say what was wrong without describing the diff, the change
     probably is not ready. -->

## What breaks if this is wrong

<!-- Name the concrete failure. "Nothing" is an acceptable answer for a docs
     change and a red flag for anything under loopstrap_core/ or spec/. -->

## Evidence

Run these three from a clean checkout and paste the output verbatim. CI runs the
same commands and compares. Do not edit the output to look tidier — a mismatch
fails, including a mismatch you introduced by reformatting.

**1. Seal delta** — `python3 artifacts/instance/tools/seal-tree.py .`

```
PASTE THE SEALED / SEAL CHANGED LINES HERE
```

**2. Contract gate** — `bash artifacts/instance/tools/contract-check.sh`

```
PASTE THE CONTRACT CLEAN LINE HERE
```

**3. Battery** — `bash tests/battery.sh`

```
PASTE THE "N PASS · N FAIL" LINE HERE
```

## Red before green

<!-- Required for any change under loopstrap_core/, spec/, contract/ or tests/.
     Delete this section only for docs-only changes.

     Show the check FAILING before your change, and passing after. Paste both
     commands and both outputs. A test that has never been observed to fail has
     not been shown to test anything — see tests/readiness/REVISION-008.md for
     what that costs.

     If you changed a frozen suite, add the REVISION-NNN.md and say so here. -->

```
BEFORE (failing):

AFTER (passing):
```

## Checklist

- [ ] I ran all three commands above on this branch and pasted real output
- [ ] The seal is regenerated and `verify-tree.py` passes
- [ ] I have shown the change failing before it passes, or it is docs-only
- [ ] I did not weaken a check to make it pass
