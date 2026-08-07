# Certification basis revision 003

`CERT-CONFORM-02` originally witnessed safe partial custody only for timeout.
The claim also names interruption, output overflow, and process failure.

The same frozen test now exercises all four refusal paths and requires every
raised error to carry an immutable, redacted stdout/stderr execution reference.
No success result may be produced. The claim and boundary are unchanged.
