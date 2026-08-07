#!/usr/bin/env bash
# Point this clone's hooks at ops/hooks.
#
# Hooks are not versioned by git, so a tracked hooks directory only binds a
# clone that opts in. One command, and it survives every later checkout:
#
#     bash ops/hooks/install.sh
#
# What it buys: a publication check that runs on every commit rather than when
# someone remembers. The check is fail-closed — no denylist is a blocked commit,
# never a passed one — so enabling these without a denylist blocks every commit.
# That is the intended behaviour and not a bug to work around. If you have no
# private terms to protect, do not enable them.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
git -C "$root" config core.hooksPath ops/hooks
echo "hooks enabled — core.hooksPath = ops/hooks"

if python3 "$root/artifacts/instance/tools/publication-check.py" \
        --root "$root" --file /dev/null >/dev/null 2>&1; then
    echo "denylist resolves — commits will be checked"
else
    echo
    echo "WARNING: no denylist resolves, so every commit will now be BLOCKED."
    echo "  Supply one at \$PUBLICATION_DENYLIST, ./proj/private-terms.txt,"
    echo "  ./.private-terms, or ~/.config/publication-denylist — one term per"
    echo "  line, kept untracked, because the list is itself the disclosure."
    echo "  Or disable again with: git config --unset core.hooksPath"
fi
