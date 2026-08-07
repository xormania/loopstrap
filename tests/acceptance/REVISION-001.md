# Acceptance revision 001

The harness-certification test basis replaced the former `available` field with
owner-controlled `enabled` state plus an external, machine-derived
certification authority. The affected Treatment fixtures and end-to-end system
setup now supply immutable mock certification receipts. The behavioral claims
remain the same except that TREAT-01 and TREAT-04 explicitly distinguish owner
enablement from certification. No compatibility path for `available` remains.
