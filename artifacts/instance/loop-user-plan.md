# Loop-User Plan — dedicated Ubuntu account for unattended runs
*Drafted 2026-07-20 (Fable, design lane). Tracking doc: check items off as they land.*
*Born from the 2026-07-19/20 smoke night — lessons L1/L2 below are xor's rulings, absorbed.*

## Rulings this plan implements
- **L1 (xor):** loops run under a dedicated user account. Containment by OS boundary —
  denial beats instruction. Kills the ambient-session class (July-12 strays), auth
  tangle, and owner/loop floor interleaving, structurally.
- **L2 (xor):** the root of xor's own access lane carries **zero constraints** — no
  planted doctrine, no deny walls, no settings. Walls and doctrine live only in the
  loop user's world. The root Claude is owner access, never a steward cage.

## Open pins — xor rules by number
| # | Question | Options | Fable lean |
|---|---|---|---|
| P1 | What lives at the root of **xor's** tree after the split | (a) nothing · (b) one-page unconstrained map (paths, campaign names, "walls live in loop user") | (b) |
| P2 | `xor/` custody home under two users | (a) stays in xor's user; loop crosses via a group-writable drop dir · (b) moves into loop user's tree; xor reads across | (a) |
| P3 | Tree topology | (a) single tree in loop user (xor su's for owner acts; root Claude loses a local tree) · (b) dual trees — loop user runs THE tree; xor's user keeps an owner-access mirror, both landed from the same courier | (b) |
| P4 | Username | — | **RULED: `math-lsp`** (2026-07-21) |

## Phase 0 — courier prerequisites (Fable, BEFORE first land anywhere)
- [ ] **Root de-imping:** remove root `CLAUDE.md` + `.claude/settings.json` (+ AGENTS) from
      staging and root-config manifest per L2/P1 ruling; replant per P1's answer.
      *Without this, the next `land`+`install` silently resurrects the imp xor deleted.*
- [ ] **Ambient-session wall:** preflight gains a scan — any live `codex`/`claude` process
      whose cwd is the member repo = named wall (closes the July-12 blindspot; the flock
      check only sees launcher-held locks).
- [ ] Reseal courier; new zip sha into `setup.sh` WANT.

## Phase 1 — account (xor, ~2 min)
- [ ] `sudo adduser <P4>` (login shell fine; password xor's choice)
- [ ] **No sudo membership** — containment is the point
- [ ] If P2=(a): create group `lspcust`; add both users; drop dir prepared with g+ws
- [ ] `mkdir ~<P4>/tmp` (courier landing spot)

## Phase 2 — tooling in the loop user's context
**One command:** `bash artifacts/prompts/provision-loop-user.sh` — full inventory + rationale in `loop-user-apps.md`; the script ends in a verify table and refuses on any red row. The table below is the summary; the apps doc is authoritative.
| Tool | Expect (machines.md) | Verify as loop user |
|---|---|---|
| git | present | `git --version` |
| gh | present | `gh --version` |
| claude | **2.1.215** | `claude --version` |
| codex | **0.144.1** | `codex --version` |
| serena | present (≥1.6 upgrade still deferred) | `serena --version` |
| rust/cargo | toolchain for local judges | `cargo --version` |
- [ ] Any missing per-user binary: install or PATH-bridge; record deltas in machines.md

## Phase 3 — auth + trust, all inside the loop user (xor)
- [ ] `gh auth login` as **xor-machine** (repo write, **no workflow scope** — ruled)
- [ ] `gh auth setup-git` (D75 — raw `git push` rides gh's token; no prompts ever)
- [ ] `gh auth status` green; `GIT_TERMINAL_PROMPT=0` honored by setup already
- [ ] `claude` login under loop user (Max account); confirm version banner
- [ ] Codex trust: after Phase 4's clone, `cd repos/<member> && codex` → accept →
      Ctrl-C; trust is path-keyed to the **new** absolute paths
- [ ] **xormania never touches this user. Ever.** (standing law)

## Phase 4 — bootstrap (xor, one command)
- [ ] Place the current `loopstrap-<UTC>.zip` courier in `~<P4>/update/` and `setup.sh` in `~<P4>/tmp/`
- [ ] `bash ~/tmp/setup.sh` — self-verify → land → fresh clone (`$LSP_MATH_REPO`) → install; stops there — the launcher refuses lsp_math until the docs ratify, by design
- [ ] If P3=(b): land the same courier in xor's tree too (owner mirror, unconstrained root)

## Phase 5 — evidence + custody migration (xor, once)
- [ ] Donor-era reports stay with the donor archive; the lsp_math ledger opens fresh
- [ ] `xor/` custody per P2 ruling; backup.sh path implications recorded after
- [ ] Old donor-era artifacts on the box: retire per P3 answer

## Phase 6 — first-launch battery (loop user)
- [ ] `DRY_RUN=1 ./launch-loop.sh <member> <member>-c1` — expected today: REFUSE at the spec-less gate (the correct answer until the docs ratify)
- [ ] Preflight standalone: all walls green, R1 on stamped base, pins verified
- [ ] —
- [ ] First real launch waits on docs ratification + first campaign prep

## Out of scope here (tracked elsewhere)
Serena ≥1.6 upgrade · vendor CI harness · docs authoring (the launch key)

*Change record: 2026-07-20 — v1 drafted (Fable).*
