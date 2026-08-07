# environment-manifest — ubuntu-dev (ruled file, instance §11 · FR-005/FR-010 · D45)
# Every tool a member run needs, each with a verify command. provision.sh (deferred,
# D45) will install FROM this file on a fresh machine; tonight it documents + gates.

## codex model pins (FR-010)
# Deliberately UNPINNED tonight (D45): user-level ~/.codex/config.toml governs model,
# model_reasoning_effort, model_reasoning_summary. Preflight wall 4 notes-not-walls
# unpinned keys by design. Freeze them here (key = "value") when xor rules the values.

## tools
- rustup toolchain (pinned per-repo by rust-toolchain.toml) — verify: `rustup show active-toolchain`
- cargo — verify: `cargo --version`
- cargo-deny (license judge) — verify: `cargo deny --version`
- claude CLI (the loop runner) — verify: `claude --version`
- codex CLI (the generator) — verify: `codex --version`
- serena — **v1.6.1 installed** (2026-07-21); the ≥1.6 trust trap is LIVE — the
  serena leg below is REQUIRED, not conditional — verify: `serena --version`
- gh CLI — verify: `gh --version`
- git — verify: `git --version`
- jq (verify.sh, trace tooling) — verify: `jq --version`

## serena leg (REQUIRED at v1.6.1 — xor's hand, fleet policy)
- in `/home/math-lsp/.serena/serena_config.yml` set:
  `trusted_project_path_patterns: ["/home/math-lsp/projects/lsp_math/repos/*", "/home/math-lsp/projects/lsp_math/.worktrees/*"]`
  — fresh homes trust nothing (D36); without this, planted project settings silently stop applying.
