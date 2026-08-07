# Active-surface test-basis revision 004

## Defect

`ACTIVE-06` claimed that the root instructions *"identify the new kernel and
frozen tests and do not activate member-specific, fixed-cap, or
persistent-Conductor doctrine."* Its test asserted three positives and five
negatives. One of the positives was:

```python
self.assertIn("legacy", combined.lower())
```

**No part of the claim required that word.** It was an unclaimed assertion, and
it tested a *string* rather than the property the string was standing in for.

The property is real and worth asserting: the root instructions must tell a
reader that material under `artifacts/` is not runtime authority. The hazard is
`artifacts/contracts/` — 956 lines shaped exactly like a live specification for a
member whose spec has not ratified. A reader who takes it as binding is the
failure this assertion exists to prevent.

But "legacy" names an **age**, and age was never what made that file dangerous.
An unmarked file that reads as a specification is dangerous whether it is a day
old or a year old. Naming the property by its age let the documentation satisfy
the assertion with one word while leaving the actual distinction unstated.

## Correction

The root instructions now state the three standings any material under
`artifacts/` can carry — **authority** (cited and enforced; the battery fails if
a cited register id is absent), **method** (transferable technique, never
executed), and **record** (evidence of one past run) — and say plainly that age
is not one of them.

The assertion follows the property rather than the word:

```python
for standing in ("authority", "method", "record"):
    self.assertIn(standing, combined.lower())
```

Three required terms rather than one, each naming a distinction a reader has to
be able to make, and the claim is extended to cover them. It is strictly stronger
than the assertion it replaces: the previous form was satisfied by the single
word appearing anywhere, including in a sentence that explained nothing.

Verified red before green, and for the right reason — the failure was at the
`assertIn("legacy")` line specifically, not elsewhere in the test.

Both test methods are also renamed off the word, which moves their rows in
`map.tsv`:

```
test_root_instructions_activate_new_kernel_without_legacy_doctrine
  -> test_root_instructions_activate_the_current_kernel_and_no_member_doctrine
test_consistency_audit_checks_active_kernel_not_legacy_doctrine
  -> test_consistency_audit_checks_the_active_kernel_not_superseded_doctrine
```

`ACTIVE-08`'s text changes "legacy Conductor doctrine" to "superseded Conductor
doctrine" — the same substitution, and the more accurate word: that doctrine was
replaced by a ruling, not outgrown.

## Not changed

No expected verdict moved. The five `assertNotIn` guards are untouched, and both
tests assert exactly what they did before plus a stricter positive. No claim was
removed and none was added; `ACTIVE-06` and `ACTIVE-08` are amended in place
because the property each states is unchanged — only its expression is.

`FROZEN.sha256` is regenerated. `INVENTORY` in `verify_freeze.py` is unchanged;
no frozen input was added or removed.
