# Certification basis revision 004

Three negative oracles were missing from otherwise-green certification claims:

- `CERT-IDENT-02` recorded an executable digest but did not alter the executable
  afterward;
- `CERT-CONFORM-01` did not prove false or incomplete observations refuse;
- `CERT-CONFORM-03` did not try to reuse a dispatch ID with different usage.

The witnesses now mutate the executable bytes, fail and truncate conformance
observations, and conflict a repeated usage charge. The requirements are
unchanged; checkpoint 01 retains the original preimplementation basis.
