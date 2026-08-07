# Judge profile: rust (the first-class default — L32/L33)

**Local deterministic set** — the Conductor runs these, in order, before reading any
diff (L5); all must pass; output captured to the pass judge-log:

1. `cargo check`
2. `cargo test`
3. `cargo clippy -- -D warnings`
4. `cargo fmt --check`

**CI** — `.github/workflows/judges.yml` from `artifacts/ci/judges-rust.yml`
(committed at member-repo creation): the four above re-executed independently,
plus the trailer/attribution judges on the `dev` lane, the license judge
(`cargo deny check` against the member's `deny.toml`), sandbox-net denial, and
the marker-driven runtime-neutrality gate.

**Provisioned extras** (available, not gating): cargo-nextest, cargo-insta,
cargo-audit, cargo-mutants, cargo-llvm-cov — a member's docs-manifest `local`
list may promote any of these to gating.

A member binds this profile via `docs-manifest.toml → [judges] profile = "rust"`
(the template default). Missing profile file for a named profile = broken
binding = validator FAIL.
