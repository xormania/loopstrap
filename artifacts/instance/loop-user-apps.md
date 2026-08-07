# Loop-User Apps — the complete pre-run environment
*2026-07-20 (Fable). Derived from an evidence grep of the machinery — every row cites its consumer.
Companion installer: `artifacts/prompts/provision-loop-user.sh` (idempotent; ends in a verify table).*

## A · apt packages
| Package | Why (evidence) | Verify |
|---|---|---|
| git | 10 scripts incl. launcher/preflight/verify | `git --version` |
| gh | launcher · preflight · reset · prep · verify; auth + PR lane | `gh --version` |
| unzip | ops/land.sh · ops/reset.sh (courier landing) | `unzip -v \| head -1` |
| coreutils/util-linux *(default)* | sha256sum ×10 scripts · **flock** (rule-8 single-session lock) · tee/cut/tr/sort/date | `flock --version` |
| gawk, sed, grep *(default)* | ledger math, stamps, gates throughout | `awk --version \| head -1` |
| python3 (≥3.10, stdlib only) | token-breaker (8 wires) + launcher heredocs; **zero pip deps** (asserted: deque/datetime/hashlib/json/os/signal/sys/time) | `python3 --version` |
| tar, gzip *(default)* | ops/backup.sh custody tarballs | `tar --version \| head -1` |
| procps | **ambient-session wall** (Phase-0 preflight scan: pgrep/ps for stray codex/claude — the July-12 blindspot) | `pgrep --version` |
| build-essential | rustc links via cc; cargo test builds | `cc --version \| head -1` |
| curl, ca-certificates | rustup + uv installers; general fetch | `curl --version \| head -1` |
| pkg-config, libssl-dev *(conditional)* | only if a c2 crate pulls native TLS deps — cheap insurance | `pkg-config --version` |

*Not needed:* `jq` (only the dormant xormania estate paste uses it — owner-side, not loop-side).

## B · Rust (rustup, not apt — apt's rustc is stale)
| Piece | Why | Verify |
|---|---|---|
| rustup + stable toolchain | generator compiles; loop's local judges | `rustc --version` `cargo --version` |
| component **rustfmt** | judge: `cargo fmt --check` (doctrine) | `cargo fmt --version` |
| component **clippy** | judge: `cargo clippy -D warnings` (doctrine) | `cargo clippy --version` |
| component **rust-analyzer** | serena's Rust language server (symbols ops on member repos) | `rust-analyzer --version` |

## C · Vendor CLIs (per-user npm prefix — globals do NOT cross Ubuntu users)
| CLI | Pin (machines.md) | Install (as loop user) | Verify |
|---|---|---|---|
| node ≥18 + npm | runtime for both | apt `nodejs npm` or nodesource | `node --version` |
| **claude** (Claude Code) | **2.1.215** | `npm i -g @anthropic-ai/claude-code` under `~/.npm-global` prefix | `claude --version` |
| **codex** | **0.144.1** | `npm i -g @openai/codex` | `codex --version` |
- Prefix ritual (once): `npm config set prefix ~/.npm-global` + PATH line in `.bashrc` — the provision script does both, idempotently.
- **Version drift vs pins = a D38 re-verify event, not a shrug.**

## D · serena (verify-first; install method is uv-based)
| Piece | Note | Verify |
|---|---|---|
| uv (astral) | serena's runner | `uv --version` |
| serena | source lives at xor's `~/tmp/serena`; loop user installs its own (`uv tool install`) — **exact package/source pinned at first install, recorded here** | `serena --version` |
| contexts/config | planted by `ops/install-configs.sh` from courier staging into the loop user's `~/.serena` | `smoke.sh` serena leg |
- Standing note: serena **≥1.6 upgrade still deferred** (tracked out of scope); whatever version installs, record it in machines.md.

## E · Explicit non-dependencies (assertions, not hopes)
- **No pip packages.** Breaker is stdlib-pure; anything importing beyond stdlib is drift.
- **No docker, no sudo** in the loop user's world. Containment is the account boundary.
- **No jq, no ripgrep via apt** (Claude Code bundles its own search).

## F · Order of operations
apt → rustup(+3 components) → npm prefix → claude+codex → uv+serena → **verify table green** → then Phase 3 (auth/trust) of `loop-user-plan.md`. The provision script enforces exactly this and exits nonzero on any red row.

*Change record: 2026-07-20 — v1, evidence-derived (grep matrix in session record).*
