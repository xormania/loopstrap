#!/usr/bin/env bash
# reset.sh — scorched-earth reset (D60). The machine posture, finally honest:
# NOTHING in the family dir is precious (D39's four legs guarantee it), so a
# reset is always available and always safe:
#   1 · backup.sh runs FIRST and must verify (xor/, reports/, live plan/,
#       dotfiles → one dated self-verifying tarball) — refuse to nuke otherwise
#   2 · xor/ (your custody lane, tarballs included) is set aside — never in scope
#   3 · rm -rf the ENTIRE family dir
#   4 · fresh courier landed, byte-verified; xor/ moved back
#   5 · fresh clone — kills LOCAL residue only; clones re-import origin's refs,
#       so step 5b verifies the remotes and FAILS LOUD if legacy refs exist (D64)
#   6 · install-configs
# land.sh remains the fast in-place path; reset.sh is the clean-slate path.
# Usage: ./reset.sh <courier.zip>      (env RESET_SKIP_CLONE=1 for dry estates)
set -uo pipefail
say(){ echo; echo "════ $* ════"; }
die(){ echo "✗ RESET REFUSED: $*"; exit 1; }
Z="${1:-$(ls -1 "$HOME"/update/loopstrap-*.zip 2>/dev/null | sort | tail -1)}"
F="${LOOPSTRAP_ROOT:-$HOME/projects/loopstrap}"   # instance root: one knob (L35)
[ -f "$Z" ] || die "courier not found: $Z"
HOME_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOME")"
F_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$F")"
[ ! -L "$F" ] || die "LOOPSTRAP_ROOT may not be a symlink: $F"
case "$F_REAL" in
  "$HOME_REAL") die "LOOPSTRAP_ROOT may not equal HOME; xor/ could not be set aside safely" ;;
  "$HOME_REAL"/*) ;;
  *) die "LOOPSTRAP_ROOT escapes the account boundary: $F_REAL" ;;
esac
F="$F_REAL"
if [ "${RESET_VALIDATE_ONLY:-0}" = "1" ]; then
  echo "RESET ROOT VALID — $F is a non-symlink descendant of $HOME_REAL"
  exit 0
fi
SAFE_Z="$(mktemp /tmp/loopstrap-reset-courier.XXXXXX.zip)"
cp -p -- "$Z" "$SAFE_Z" || die "could not stage courier outside the reset root"
Z="$SAFE_Z"
trap 'rm -f "$SAFE_Z"' EXIT
STAMP="$(date -u +%Y%m%dT%H%M%S.%N)"

say "1/6 BACKUP first — no verified tarball, no nuke"
if [ -d "$F" ]; then
  cd "$F"
  unzip -o -q "$Z" backup.sh && chmod +x backup.sh
  ./backup.sh || die "backup did not verify — nothing was touched"
else
  echo "  no existing tree — fresh install path"
fi

say "2/6 SET ASIDE xor/ (custody lane, tarballs inside — never in reset scope)"
KEEP=""
if [ -d "$F/xor" ]; then
  mkdir -p "$HOME/tmp" || die "cannot create custody staging under HOME"
  KEEP="$(mktemp -d "$HOME/tmp/xor-keep-$STAMP.XXXXXX")"
  rmdir "$KEEP" || die "cannot prepare custody staging"
  mv "$F/xor" "$KEEP" || die "could not set xor/ aside"
  echo "  xor/ → $KEEP"
fi

say "3/6 NUKE"
rm -rf "$F"
echo "  gone."

say "4/6 FRESH LAND"
mkdir -p "$F" && cd "$F"
unzip -q "$Z" || die "unzip"
python3 artifacts/instance/tools/verify-tree.py . >/dev/null \
  || die "courier failed exhaustive hash/mode verification (xor/ is safe at ${KEEP:-n/a})"
echo "  LANDING-CLEAN"
[ -n "$KEEP" ] && mv "$KEEP" "$F/xor" && echo "  xor/ restored"

say "5/6 FRESH CLONE (local residue structurally dead)"
if [ "${RESET_SKIP_CLONE:-0}" = "1" ]; then echo "  skipped (RESET_SKIP_CLONE=1)"; else
  [ -n "${GH_TOKEN:-}" ] || { read -rsp 'GH_TOKEN (env only): ' GH_TOKEN; echo; export GH_TOKEN; }
  while read -r m; do
    slug="$(grep -A3 "^\[$m\]" artifacts/members.toml | grep -oP 'repo *= *"\K[^"]+')"
    gh repo clone "$slug" "repos/$m" -- -q && echo "  cloned $m ($slug)" || die "clone $m ($slug)"
  done < <(grep -oP '^\[\K[^]]+' artifacts/members.toml)
fi
say "5b/6 REMOTE-LEGACY GUARD (D64) — origin must carry only main + run/*"
LEG=0
for r in repos/*/; do
  [ -d "$r/.git" ] || continue
  bad="$(git -C "$r" ls-remote --heads --tags origin | awk '{print $2}' | grep -vE '^refs/heads/(main$|run/[0-9]+/)' | grep -v '\^{}' || true)"
  [ -n "$bad" ] && { echo "  ✗ $(basename $r): $bad"; LEG=1; }
done
[ "$LEG" = "1" ] && die "remote legacy present — run the D64 purge, then re-run reset"
echo "  remotes clean ✓"

say "6/6 INSTALL"
./install-configs.sh || die "install-configs"

say "RESET COMPLETE — pristine courier · fresh clones · xor/ intact · old world in the tarball"
echo "next:  cd repos/lsp_math && codex   # trust, Ctrl-C, cd ../.."
echo "note:  the launcher refuses lsp_math (spec-less/read-only) until the lsp_math docs ratify — by design."
