# interface-standards.md — how anything reaches xor's hands (ruled file, D48)

The design lane's compute is unlimited; xor's hands, attention, and trust are
the scarce resources (D48, composing with "attention as the scarcest
resource"). Every deliverable is priced in HIS currency. This is the gate a
script, paste, or instruction passes before it ships — no exceptions, including
under time pressure, which is when tonight proved it matters most.

## The checklist

1. **One paste, self-contained.** Writes itself (`cat > x.sh << 'XEOF'`),
   runs itself. No "create a file, edit it, then…". No placeholders to
   hand-edit — secrets are prompted (`read -rsp`), facts are read from
   `machines.md` or probed-and-printed.
2. **Verified here first.** Simulated in the design container against the
   closest reproducible state before it ever touches xor's terminal. What
   cannot be simulated is named as such, with the loud-failure path stated.
   (The one sim-verified script of the night worked first try; most of the
   unverified ones did not.)
3. **Fails loud and paste-ready.** Every failure path prints the verbatim
   underlying error plus enough state that pasting the output back IS the bug
   report. `2>/dev/null` on a decision path is a defect (swallowed-error).
4. **Effects verified, not claimed.** Every write is read back and asserted
   before PASS is printed (claim-exceeding-mechanism). Exit codes are
   corroborated by content (exit-code-trust).
5. **Fixed-string operations on literal data** (literal-vs-regex). Whole-file
   or whole-object replacement over surgical patching when in doubt.
6. **Idempotent and re-runnable.** A re-paste after a mid-failure converges;
   it never compounds.
7. **No environment guesses** (environment-assumption): unknown facts are
   asked or probed, and the probe result is printed into the record.
8. **Never touches auth plumbing.** Credential mechanics are xor's alone —
   ruled 2026-07-19. A credential gap stops the work and states the gap.
9. **Read-first on any external system.** Print live state before changing it;
   converge, don't assume a baseline (the estate divergence was found this way
   and would have bitten silently otherwise).
10. **Interaction budget stated.** The hand-off says exactly what xor will do
    ("one paste, one Enter at the trust prompt, done") — and that statement is
    kept.

## Composition with the walls

Depth-first spending never relaxes containment: the design lane still holds no
credentials, the courier (D47) is still the only code path to the live tree,
and human authority still closes every loop. Tokens buy verification and
context — never shortcuts through the architecture.

## Invocation

xor says **"interface cost"** → current deliverable stops and is re-priced
against this list before anything else happens.
