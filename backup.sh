#!/usr/bin/env bash
# backup.sh — the replaceability leg for disk-only state (D39).
# Everything on this machine must be replaceable: code ⇒ remotes · corpus ⇒ couriers ·
# machine ⇒ provision.sh · DISK-ONLY STATE ⇒ this script. Assembles one dated,
# hash-manifested, self-verifying tarball of everything that exists nowhere else:
#   artifacts/reports/        (run gold: traces, sweeps, owner records)
#   xor/                      (custody lane; xor/backups itself excluded)
#   repos/*/plan/             (live run state between custody sweeps)
#   machine-local dotfiles    (~/.codex/config.toml, ~/.serena/serena_config.yml,
#                              ~/.serena/contexts/, ~/.claude/settings.json)
# Excluded on purpose: repos code (remotes are that leg), .worktrees/ (ephemeral),
# ~/.serena caches + language servers (rebuildable). The OFF-MACHINE copy is xor's
# act — this script only assembles and verifies; move the tarball somewhere that
# is not this disk.
#
# Usage: ./backup.sh [dest-dir]        default dest: xor/backups
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fail() { echo "REFUSE  $*" >&2; exit 1; }

DEST="${1:-$ROOT/xor/backups}"; mkdir -p "$DEST"
STAMP="$(date +%Y%m%dT%H%M%S)"
NAME="loopstrap-backup-$STAMP"
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/root" "$STAGE/home"

copy_tree() { # $1=base  $2=relpath  $3=stage-sub  — prune-safe, loud on absence
  if [ -e "$1/$2" ]; then
    ( cd "$1" && find "$2" -type f ! -path 'xor/backups/*' -print0 \
        | xargs -0 -r cp -a --parents -t "$STAGE/$3/" )
    echo "  + $2"
  else
    echo "  - $2 (absent — nothing to back up)"
  fi
}

echo "collecting:"
copy_tree "$ROOT" "artifacts/reports" root
copy_tree "$ROOT" "xor"               root
for d in "$ROOT"/repos/*/plan; do
  [ -d "$d" ] || continue
  copy_tree "$ROOT" "${d#"$ROOT"/}" root
done
for f in .codex/config.toml .serena/serena_config.yml .claude/settings.json; do
  copy_tree "$HOME" "$f" home
done
copy_tree "$HOME" ".serena/contexts" home

n=$(find "$STAGE" -type f | wc -l)
[ "$n" -gt 0 ] || fail "nothing collected — refusing to record an empty backup"

# manifest travels INSIDE the tarball; restore is byte-verifiable
( cd "$STAGE" && find . -type f ! -name BACKUP.manifest -print0 | sort -z | xargs -0 sha256sum > BACKUP.manifest )
tar -czf "$DEST/$NAME.tar.gz" -C "$STAGE" .
sha256sum "$DEST/$NAME.tar.gz" > "$DEST/$NAME.tar.gz.sha256"

# self-verify: fresh extract, full byte-match — a backup unverified is a hope, not a leg
V="$(mktemp -d)"
tar -xzf "$DEST/$NAME.tar.gz" -C "$V"
( cd "$V" && sha256sum -c BACKUP.manifest --quiet ) || { rm -rf "$V"; fail "self-verify FAILED — do not trust $NAME"; }
rm -rf "$V"

printf '%s · backup · %s files · %s.tar.gz · %s\n' \
  "$(date -Iseconds)" "$n" "$NAME" "$(awk '{print $1}' "$DEST/$NAME.tar.gz.sha256")" \
  >> "$DEST/backup-log.md"

echo "backup verified: $DEST/$NAME.tar.gz  ($n files)"
echo "NOW MOVE A COPY OFF THIS MACHINE — the off-machine leg is yours, not mine."
