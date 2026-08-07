---
argument-hint: <member>
description: Status of the active campaign on a member
---
Member: $ARGUMENTS. From `repos/$ARGUMENTS/plan/` (Run-state table is the entry point; newest claims file) plus read-only `gh` (open PRs, CI verdicts): report units merged/total, judge passes and failure classes since the last report, the unit in flight, breaker state, and anything drifting from the curated backlog's scope fence. Every claim carries file+line. Update the member's board row only; no other writes.
