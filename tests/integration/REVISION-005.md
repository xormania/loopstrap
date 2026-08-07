# Integration revision 005

Deterministic integration fixtures now create machine-owned mock certification
receipts and pass the resulting authority into the system facade. The boolean
schema negative case targets `enabled`; the obsolete `available` field is not
accepted.
