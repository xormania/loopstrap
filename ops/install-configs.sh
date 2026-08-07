#!/usr/bin/env bash
# ops/install-configs.sh — plant staged agent configs into member repos.
# Staging: artifacts/agent-configs/<member>/  ->  repos/<member>/
# Duties: copy · write .git/info/exclude entries · write manifests (sha256) ·
#         refuse on foreign collision · idempotent · --check = drift report only
#         (.serena/project.yml: presence-checked only — serena normalizes it on index).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGING="$ROOT/artifacts/agent-configs"
CHECK=0; [[ "${1:-}" == "--check" ]] && CHECK=1
MB="# >>> loopstrap agent-config plants (managed block — do not edit) >>>"
ME="# <<< loopstrap agent-config plants <<<"
EXCLUDES=("AGENTS.md" "CLAUDE.md" ".claude/" ".codex/" ".serena/" "plan/")
fail=0; drift=0; planted=0; missing_repos=0

sha() { sha256sum "$1" | awk '{print $1}'; }

# render(): substitute the __ROOT__ token (used by settings walls) with this tree's
# absolute root, so planted denies bind on any user/home. Files without the token
# pass through byte-identical.
RND="$(mktemp -d)"; trap 'rm -rf "$RND"' EXIT
render() {
  local out="$RND/$(printf '%s' "$1" | sha256sum | cut -c1-16)"
  python3 - "$1" "$out" "$ROOT" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1])
output = Path(sys.argv[2])
root = sys.argv[3]
output.write_text(source.read_text(encoding="utf-8").replace("__ROOT__", root), encoding="utf-8")
PY
  printf '%s' "$out"
}

list_files() { (cd "$1" && find . -type f | sed 's|^\./||' | sort); }

manifest_has() { # $1=manifest $2=rel — echoes recorded hash or nothing
  [[ -f "$1" ]] && awk -F'\t' -v p="$2" '$2==p{print $1}' "$1" || true
}

install_member() {
  local m="$1" mdir="$STAGING/$1" repo="$ROOT/repos/$1"
  if [[ ! -d "$repo/.git" ]]; then
    echo "MISSING $m — repos/$m is not a git checkout"
    missing_repos=$((missing_repos+1)); fail=1; drift=1
    return
  fi
  local manifest="$repo/.git/loopstrap-agent-config.manifest" newmanifest=""
  while IFS= read -r rel; do
    local src; src="$(render "$mdir/$rel")"; local dst="$repo/$rel"
    if [[ $CHECK -eq 1 ]]; then
      if [[ ! -f "$dst" ]]; then echo "MISSING $m/$rel"; drift=1
      # serena normalizes .serena/project.yml on index (values preserved) — content is
      # serena's post-plant; --check verifies presence only. Install still refreshes it.
      elif [[ "$rel" == ".serena/project.yml" ]]; then :
      elif ! cmp -s "$src" "$dst"; then echo "DRIFT   $m/$rel"; drift=1; fi
      continue
    fi
    if [[ -f "$dst" ]] && ! cmp -s "$src" "$dst"; then
      local rec; rec="$(manifest_has "$manifest" "$rel")"
      if [[ -z "$rec" ]]; then
        echo "REFUSE  $m/$rel exists and is not ours — skipped (resolve by hand)"; fail=1; continue
      fi
    fi
    mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"; planted=$((planted+1))
    newmanifest+="$(sha "$src")"$'\t'"$rel"$'\n'
  done < <(list_files "$mdir")
  if [[ $CHECK -eq 0 ]]; then
    printf '%s' "$newmanifest" > "$manifest"
    local excl="$repo/.git/info/exclude"
    mkdir -p "$(dirname "$excl")"; touch "$excl"
    # strip old managed block, then append fresh
    awk -v b="$MB" -v e="$ME" 'BEGIN{skip=0} $0==b{skip=1;next} $0==e{skip=0;next} !skip' "$excl" > "$excl.tmp"
    { cat "$excl.tmp"; echo "$MB"; for x in "${EXCLUDES[@]}"; do echo "$x"; done; echo "$ME"; } > "$excl"
    rm -f "$excl.tmp"
  fi
}

# Registry and staging must be a bijection. serena-home is fleet configuration,
# not a member plant.
mapfile -t MEMBERS < <(python3 - "$ROOT/artifacts/members.toml" <<'PY'
import sys, tomllib
data=tomllib.load(open(sys.argv[1], "rb"))
for name in sorted(data): print(name)
PY
) || { echo "REFUSE  artifacts/members.toml is unparseable"; exit 1; }
[[ ${#MEMBERS[@]} -gt 0 ]] || { echo "REFUSE  member registry is empty"; exit 1; }
for m in "${MEMBERS[@]}"; do
  [[ -d "$STAGING/$m" ]] || { echo "MISSING staging for registered member $m"; fail=1; drift=1; continue; }
  install_member "$m"
done
for mdir in "$STAGING"/*/; do
  m="$(basename "$mdir")"
  case "$m" in shared|root|serena-home) continue;; esac
  found=0
  for registered in "${MEMBERS[@]}"; do [[ "$m" == "$registered" ]] && found=1; done
  [[ $found -eq 1 ]] || { echo "REFUSE  unregistered member staging: $m"; fail=1; drift=1; }
done

# root signposts (root has no .git — manifest lives beside)
RMAN="$ROOT/.loopstrap-root-config.manifest"; newroot=""
while IFS= read -r rel; do
  src="$(render "$STAGING/root/$rel")" dst="$ROOT/$rel"
  if [[ $CHECK -eq 1 ]]; then
    if [[ ! -f "$dst" ]]; then echo "MISSING root/$rel"; drift=1
    elif ! cmp -s "$src" "$dst"; then echo "DRIFT   root/$rel"; drift=1; fi
    continue
  fi
  if [[ -f "$dst" ]] && ! cmp -s "$src" "$dst" && [[ -z "$(manifest_has "$RMAN" "$rel")" ]]; then
    echo "REFUSE  root/$rel exists and is not ours — skipped"; fail=1; continue
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"; planted=$((planted+1)); newroot+="$(sha "$src")"$'\t'"$rel"$'\n'
done < <(list_files "$STAGING/root")
[[ $CHECK -eq 0 ]] && printf '%s' "$newroot" | sort -t"$(printf '\t')" -k2 > "$RMAN"   # (D60a) deterministic order ⇒ byte-noop on a current courier

echo "----"
if [[ $CHECK -eq 1 ]]; then
  [[ $drift -eq 0 && $fail -eq 0 ]] && echo "CHECK OK — every registered member is planted and matches staging." || echo "CHECK: missing or drifted required state (see above)."
  [[ $drift -eq 0 && $fail -eq 0 ]] && exit 0 || exit 1
fi
echo "planted/refreshed: $planted   missing repos: $missing_repos   refusals: $fail"
[[ $fail -eq 0 ]] && echo "OK — every registered member config installed." || echo "INCOMPLETE — resolve every missing repository or collision above."
exit $fail
