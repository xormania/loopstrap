#!/usr/bin/env bash
# regen-doctrine.sh — regenerate every member's CLAUDE.md (loop) + AGENTS.md (generator)
# from the shared templates by INLINING the family-law block (never @import — imports
# do not expand on subdir launch, verified Claude Code 2.1.215). Run from repo root:
#   artifacts/agent-configs/shared/regen-doctrine.sh
# Then ./ops/install-configs.sh to plant. Per-member content lives in the CASE block below —
# the one place member facts are authored; templates carry structure only.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
AC="$ROOT/artifacts/agent-configs"
LAW="$(cat "$AC/shared/family-law-block.md")"
CT="$AC/shared/_claude.tmpl"; AT="$AC/shared/_agents.tmpl"; ST="$AC/shared/_agents-stub.tmpl"

emit() { # $1=file  reads stdin as content
  cat > "$1"
}
fill() { # tokenized render: reads template on $1, substitutes from env, prints
  local tmpl="$1"; local out; out="$(cat "$tmpl")"
  out="${out//\{\{MEMBER\}\}/$MEMBER}"
  out="${out//\{\{ROLE\}\}/$ROLE}"
  out="${out//\{\{KIND\}\}/$KIND}"
  out="${out//\{\{BASIS\}\}/$BASIS}"
  out="${out//\{\{BOUNDARY\}\}/$BOUNDARY}"
  out="${out//\{\{GUARANTEES\}\}/$GUARANTEES}"
  out="${out//\{\{NEVERS\}\}/$NEVERS}"
  out="${out//\{\{LAW\}\}/$LAW}"
  printf '%s\n' "$out"
}

gen_member() { # MEMBER ROLE KIND BASIS BOUNDARY GUARANTEES NEVERS  (spec-bearing)
  fill "$CT" > "$AC/$MEMBER/CLAUDE.md"
  fill "$AT" > "$AC/$MEMBER/AGENTS.md"
  echo "  gen  $MEMBER  (loop + generator)"
}
gen_stub() { # MEMBER ROLE  (spec-less: read-only, plan-only, never licensed)
  fill "$CT" > "$AC/$MEMBER/CLAUDE.md"
  KIND="" BASIS="" BOUNDARY="" GUARANTEES="" NEVERS="" fill "$ST" > "$AC/$MEMBER/AGENTS.md"
  echo "  gen  $MEMBER  (loop + stub — spec-less, read-only)"
}

# ---- per-member facts (the sole authoring surface) ----
KIND="" BASIS="" BOUNDARY="" GUARANTEES="" NEVERS=""   # stub defaults; spec-bearing members override inline

MEMBER=lsp_math  ROLE="**the math language server** — lsp_math: a small declarative math language and its Rust language server (LSP 3.17 over stdio)." gen_stub

echo "done."
