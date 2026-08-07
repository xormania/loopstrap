# Integration test-basis revision 002

The revision-001 test source hash was
`73a0b9707101c1b7425658bdf53b8d14f5f36cffd04281cb77fee1975e01ac79`.

Claim SYS-08 said verification was digest-bound, but its test exercised only a
matching plan. That positive path could not detect removal of the mismatch
refusal. The test now first submits a different visible-plan digest, requires a
`PromotionError`, and verifies that the cell remains in implementation before
running the matching plan.

No production behavior or claim text changed. This is an oracle-strengthening
revision identified during mutation design.
