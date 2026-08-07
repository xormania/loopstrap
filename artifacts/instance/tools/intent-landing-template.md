# Intent Landing Channel — protocol + templates (instance §15)

**What this is.** The standing protocol by which xor's intent, drafted in design sessions, lands on the authoritative layer (this machine) — checked at the truth, never at the mirror. Courier layer: `xor/channel/` (out-of-doctrine envelope space); payloads land in doctrine (`artifacts/intent/`). Both legs are memorialized files.

## Layout and naming

```
xor/channel/
  inbox/    ← proposals (landed by xor's paste):  NNN-<slug>.md
  outbox/   ← echoes (written by the root session): NNN-<slug>-echo.md
```

`NNN` is a monotonic counter, never reused (channel NNN — registered series; the register opens fresh for lsp_math). Pairs self-index by name.

## Forward leg — the proposal

The design session emits a paste block that is a **courier, not logic**: it writes the proposal file into `inbox/` verbatim (heredoc), verifies its stated sha256, then instructs the session to execute it. Proposal file body:

```
# Intent proposal NNN-<slug> · <date> · provenance: design chat
PROPOSED ENTRIES (verbatim, append targets named):
→ artifacts/intent/family.md            [or intent/<member>.md]
- `rule:` <text> *(<date>)*
- `lean:` <text> *(<date>)*
Design-session force-level rationale: <one line per entry>
```

## The checks — run against LIVE disk, in order, before any write

1. **Duplicate / supersede** — read the target intent file whole: does an existing entry already say this, contradict it, or get superseded by it?
2. **Basis collision** — grep the ratified surfaces the entry touches (instance, FR register, `contracts/`, member specs): does ratified text already answer or contradict it? A `rule:` colliding with basis is a **REFUSAL** — report the colliding clause (it means xor should amend basis instead; the register never forks the law).
3. **Force-level sanity** — flag a `rule:` that reads like taste (candidate `lean:`) or a `lean:` that reads like an absolute (candidate `rule:`). **Flag, never change.**

All clear → append verbatim (append-only, never reorder, never rewrite). Any check trips → **land NOTHING**, write the refusal echo with finding + recommendation, wait for xor.

## Return leg — the echo (written to `outbox/`, xor uploads it to the design session)

```
# ECHO NNN-<slug> · <date>
landed: <the lines, verbatim>            | or REFUSED: <finding + recommendation>
file: <path> · <N> lines · sha256 <first 12 hex>
drift-notes: <one line each: xor live-edits seen, owner acts, board moves,
anything the design session's mirror should know — omit section if none>
```

The **sha is the sync token**: the design session's mirror is authoritative-never, lagging-always; the echo re-syncs it. A stale mirror never blocks anything — it only means the next proposal's checks do more work at the truth.

## Standing rules

- xor's paste is the authorizing act (forward); the outbox write surfaces as xor's ask-gate click (return) — human at both ends, files in between.
- The channel carries **intent payloads only**; anything basis-grade rides the landing protocol (instance §8), not this.
- Envelopes stay in `xor/channel/` (out-of-doctrine, xor's retention); the session MAY custody-sweep notable echoes into `reports/`, never required.
