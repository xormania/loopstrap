#!/usr/bin/env bash
# Frozen preimplementation claims plus deterministic mock-harness acceptance.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
python3 "$ROOT/tests/acceptance/verify_freeze.py" || exit 1
exec python3 "$ROOT/tests/acceptance/run.py"
