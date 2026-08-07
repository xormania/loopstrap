# arm-gate — the pre-ARM battery (L13)

**Purpose.** Breaker minimization by prevention: every historically-known halt class is
verified green BEFORE xor arms. ARM is legal only on a green gate. Detection is never
softened — the breaker still fires on anything the gate missed; the gate exists so it
rarely has anything to catch.

**Run** as `math-lsp` at the root, steward-driven; report one PASS line + this
checklist as the receipt in `campaigns/<id>/` before requesting ARM.

1. `./ops/install-configs.sh --check` — clean (no drift, no refusals).
2. `./ops/preflight.sh <member> <cid>` — green (each member being armed) (env walls · cited-input hashes · warmup).
3. `./ops/wall.sh --sweep` holds · `artifacts/instance/tools/audit-consistency.sh` exits 0.
4. **codex trust recorded** for each `repos/<member>` (§11 wall 1): trusted once interactively;
   an untrusted repo silently drops its project config.
5. **serena**: `trusted_project_path_patterns` present in `~/.serena/serena_config.yml`
   (≥1.6 trap, D36) · `./ops/serena-fleet.sh` warm with zero warnings.
6. **auth**: `gh auth status` = xor-machine · push probe round-trips:
   `git -C repos/<member> push origin HEAD:refs/heads/arm-probe` then delete `arm-probe` — per member being armed.
7. **base footing**: the member's int branch exists (registry) · `git -C repos/<member> rev-parse origin/<int>`
   equals the kickoff's `base_sha` — a stale base between prep and arm is the
   SMOKE-BASE-1 class and dies here.
8. **versions**: `claude --version` / `codex --version` match `machines.md`, or their
   D38 re-verify records exist for the drift.
9. **budget**: `project-budget.toml` current; campaign caps set, or the project tier
   consciously governing (recorded either way).
10. **citations**: every kickoff-cited input exists; recorded hash recomputes clean.

11. **lanes (when >1, L16)**: each lane's worktree exists and is clean · per-lane locks
    absent · lane assignments in the backlog are disjoint (clauses and footprints) ·
    serena trust globs = the fleet-derived pair for THIS root (ops/serena-fleet.sh prints PASS or the corrective line — L35).
12. **vendor status**: GitHub Actions operational (status probe or dashboard) — arming
    into a known outage is a recorded choice, not an accident (L14).

Any red ⇒ fixed before ARM, never waived. The gate prevents; the breaker detects.
On green + xor's ARM, **the steward launches the Conductor** (L20) — per lane.
