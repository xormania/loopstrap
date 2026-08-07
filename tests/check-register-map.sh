#!/usr/bin/env bash
# Stable shell entry point for protected runtime-map reconciliation.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/check_register_map.py" "$@"
