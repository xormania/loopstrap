# Readiness test-basis revision 002

## Defect

The responsibility-mode test changed each guarantee’s project-contract
reference without changing the enclosing Cell’s declared `contract_refs`.
Correct referential validation therefore rejected an undeclared reference
before the test could reach its intended shared-versus-exclusive assertion.

## Correction

The positive and negative mutations now change both the Cell declaration and
the guarantee reference. No claim, responsibility expectation, or production
interface changed.
