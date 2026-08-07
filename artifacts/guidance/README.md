# guidance/ — the segment map + per-segment guidance (advisory)

**What lives here (L6).** Two artifact kinds, both prep-time, both hash-cited at kickoff:

- `segment-map.md` — the work breakdown. Segments follow the contract parties/layers
  of the member's ratified docs (`parties.txt` of its doc set, L26). **Required property: clause coverage** — every segment
  names the contract clauses it discharges, and the union covers the ratified set; a
  clause without an owner segment, or a segment without clauses, fails the map.
  Dependency order between segments is the curated backlog's spine. At prep, each
  in-scope segment's map row + memo feed a dispatched Claude Code plan handoff's
  decomposition worksheet, attacked by an adversarial plan-review handoff and
  dispositioned by the steward (L10/L12) — its accepted output IS that segment's
  slice of the backlog, cited by hash at kickoff.
- `guidance-<segment>.md` — one memo per segment: how the field does this slice —
  candidate crates with maturity notes, reference implementations worth reading, known
  failure modes, testing patterns — options + evidence + tradeoffs, dated and sourced;
  recommendations labeled as leans.

**Force (L6, firm).** Guidance advises, contracts bind, judges gate. A unit may diverge
from guidance freely — worth a line in the PR body, never a gate. Nothing here is
citable as authority over a contract clause; adopting a practice because its source is
admired is the authority-borrowing failure this line exists to kill.

**Discipline.** Drafted at Prepare (steward drafts; xor rules what needs ruling); every
memo dated + sourced; cited by path + content hash in the kickoff like every input (§7);
an uncited memo binds nothing. **TO AUTHOR** — the map derives from the ratified docs
and cannot precede them.
