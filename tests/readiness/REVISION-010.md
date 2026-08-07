# Readiness test-basis revision 010

## Defect

A composite naming `cell_id` declares itself the *interior* of that Cell. A
parent composite wiring that Cell wires it by the Cell's own declared ports —
which is the entire reason the construction is worth having, because it is what
lets a Cell stand in for its decomposition and a decomposition stand in for its
Cell.

Nothing required the two boundaries to agree. The existing check verified only
that each external reference names a real port of a member, so an interior could
expose a boundary the Cell it implements does not have:

    cell.first    inputs  [schema.totally.different]
    its interior  external_inputs  2 ports, both schema.document   -> ACCEPTED

The parent then wires one contract while a different one executes. Revision 009
closed two referential gaps in the same graph; those were hygiene. This is the
substitutability condition, and without it the recursion in revision 009 is
guaranteed to terminate on something that need not mean anything.

## Correction

`READY-CONTRACT-08`. For every composite declared as an interior, the exposed
external port schemas must equal the controlling Cell's declared port schemas,
positionally, for inputs and outputs alike.

Bijection rather than subset, in both directions, because neither direction is
a legitimate freedom. A declared port the interior cannot receive is a promise
nothing keeps. An exposed port the Cell never declares is an entry no parent can
reach.

Correspondence is positional and by schema so that no new schema field is
required — a named port mapping is the more explicit rule, but it would add a
required field, which moves an `_exact` field set, a declared pair, and
`C-SCHEMA-001` with it. That is the upgrade path if positional ordering proves
too implicit in use; it is not this change.

Unlike the containment walk in revision 009, this check is **local** — one
composite against one Cell, no transitive closure — so it is mirrored in CUE as
`_interiorBoundaries` and both producers now refuse it:

    _interiorBoundaries."composite.inner".inputs.0: conflicting values
      "schema.unrelated" and "schema.document"
    _interiorBoundaries."composite.inner".inputs: incompatible list lengths (1 and 2)

List unification supplies both halves of the rule at once: equal length and
equal elements. Presence of the optional `cell_id` is tested by iterating the
composite's own fields, which needs no existence operator.

Confirmed by mutation. Two weakened implementations, arity-only and schema-only,
are each killed by a different assertion in the test — which is why the test
carries three and not two.

The containment fixture from revision 009 is made boundary-conformant, so the
cyclic graph is still refused for the cycle and not for a boundary that happens
to disagree. `READY-CONTRACT-07` continues to pass unchanged.

## Deliberately not added

Everything left open by revision 009 stays open: reachability from
`root_composite_id`, dependency cycles, and dataflow cycles. Nothing learned
here bears on any of them.

Preventive, like the two before it. Nothing in the repository exercises the
containment recursion yet — the shipped fixture leaves `cell_id` absent
throughout. The check is here because the model declares the construction, and
an unsound composition rule is not discovered by testing the composition; it is
discovered when something built on top of it disagrees with itself.

No existing claim, fixture, or expected verdict changed, and no frozen input is
added. One claim is added, `READY-CONTRACT-08`.
