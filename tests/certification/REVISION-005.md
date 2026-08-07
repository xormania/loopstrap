# Certification basis revision 005

The conformance witness previously reopened only after the completion event and
its following checkpoint. That left the durable ordering around completion
implicit.

The witness now proves the completed `SystemJob` is present in a verified state
checkpoint before the human-readable `harness.completed` event. It clones the
run at that exact prefix, reopens it, and requires dispatch reuse and one-time
usage accounting without a second harness invocation. This directly exercises
the completion-event interruption boundary named by `CERT-CONFORM-03`.
