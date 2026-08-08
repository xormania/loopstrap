---
description: One-screen summary of the repository — gates, branch, budget, pins, what is open
---
Report the state of this repository in one screen. **Read-only: change nothing,
fix nothing, and do not run the battery** — it takes 48 seconds and this is a
status, not a verification. If something is red, say so and stop; the operator
decides what to do about it.

Run these, in this order. Together they take under three seconds plus one network
call.

```shell
python3 artifacts/instance/tools/verify-tree.py
bash artifacts/instance/tools/contract-check.sh
git status --porcelain | wc -l
git log --oneline -1
git rev-list --count origin/main..origin/dev
gh pr list --state open --json number,title,isDraft,baseRefName
python3 artifacts/instance/tools/pin-check.py --check
```

Then present exactly this, filled in — no preamble, no closing summary:

```
TREE      <verified | the failure line>
GATE      <the contract-check summary line, verbatim>
BRANCH    <name> · <n> uncommitted · dev is <n> ahead of main
OPEN      <#n title (draft?)> per line, or "none"
PINS      <n behind: names> or "current"
```

Then, and only if any apply, a short **Needs attention** list. Include an item
only when it is actionable now:

- the tree does not verify, or the gate has diagnostics
- uncommitted paths exist (name the count, not the files)
- a pin is behind by a **major** version
- `dev` is ahead of `main` with no open promotion pull request
- an open pull request is red

Rules for the report:

- **Deferred gate findings are pre-existing.** Two of them concern roles reaching
  a harness its own profile rules out. Report the count; never present them as new.
- **Echo the gate's own summary line; do not re-derive anything from it.** It
  already carries the invariant count against its cap. Reading the budget file
  separately only creates a second number that can disagree with the first.
- **Report nothing about the loop** — whether it is armed, which treatments
  exist, what a run would do. That is the product's state, not this repository's,
  and no decision made here turns on it.
- Do not offer to fix anything unless asked. Do not speculate about causes.
- If `gh` is unavailable, print `OPEN unavailable` rather than omitting the line —
  "could not check" and "nothing open" are different answers.

Open work lives in `proj/handoff/`; mention it only if the operator asks what to
do next.
