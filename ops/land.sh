#!/usr/bin/env bash
# ops/land.sh — converge the installed tree to an exhaustive, hash- and mode-sealed
# courier. Mutable runtime paths (repos/, .worktrees/, xor/, scratch/, reports/)
# are outside courier completeness and are never removed.
set -uo pipefail

fail(){ echo "✗ LANDING FAILED: $*" >&2; exit 1; }
ZIP="${1:-}"
[ -f "$ZIP" ] || fail "usage: ./ops/land.sh <courier.zip>"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || fail "cannot enter live root"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Reject ambiguous archive topology before extraction. unzip otherwise accepts
# duplicate entries and may let a later entry silently replace an earlier one.
mapfile -t ZIP_ENTRIES < <(unzip -Z1 "$ZIP") || fail "cannot enumerate courier"
[ "${#ZIP_ENTRIES[@]}" -gt 0 ] || fail "courier is empty"
for entry in "${ZIP_ENTRIES[@]}"; do
  case "$entry" in
    /*|*\\*|../*|*/../*|*/..)
      fail "unsafe archive path: $entry";;
  esac
done
DUPLICATE="$(printf '%s\n' "${ZIP_ENTRIES[@]}" | sort | uniq -d | head -1)"
[ -z "$DUPLICATE" ] || fail "duplicate archive path: $DUPLICATE"

unzip -q "$ZIP" -d "$TMP" || fail "zip extract"
NEWMAN="$TMP/loopstrap.manifest"
[ -f "$NEWMAN" ] || fail "no loopstrap.manifest inside the courier"
[ -f "$TMP/loopstrap.modes" ] || fail "no loopstrap.modes inside the courier"
( cd "$TMP" && sha256sum -c loopstrap.manifest --quiet ) \
  || fail "courier fails its own hash manifest"
python3 "$TMP/artifacts/instance/tools/verify-tree.py" "$TMP" >/dev/null \
  || fail "courier is not exhaustive, path-safe, regular-file-only, and mode-true"
echo "courier verified: hashes + exhaustive paths + modes ($(wc -l < "$NEWMAN") files)"

OLDMAN="$ROOT/loopstrap.manifest"

# Resolve the full stale set and validate destination topology before changing a
# byte. A managed file that became a directory or link is ambiguity, not license
# to recursively delete unmanifested contents.
STALE="$TMP/.stale"
: > "$STALE"
if [ -f "$OLDMAN" ]; then
  comm -23 \
    <(awk '{p=$2; sub(/^\.\//,"",p); print p}' "$OLDMAN" | sort) \
    <(awk '{p=$2; sub(/^\.\//,"",p); print p}' "$NEWMAN" | sort) > "$STALE"
fi
while IFS= read -r stale; do
  [ -n "$stale" ] || continue
  if [ -e "$stale" ] || [ -L "$stale" ]; then
    [ -f "$stale" ] && [ ! -L "$stale" ] \
      || fail "stale managed path changed type; refusing recursive removal: $stale"
  fi
done < "$STALE"

while read -r _hash raw; do
  rel="${raw#./}"
  src="$TMP/$rel"
  dst="$ROOT/$rel"
  parent="$(dirname "$dst")"
  # Symlinked parent components could redirect installation outside ROOT.
  probe="$parent"
  while [ "$probe" != "$ROOT" ] && [ "$probe" != "/" ]; do
    [ ! -L "$probe" ] || fail "destination parent is a symlink: ${probe#"$ROOT"/}"
    probe="$(dirname "$probe")"
  done
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    [ -f "$dst" ] && [ ! -L "$dst" ] \
      || fail "managed destination is not a regular file: $rel"
  fi
  mkdir -p "$parent" || fail "cannot create parent for $rel"
  tmp_dst="$parent/.loopstrap-land.$$.tmp"
  cp -p -- "$src" "$tmp_dst" || fail "copy failed: $rel"
  mv -f -- "$tmp_dst" "$dst" || fail "commit failed: $rel"
done < "$NEWMAN"

removed=0
while IFS= read -r stale; do
  [ -n "$stale" ] || continue
  if [ -e "$stale" ]; then
    rm -f -- "$stale" || fail "stale removal failed: $stale"
    removed=$((removed+1))
  fi
done < "$STALE"

cp -p "$NEWMAN" "$ROOT/loopstrap.manifest" || fail "cannot install manifest"
while IFS=$'\t' read -r mode rel; do
  chmod "$mode" "$ROOT/$rel" || fail "cannot apply mode $mode to $rel"
done < "$TMP/loopstrap.modes"

python3 "$ROOT/artifacts/instance/tools/verify-tree.py" --allow-runtime "$ROOT" >/dev/null \
  || fail "post-landing tree verification"
echo "LANDED CLEAN — $(wc -l < "$NEWMAN") files installed, $removed stale files removed; runtime custody paths preserved."
