#!/usr/bin/env bash
# Stable shell entry point for exhaustive read-only syntax inventory.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/check_syntax.py"
