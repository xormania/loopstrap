#!/usr/bin/env bash
# setup.sh — select, exhaustively verify, land, clone, and plant one courier.
set -uo pipefail
T(){ date +%H:%M:%S; }
say(){ echo; echo "════ $(T) $* ════"; }
die(){ echo "✗ $(T) STOP: $*" >&2; exit 1; }
UPD="$HOME/update"
F="${LOOPSTRAP_ROOT:-$HOME/projects/loopstrap}"
HOME_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOME")"
F_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$F")"
[ ! -L "$F" ] || die "LOOPSTRAP_ROOT may not be a symlink"
case "$F_REAL" in "$HOME_REAL"/*) ;; *) die "LOOPSTRAP_ROOT escapes the account boundary";; esac
F="$F_REAL"

say "0 · SELECT newest courier in $UPD"
mkdir -p "$UPD/consumed" || die "cannot create update directories"
ZIP="$(find "$UPD" -maxdepth 1 -type f -name 'loopstrap-*.zip' -printf '%f\n' | sort | tail -1)"
[ -n "$ZIP" ] || die "no loopstrap-*.zip in $UPD"
ZIP="$UPD/$ZIP"
echo "  using: $(basename "$ZIP")"

say "0b · VERIFY exhaustive payload, hashes, types, and modes"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP" || die "unzip failed"
[ -f "$TMP/loopstrap.manifest" ] || die "courier carries no loopstrap.manifest"
[ -f "$TMP/artifacts/instance/tools/verify-tree.py" ] || die "courier carries no verifier"
( cd "$TMP" && sha256sum -c loopstrap.manifest --quiet ) || die "payload fails its hash manifest"
python3 "$TMP/artifacts/instance/tools/verify-tree.py" "$TMP" >/dev/null \
  || die "payload is incomplete, unsafe, linked, or mode-drifted"
echo "  payload verified ($(wc -l < "$TMP/loopstrap.manifest") files)"

say "1 · LAND"
mkdir -p "$F" || die "cannot create Loopstrap root"
cd "$F" || die "cannot enter Loopstrap root"
unzip -o -q "$ZIP" ops/land.sh || die "cannot bootstrap ops/land.sh"
chmod 0755 ops/land.sh || die "cannot make ops/land.sh executable"
./ops/land.sh "$ZIP" || die "landing"

say "2 · CLONE registered member repos"
gh auth setup-git >/dev/null 2>&1 || true
export GIT_TERMINAL_PROMPT=0
python3 - artifacts/members.toml <<'PY' > "$TMP/members.tsv" || die "member registry parse"
import sys, tomllib
data=tomllib.load(open(sys.argv[1], "rb"))
for name, row in sorted(data.items()):
    print(f"{name}\t{row['repo']}")
PY
while IFS=$'\t' read -r member slug; do
  if [ -d "repos/$member/.git" ]; then
    echo "  repos/$member exists — keeping"
  else
    gh repo clone "$slug" "repos/$member" -- -q || die "clone $member ($slug)"
  fi
  echo "  $member main tip: $(git -C "repos/$member" rev-parse --short origin/main 2>/dev/null || echo '?')"
done < "$TMP/members.tsv"

say "3 · INSTALL"
./ops/install-configs.sh || die "install-configs"

say "4 · ARCHIVE the consumed courier"
mv -- "$ZIP" "$UPD/consumed/" || die "could not archive $(basename "$ZIP")"
say "DONE — engine landed, member repos cloned, configs planted."
