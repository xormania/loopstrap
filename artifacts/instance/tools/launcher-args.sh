#!/usr/bin/env bash
# Canonical Claude argument builder. The launcher and consistency audit both call
# this function so the audited vector is the vector that will be executed.
build_claude_args() {
  local max_turns="$1" root="$2" max_budget="$3"
  CLAUDE_ARGS=(
    -p
    --permission-mode dontAsk
    --max-turns "$max_turns"
    --output-format stream-json
    --verbose
    --add-dir "$root/artifacts"
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep"
    --max-budget-usd "$max_budget"
  )
}
