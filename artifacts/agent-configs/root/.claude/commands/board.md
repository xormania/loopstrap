---
description: Refresh the fleet board from live run state
---
Refresh `artifacts/campaigns/board.md` (instance §2, §9). For each member repo: read `plan/HALTED.md` (present? content?), the `plan/backlog.md` Run-state table, and the newest `plan/claims/*`; check open PRs and CI verdicts via read-only `gh`. Update rows only where state actually transitioned: campaign, state (per instance §2), blocker/prerequisite, next act, whose move; bump the refresh date. Show me the board diff before writing; cite file+line for every changed cell. No other writes; no git/gh mutations.
