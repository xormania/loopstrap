# Integration test-basis revision 004

The revision-003 test source hash was
`e2195867775919ec151b3345fac698ada4b0ea8c670077e7790fe7e557e5f896`.

Budget review found an untested accounting escape: negative or non-finite usage
could reduce totals or evade comparisons, and negative or misspelled shadow
prices could invert the economic rule. SYS-10 and one refusal test were added
before hardening production validation.

This revision expands the claim inventory without weakening prior tests.
