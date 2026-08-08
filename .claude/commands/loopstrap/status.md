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
python3 -c "import json;d=json.load(open('config/gate-budget.v1.json'));print(len(d['invariants']),d['max_invariants'])"
```

Then present exactly this, filled in — no preamble, no closing summary:

```
TREE      <verified | the failure line>
GATE      <n>/<cap> invariants<, at capacity if equal> · <n> diagnostics · <n> deferred
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
- **The budget being at capacity is a constraint, not a fault.** It belongs on the
  `GATE` line, which already carries the count — do not repeat it, and keep it out
  of *Needs attention*.
- Report nothing about whether the loop is armed. That is product state; no
  dev-lane decision turns on it, and `.agents/README.md` covers it as orientation.
- Do not offer to fix anything unless asked. Do not speculate about causes.
- If `gh` is unavailable, print `OPEN unavailable` rather than omitting the line —
  "could not check" and "nothing open" are different answers.

Open work lives in `proj/handoff/`; mention it only if the operator asks what to
do next.
