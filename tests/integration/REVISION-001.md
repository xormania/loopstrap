# Integration test-basis revision 001

The preimplementation test source hash was
`5aeb23a17246bcebff84e129501f2bbb0d53b5e5ae33a2a55d2019d3979df585`.
Its reviewer treatment fixture requested mock behavior `clean`.

That behavior is outside the independently pre-existing protocol enumerated by
`tests/acceptance/mock_harness.py`; the correct no-write behavior is `echo`.
The baseline harness refusal (`exit 2`, argparse) therefore accused the fixture,
not the kernel.

Revision: replace the two reviewer-only `clean` fixture values with `echo`.
Claims, assertions, mappings, and production expectations are unchanged. This
revision occurred before the integration suite first became green.
