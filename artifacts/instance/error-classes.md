# error-classes.md — the named failure ledger (ruled file, D48)

Named so they can be invoked in two words and killed on sight. Each entry:
definition · a real instance (dated, from the record) · the guard that
mechanizes its death. New classes are appended when caught; none are deleted.
Sessions cite classes by name; "watch for &lt;class&gt;" is a complete instruction.

## The standing four (pre-2026-07-19)

**authority-conflation** — treating a summary, memory, or paraphrase as if it
carried the force of the ratified source. *Guard:* the corpus wins; cite the
file, not the recollection.

**memory-as-fact** — asserting from recall what the tree can answer.
*Instance:* nearly "added" loop-stream capture the launcher already had
(2026-07-19). *Guard:* read before claiming; silence is never believed before
re-verification.

**negative-evidence-vs-absence** — "I found nothing" read as "nothing exists."
*Instance:* Codex-verification doubt at launch minute — the work existed,
outside this project's context (2026-07-19). *Guard:* absence from context is a
statement about the context; say which.

**claim-exceeding-mechanism** — reporting an outcome the mechanism never
established. *Instances (three in one night):* sed "patched" unchanged bytes
across three estate rounds; audit silently PASSing a missing manifest;
exit-code trust on gh (see below). *Guard:* every write re-read and
byte-asserted before PASS is printed — now the standard in every tool we ship. *Worst instance (2026-07-19, D64):* ops/reset.sh's header promised "c1 residue dies structurally by fresh clones" — false; clones re-import origin's refs. A false claim in a shipped header, blessed by a sim whose fixture lacked the very refs at issue.

## Minted 2026-07-19 (run-2 arming night)

*(authority-conflation, second instance 2026-07-19: the generic loss-proof-remotes
prior overrode xor's specific "there is no c1" ruling for a whole night — a
general principle never outranks the specific ruling; when they touch, cite the
ruling or ask. → D64.)*

**environment-assumption** — acting on a guessed fact about a machine.
*Instances:* `/home/xor` "fix" that broke correct `/home/work` paths (from the
wrong box's prompt); the empty-tree hypothesis. *Guard:* `machines.md` is
required reading; unknown facts are ASKED or PROBED-and-printed, never guessed.

**swallowed-error** — discarding stderr/bodies and then reasoning about the
failure blind. *Instance:* three estate rounds guessing at a 409 that, once
printed verbatim, solved itself in one round. *Guard:* scripts print the
verbatim API/tool error on every failure path; `2>/dev/null` on a decision
path is a defect.

**literal-vs-regex** — feeding literal strings (with `[ ] * .`) to regex
engines. *Instance:* the sed loop above. *Guard:* fixed-string operations only
(`grep -F`, bash `${var/"lit"/rep}`, python `str.replace`) for literal data;
whole-file replacement over surgical patching when in doubt.

**exit-code-trust** — believing a tool's exit status over its observable
effect. *Instance:* `gh api ... || echo MISSING` that never fired on a 404.
*Guard:* detect by content (`grep '"sha"'`), verify by read-back.

**charter-not-granted** — verifying that walls deny without verifying that the
chartered surface is granted. *Instance:* the first live loop halt — dontAsk +
deny-only refused every prompt-worthy capability; W3 tested the negative
surface only. *Guard:* D46 — grants are explicit per launch; every permission
design names BOTH lists; smoke exercises both directions.

**courier-divergence** — hand-patching the live tree so it drifts from the
sealed courier. *Instance:* the whole night's fix-scripts. *Guard:* D47 —
code alters in the design lane only; `ops/land.sh` is the sole update path; live
divergence is drift, reported then landed away.

**interface-cost** — spending xor's hands, attention, or trust to save the
model effort: placeholder edits, avoidable round-trips, unverified hand-offs,
questions the transcript already answered. *Instances:* pervasive, 2026-07-19.
*Guard:* D48 — tokens are unconstrained and xor's acts are the scarce
resource; verify-here-first, one-paste self-contained deliverables, secrets
prompted, errors paste-ready. xor invokes the class by name; work stops and
re-prices.

**era-bound-rule survival** *(stratum 3 — minted 2026-07-19, xor's catch)* — a
protective rule outliving the precondition that justified it, because nothing
re-derives rules when their preconditions die. Text-greps cannot see it: the
drift lives in doctrine-in-force and operator behavior, not in files.
*Instance:* the never-delete/quarantine posture, justified only by
"custody-tangled, no backup leg," survived D39's backup leg by weeks of
guidance until xor demanded reset (→ D60). *Guard:* protective rules state
their **valid-while** condition at birth (the healthy pattern already in law —
serial-as-bootstrap, W3-as-version-bound); every drift sweep runs the third
stratum: walk the register asking, per rule, "does its stated reason still
hold against everything ruled since?" — artifacts, then text, then **doctrine**.

**pipefail-empty-extract** *(minted 2026-07-19, found by fixture execution — D65)* —
under `set -euo pipefail`, a grep-shaped extractor inside `$( )` whose legitimate
answer is *empty* (no ledger yet, no cost field on a crashed stream, an absent
optional toml key) kills the script **silently** at the assignment. *Instances:*
the launcher died wordlessly after PREFLIGHT CLEAR on a fresh machine; the
reconcile path crashed on exactly the crashed-run streams it exists to
reconcile; `sect()` on a dormant member's absent key would have killed every
launch for that member. *Guard:* every extractor whose empty is legal ends
`|| true` (or `|| VAR=default`) with an explicit `${VAR:-default}`; and the
class-test is now standing — the launcher battery runs the fresh-machine,
costless-orphan, and absent-key cases before any courier ships launcher changes.
