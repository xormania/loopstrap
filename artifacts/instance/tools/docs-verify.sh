#!/usr/bin/env bash
# docs-verify.sh — stable command surface for the schema-complete Python validator.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/docs_verify.py" "$@"
