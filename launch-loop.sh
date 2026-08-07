#!/usr/bin/env bash
# Fail-closed compatibility signpost. The executable launcher will be built
# only after governing documents, role assignments, and live adapters are
# independently certified.
set -u

echo "NOT ARMED — governing documents, role assignments, and live treatment certification are incomplete; no vendor was invoked." >&2
exit 2
