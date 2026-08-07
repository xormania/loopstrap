#!/usr/bin/env bash
# probe launcher — ./probe/run.sh <claude|codex|grok>
#
# Interrogates a vendor CLI and produces two deliverables per run:
#   reports/<vendor>-report.md     the human fact sheet, probe log appended
#   reports/<vendor>-surface.json  the machine-readable surface, ingested by
#                                  artifacts/instance/tools/probe-ingest.py
#
# Sessions are ATTENDED. This is owner-run research, not something the loop
# invokes: it spends real tokens against a real vendor account and writes a file
# you are asked to approve.
#
# Staging: the kit lives in a git working tree now, and a probe repo git-walks
# upward, so the kit copies itself to a neutral directory and re-executes there.
# Nothing probes near real project state.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
v="${1:-}"

if [ "${LOOPSTRAP_PROBE_STAGED:-0}" != "1" ] \
   && git -C "$HERE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  STAGE="${PROBE_STAGE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/loopstrap-probe}"
  mkdir -p "$STAGE"
  # A neutral staging root must not itself sit in a repository.
  if git -C "$STAGE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "REFUSE  staging directory is inside a git working tree ($STAGE)" >&2
    echo "        set PROBE_STAGE_DIR to somewhere neutral" >&2
    exit 1
  fi
  KIT="$STAGE/kit"
  rm -rf "$KIT"; mkdir -p "$KIT"
  cp -R "$HERE/run.sh" "$HERE/lib" "$HERE/prompts" "$KIT/"
  echo "staged        : $KIT (source: $HERE)"
  # Reports and work default beside the staged kit; override to collect them.
  LOOPSTRAP_PROBE_STAGED=1 exec "$KIT/run.sh" "$@"
fi

launch() { # $1 vendor  $2 cli-binary
  source "$HERE/lib/setup.sh" "$1"
  command -v "$2" >/dev/null || { echo "REFUSE  $2 CLI not found" >&2; exit 1; }
  PROMPT="$WORK/prompt.md"
  sed -e "s|{{REPORT_PATH}}|$REPORT|g" \
      -e "s|{{SURFACE_PATH}}|$SURFACE|g" \
      -e "s|{{HARNESS_ID}}|$3|g" \
      "$HERE/prompts/$1-inventory.md" > "$PROMPT"
  VERSION="$("$2" --version 2>/dev/null | head -1 || true)"
  BINARY="$(command -v "$2")"
  echo "version       : $VERSION"
  echo "binary        : $BINARY"
  echo "binary sha256 : $(sha256sum "$(readlink -f "$BINARY")" 2>/dev/null | cut -d' ' -f1 || echo unavailable)"
  echo "prompt sha256 : $(sha256sum "$PROMPT" | cut -d' ' -f1)"
  echo
  echo "After the run:  python3 artifacts/instance/tools/probe-ingest.py --surface $SURFACE"
  echo
  exec "$2" "$(cat "$PROMPT")"
}

case "$v" in
  claude) export DISABLE_AUTOUPDATER=1; launch claude claude claude-code ;;
  codex)  launch codex codex codex ;;
  # No launcher is authored for grok on purpose. Its invocation surface has never
  # been verified against current vendor docs, and this kit refuses to guess
  # flags — which is also why config/harness-profiles.v1.json pins it ruled-out.
  grok)   echo "REFUSE  grok launcher not authored — invocation surface unverified" >&2
          echo "        see probe/prompts/grok-inventory.md; verify the launch shape" >&2
          echo "        from current docs first, then add a stanza mirroring claude" >&2
          exit 1 ;;
  *)      echo "usage: ./probe/run.sh <claude|codex|grok>" >&2; exit 1 ;;
esac
