# Readiness test-basis revision 004

## Defect

The competing-promotion setup attempted promotion immediately after
verification. Loopstrap already and correctly requires accepted post-result
review before any promotion, so the test stopped at that older safety boundary
instead of exercising its stated stale-candidate conflict claim.

## Correction

Both independently verified child candidates now receive accepted,
evidence-backed post-result reviews before the first promotion. The second
promotion therefore reaches the intended compare-and-swap conflict.

No claim or expected conflict behavior changed.
