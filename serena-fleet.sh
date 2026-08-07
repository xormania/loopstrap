#!/usr/bin/env bash
# serena-fleet.sh — serial register + warm for every member repo.
# Kills the one first-run race in the Serena shared-state map (LS installs) and
# pre-warms symbol caches. Run once after repos exist, and after adding a repo.
# Requires the serena CLI; override the command with SERENA_CMD (e.g. an uvx form).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERENA_CMD="${SERENA_CMD:-serena}"
# fleet shadow context — single_project lock for codex (register D26)
CTX_SRC="$ROOT/artifacts/agent-configs/serena-home/contexts/codex.yml"
CTX_DST="$HOME/.serena/contexts/codex.yml"
if grep -q "PASTE-BUILT-IN-PROMPT" "$CTX_SRC" 2>/dev/null; then
  echo "NOTE: staged codex context still carries the paste-me marker — paste the built-in"
  echo "      prompt (src/serena/resources/config/contexts/codex.yml) into staging first."
  echo "      Skipping context install; indexing continues."
elif [[ -f "$CTX_DST" ]] && cmp -s "$CTX_SRC" "$CTX_DST"; then
  echo "fleet context ok: $CTX_DST"
elif [[ -f "$CTX_DST" ]]; then
  echo "WARN: $CTX_DST exists and differs from staging — resolve by hand (fleet policy is human-authored)."
else
  mkdir -p "$(dirname "$CTX_DST")" && cp "$CTX_SRC" "$CTX_DST" && echo "installed fleet context: $CTX_DST"
fi

found=0
for repo in "$ROOT"/repos/*/; do
  [[ -d "$repo/.git" ]] || continue
  found=1
  echo "== indexing $repo"
  $SERENA_CMD project index "$repo"
done
[[ $found -eq 0 ]] && { echo "no git checkouts under repos/ yet"; exit 1; }
# D36: serena >=1.6 migration trap — a FRESH ~/.serena ships trusted_project_path_patterns: []
# (trusts nothing), and externally-planted ls_specific_settings / activation_command then
# silently stop applying. Loud check, version-safe (a plain grep works at any version):
SCFG="$HOME/.serena/serena_config.yml"
G1="$ROOT/repos/*"; G2="$ROOT/.worktrees/*"
WANT="trusted_project_path_patterns: [\"$G1\", \"$G2\"]"
if [[ ! -f "$SCFG" ]] || ! grep -q 'trusted_project_path_patterns' "$SCFG"; then
  echo "WARN: no trusted_project_path_patterns in ${SCFG} — serena >=1.6 silently drops"
  echo "      planted project settings. Set (xor's hand, fleet policy):"
  echo "        $WANT"
elif grep 'trusted_project_path_patterns' "$SCFG" | grep -qF "$G1" \
  && grep 'trusted_project_path_patterns' "$SCFG" | grep -qF "$G2"; then
  echo "trust globs ok — cover $G1 and $G2 (derived-at-site, L35)"
else
  echo "WARN: trusted_project_path_patterns present but STALE for THIS root (L35):"
  echo "  current : $(grep 'trusted_project_path_patterns' "$SCFG" | head -1)"
  echo "  corrective line (xor's hand):"
  echo "        $WANT"
fi

cat <<EON
----
Fleet warmed (serially — the safe order). Reminders (artifacts/handoff/serena-multiproject-handoff.md):
 - serena_config.yml: trusted_project_path_patterns should glob $ROOT/repos/* and $ROOT/.worktrees/*.
 - One live Serena instance per repo root; stdio per client session gives you this.
 - Run-time launch is the staged .codex/config.toml line: serena start-mcp-server --context codex --project-from-cwd
   (the fleet shadow context supplies single_project — file must stay named codex, D26/D36).
 - Global contexts/modes/prompt-overrides/global-memories = fleet policy: human-authored only.
EON
