# Readiness test-basis revision 005

## Gap

The raw-execution claim initially exercised the credential-safe custodian
directly, but did not prove that the active harness dispatch path actually used
that custodian. A correct standalone component could therefore coexist with a
dispatcher that still discarded raw stdout and stderr.

## Correction

The same frozen claim now also dispatches the deterministic mock harness through
`LoopstrapSystem`, verifies that the returned execution reference resolves to
retained raw output, and confirms that the completion event carries that exact
reference.

The claim meaning did not change; its integration witness was completed.
