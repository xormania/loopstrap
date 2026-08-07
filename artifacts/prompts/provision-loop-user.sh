#!/usr/bin/env bash
# NOTE (L31): this script = engine base + language packs; the Rust pack here serves
# the lsp_math member. Future members bring their packs per their docs-manifest binding.
# provision-loop-user.sh — stand up the loop user's toolchain (loop-user-apps.md, section F order).
# Idempotent. Run AS the loop user. Ends in a verify table; exits nonzero on any red row.
# PROVISION_SIM=1 skips network-gated legs (rustup/uv) for fixture proofs only.
set -uo pipefail
T(){ date +%H:%M:%S; }; say(){ echo; echo "════ $(T) $* ════"; }
FAIL=0; need(){ command -v "$1" >/dev/null 2>&1; }

say "A · apt"
sudo -n true 2>/dev/null && SUDO=sudo || SUDO=""
$SUDO apt-get update -qq || true
if ! $SUDO apt-get install -y -qq git gh unzip curl ca-certificates build-essential procps pkg-config libssl-dev python3; then
  echo "  ✗ apt leg incomplete — run once with an admin/sudo user, then rerun me"
fi

say "B · rustup + components (rustfmt, clippy, rust-analyzer)"
if [ "${PROVISION_SIM:-0}" = "1" ]; then echo "  SIM: skipped (network-gated leg)"
else
  need rustup || { curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal; . "$HOME/.cargo/env"; }
  . "$HOME/.cargo/env" 2>/dev/null || true
  rustup toolchain install -q stable
  rustup component add rustfmt clippy rust-analyzer -q
fi

say "C · npm per-user prefix + vendor CLIs"
mkdir -p "$HOME/.npm-global"
npm config set prefix "$HOME/.npm-global"
grep -q '.npm-global/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> "$HOME/.bashrc"
export PATH="$HOME/.npm-global/bin:$PATH"
need claude || npm i -g --silent @anthropic-ai/claude-code
need codex  || npm i -g --silent @openai/codex

say "D · uv + serena"
if [ "${PROVISION_SIM:-0}" = "1" ]; then echo "  SIM: skipped (network-gated leg)"
else
  need uv || { curl -fsSL https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
  need serena || uv tool install serena-agent || echo "  serena package name differs — install from source per apps doc, then record it"
fi

say "VERIFY"
row(){ printf '  %-14s ' "$1"; b="${2%% *}"
  if command -v "$b" >/dev/null 2>&1; then echo "$({ $2 2>&1 || true; } | head -1)"; else echo "MISSING"; FAIL=1; fi; }
row git        "git --version"
row gh         "gh --version"
row unzip      "unzip -v"
row flock      "flock --version"
row pgrep      "pgrep --version"
row python3    "python3 --version"
row cc         "cc --version"
row node       "node --version"
row npm        "npm --version"
row claude     "claude --version"
row codex      "codex --version"
if [ "${PROVISION_SIM:-0}" != "1" ]; then
  row rustc    "rustc --version"
  row cargo    "cargo --version"
  row rustfmt  "cargo fmt --version"
  row clippy   "cargo clippy --version"
  row rust-analyzer "rust-analyzer --version"
  row uv       "uv --version"
  row serena   "serena --version"
fi
[ "$FAIL" = 0 ] && { echo; echo "PROVISIONED ✓ — next: Phase 3 auth/trust (loop-user-plan.md)"; exit 0; } \
                || { echo; echo "✗ red rows above — fix, rerun"; exit 1; }
