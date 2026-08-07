# CI judges — the deterministic gate (product content)

Committed into a member repo at creation as `.github/workflows/judges.yml` —
the **Rust profile** (first language pack; a member's docs-manifest `[judges]`
selects its profile). **CI files are
product content — the repo's own deterministic gate — not harness plants; they
are committed, not excluded.** Judges run on every PR and every `unit/**` push:
server-side verdicts are record data (D23).

## The set (process.md §10)

Always-on:
- **join-keys (I2)** — every non-merge commit in the range carries
  `Unit:/Pass:/Brief:/Config:` trailers; the `Brief:` hash resolves under
  `plan/` where present. Protects the record↔commit join. No toolchain needed;
  runs first and fast.
- **attribution (D30-auth)** — every non-merge commit's author AND committer is
  `xormania`; the machine identity `xor-machine` never appears as author or
  committer (name or email); no `Co-authored-by:` / "generated with" trailers
  (D23, no agent attribution). Repo-var knobs (Settings → Actions → Variables):
  `EXPECT_AUTHOR` (default `xormania`), `FORBID_AUTHOR` (default `xor-machine`),
  `EXPECT_AUTHOR_EMAIL` (optional — asserted only if set, since the author
  email is environment-specific).
- **the four cargo judges** — `fmt --check`
  runs FIRST (cheapest, most common failure ⇒ fail fast), then `check`,
  `clippy -D warnings`, `test`. Cached (`rust-cache`); machine-readable output
  (`--message-format=json`, test json where the toolchain supports it) for the
  loop to parse verdicts, not scrape.
- **toolchain assertion** — the runner must honor `rust-toolchain.toml` (family
  pin, D22.4); a silent drift to a different compiler than the loop judged
  against is surfaced.

Dormant until their fixtures land (guarded like the empty-crate check — ready,
not retrofitted):
- **refusal property (I4)** — the universal property (refusal ⇒ exit 1 ⇒
  nothing changed), the first fixture family. Binary members: exit-code snapshot. Runs when `tests/refusal*` exists.
- **runtime-neutrality** *(intent rule — marker-driven)* — a crate carrying the
  `.runtime-neutral` marker at its root must expose no `async` and pull no runtime
  crates (`tokio`/`futures`/…). Opt-in; binary crates that legitimately use async
  simply never carry the marker. Hard gate where opted in.
- **license gate** *(intent rule)* — `cargo deny check licenses` against a
  committed `deny.toml`: admissible = MIT/Apache-2.0/BSD/ISC/Zlib/Unicode; MPL by
  per-crate grant (added to that crate's deny.toml with a dated comment);
  GPL-family never. Missing deny.toml fails LOUD, never permissive.
- **phones-home lint** *(intent rule — warning-tier)* — flags network symbols
  (`reqwest`/`std::net`/…) for the
  finder to verify against the spec's egress grant. A `.egress-granted` marker
  silences known-legitimate cases. Never blocks — blunt by nature.

Not yet in CI (need prerequisites outside the runner):
- **vocabulary judge (I1)** — term-lint from the lexicon; dependency-blocked on
  the lsp_math lexicon (contracts/ — TO AUTHOR).
- **fixture-corpus judge (I3)** — parser vs the language-neutral TOML corpus;
  activates when `instance/fixtures/` exports.


## Marker files (committed product content, per crate)

- `deny.toml` — license policy (above). Required where the license gate runs.
- `.runtime-neutral` — presence enables the runtime-neutrality gate. No lsp_math
  crate ships it yet.
- `.egress-granted` — optional; one line per crate/path with a spec-granted
  egress, to silence the phones-home warning.

## Deployment

Updating a template here updates the gate for **future** repos (committed at
creation). **An existing repo takes a template change as a normal committed unit** —
CI is product content, so it rides a PR through the judges like any code, not an
`install-configs.sh` plant. The empty-crate guard means a template can land in a
code-less repo without wedging the required check.
