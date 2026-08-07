# Readiness test-basis revision 001

## Defect

The supposedly valid `contract_graph_data()` fixture assigned
`contract.root` with `exclusive` responsibility to both member Cells. The
responsibility-mode test then changed both members to another shared contract
reference and expected that same duplicate-exclusive condition to fail.

The valid baseline and its negative mutation were therefore structurally
indistinguishable for the property under test.

## Correction

The second member now starts with `contract.second`. The negative case still
changes both member guarantees to `contract.exclusive`; the positive shared case
still changes both to `contract.shared`.

No claim, test method, expected outcome, or implementation surface changed.
Checkpoint 01 preserves the original frozen basis.
