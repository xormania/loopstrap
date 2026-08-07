# Readiness test-basis revision 009

## Defect

`ContractGraph` models composition recursively: a composite carries an optional
`cell_id` (`controlling_cell_id`) declaring itself the *interior* of a Cell, so
containment is an edge from a Cell to the members of its interior, and depth is
reached by alternation. Nothing checked that the relation terminates.

A graph in which cell A's interior contains cell C, whose interior contains cell
A, was admitted by both producers — `ContractGraph.from_dict` and `cue vet -d
'#ContractGraph'`. No composite need contain the Cell it is the interior of, so
the cycle is not visible to any local comparison. That is a regress, not a
decomposition, and every consumer that walks the relation inherits it.

Separately, `dependencies` was parsed as a list of nonempty strings and never
resolved against anything. Not the cycle — **the referent**. A Cell could declare
a dependency on a Cell the graph never declares, and both producers accepted it,
while four referential checks for members, connections, external ports and
guarantee support sat directly beside it.

Established against live controls rather than by inspection: the shipped fixture
was accepted, a composite controlling an unknown Cell was refused, a connection
escaping membership was refused, and a connection whose port schemas disagree was
refused by `cue vet` with rc=1. The first attempt at a cyclic fixture was itself
invalid — cloned Cells reused one `contract_ref` under `exclusive`
responsibility, so the overlap check fired before the containment relation was
ever consulted, and a red for the wrong reason proves nothing.

## Correction

Two checks in `ContractGraph.validate`, two claims.

`READY-CONTRACT-06` resolves every `dependencies` entry against the declared Cell
set, and asserts both directions: a declared referent is admitted, an undeclared
one is refused. The CUE definition mirrors it through `_dependencyChecks`, using
the same `undefined field` mechanism `_connectionChecks` already relies on.

`READY-CONTRACT-07` walks containment from every Cell and refuses a Cell
reachable from its own interior, reporting the path. The fixture builds three
levels of nesting and closes the loop two hops out, with no composite ever
containing its own controlling Cell — so a check comparing a composite's members
against its controlling Cell admits it. Both graphs declare the same six Cells
and the same three composites and differ only in what one interior holds, so the
contrast isolates the cycle. The legal three-level graph is asserted as admitted
in the same test: a check that refused all nesting would otherwise pass.

Confirmed by mutation rather than by a green run. Two weakened implementations —
"a composite may not contain its own controlling Cell", and a one-hop cycle
search — both accept the cyclic graph and are killed by the test.

Containment acyclicity is not mirrored in CUE. Expressing transitive closure
there needs a declared depth bound, and adding a depth field to the schema is a
larger change than this defect warrants. The asymmetry is not new: the exclusive
responsibility check is already Python-only, and CUE stands as the shape gate
while Python carries the relational checks.

## Deliberately not added

- **Reachability from `root_composite_id`.** An island of declared-but-unwired
  Cells is still admitted. Whether a graph may declare a Cell it has not yet
  connected is a design question, not a defect, and inventing an answer here
  would be a guess with a diagnostic attached.
- **Dependency cycles.** A referent that resolves may still participate in a
  cycle. Mutual dependency between Cells is not obviously invalid, and no
  incident distinguishes the cases.
- **Dataflow cycles.** Connections may form a loop and this stays permitted.
  Feedback is legitimate in a dataflow graph; refusing it would be a preference.

Both new checks are preventive. Nothing in the repository exercised the
containment recursion — the shipped fixture leaves `cell_id` absent throughout
and the only consumer is one nested lookup in the driver — so neither has an
incident behind it in this repository. They are here because the model declares
the recursion, and a declared recursion with no termination guarantee becomes
expensive exactly when the graph is large enough that finding it by hand costs a
day.

No existing claim, fixture, or expected verdict changed. Two claims are added,
`READY-CONTRACT-06` and `READY-CONTRACT-07`.
