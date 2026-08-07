# Certification basis revision 002

The original `CERT-CONFORM-01` witness passed a hand-constructed conformance
observation to the evaluator. That proved the observation schema, but not the
claim's required real Loopstrap path.

The witness now executes a bounded deterministic harness through
`LoopstrapSystem`, verifies structured parsing, workspace mutation, raw-output
custody, exact usage charging, independent Cell/root evidence and acceptance,
then reopens the run and proves the completed dispatch is reused without a
second completion or charge. The claim text and acceptance boundary are
unchanged. Checkpoint 01 preserves the original preimplementation basis.
