#!/usr/bin/env bash
# ops/custody-sweep.sh — immutable, self-contained plan/ custody snapshot.
# Every invocation gets a unique directory; later sweeps cannot overwrite any
# byte named by an earlier manifest.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail() { echo "REFUSE  $*" >&2; exit 1; }

m="${1:-}"; CID="${2:-}"
[[ -n "$m" && -n "$CID" ]] || fail "usage: ./ops/custody-sweep.sh <member> <campaign-id>"
SRC="$ROOT/repos/$m/plan"
[[ -d "$SRC" ]] || fail "no run state: repos/$m/plan/ absent — nothing to sweep"
find "$SRC" -type f -print -quit | grep -q . \
  || fail "plan/ exists but holds no files — refusing to record an empty sweep"

DST="$ROOT/artifacts/reports/$CID"
mkdir -p "$DST"
STAMP="$(date -u +%Y%m%dT%H%M%S.%N)"
SNAP="$(mktemp -d "$DST/plan-sweep-$STAMP.XXXXXX")"
COMMITTED=0
trap '[[ $COMMITTED -eq 1 ]] || rm -rf "$SNAP"' EXIT
STATE="$SNAP/state"
TRACES="$SNAP/traces"
mkdir -p "$STATE" "$TRACES"

cat > "$TRACES/FIDELITY.md" <<'EOF'
Trace fidelity (instance §13, FR-010): these JSONLs carry vendor reasoning
SUMMARIES, never raw chain-of-thought. Telemetry, never authority — never
citable as basis, never a steering channel.
EOF

swept=0
while IFS= read -r -d '' source; do
  rel="${source#"$SRC"/}"
  case "$rel" in
    *.jsonl|*.err) output="$TRACES/$rel" ;;
    *)             output="$STATE/$rel" ;;
  esac
  mkdir -p "$(dirname "$output")"
  cp -p -- "$source" "$output"
  swept=$((swept+1))
done < <(find "$SRC" -type f -print0 | sort -z)

MANIFEST="$SNAP/MANIFEST.sha256"
( cd "$SNAP" && find state traces -type f -print0 | sort -z | xargs -0 sha256sum > "$MANIFEST" )
( cd "$SNAP" && sha256sum -c MANIFEST.sha256 --quiet ) \
  || fail "manifest self-check FAILED"
COMMITTED=1

printf '%s · custody-sweep · %s/%s · %s source files · snapshot %s\n' \
  "$(date -Iseconds)" "$m" "$CID" "$swept" "$(basename "$SNAP")" >> "$DST/owner-records.md"
echo "swept $swept source files: repos/$m/plan/ → reports/$CID/$(basename "$SNAP")/"
echo "manifest: $MANIFEST"
echo "custody verified (immutable byte-match)"
