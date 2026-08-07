# Certification basis revision 006

The owner corrected the runtime ontology: a Role is a responsibility such as
Planner or Implementer, while a Role-Treatment is the harness-specific
realization of that Role. Harness and model provider are independent because a
model can be routed through a different vendor's harness.

The certification basis now additionally requires:

- structured Role-Treatment identity for Role, harness, provider/model route,
  native reasoning control, expected wire value, orchestration, wrapper, and
  role-specific configuration;
- a Role-Treatment cannot be assigned to a different Role;
- two Roles using the same harness and model remain distinct certification
  units;
- one common wrapper contract with three harness-native CLI compilers;
- fail-closed configuration isolation and invocation overrides;
- separate requested, sent, and observed launch evidence, with fallback,
  hidden configuration, model substitution, and unproved reasoning refused.

This extends the existing nineteen claims. It does not weaken any prior
certification boundary.
