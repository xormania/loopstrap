# Readiness test-basis revision 003

## Defect

The scripted driver result supplied integration evidence for the `children`
phase. In the versioned workflow, `children` has no role and transitions to the
separate `integration` phase, which is assigned to the integrator. Treating the
children wait-state as the integration result would bypass that configured
role.

## Correction

The scripted result now supplies the same evidence for the `integration`
phase. The driver is responsible for deterministically entering that phase only
after all child Cells close.

No claim or expected end state changed.
