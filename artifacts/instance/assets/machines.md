# machines.md — the environment fact sheet (ruled file, D48)

Every fact here is **evidence-sourced** — proven by a transcript, a script output,
or xor's own prompt line — or it is marked **UNKNOWN**. Nothing in this file is
assumed. Any session or script that touches a machine reads this FIRST; any
script that needs a fact not listed here ASKS xor or PROBES and prints — it
never guesses. (Error class: environment-assumption — see error-classes.md.)

Update discipline: facts change only with new evidence; cite the source inline.
UNKNOWN is a first-class value and stays until evidence arrives. Donor-era
evidence rows were retired with the donor archive at the lsp_math port
(2026-07-21); rows below carry only what remains proven or is newly proven.

---

## Box 1 — ubuntu-dev (the agent machine)

The only machine agents run on. xormania's credential NEVER touches it.

| fact | value | evidence |
|---|---|---|
| host | `ubuntu-dev` (WSL2, Ubuntu x86_64) | motd, transcripts through 2026-07-21 |
| runner account | **`math-lsp`** (P4 ruled 2026-07-21) · HOME `/home/math-lsp` | provisioning transcript 2026-07-21 |
| Loopstrap root | `/home/math-lsp/projects/loopstrap` — **exists only after first land** | setup path; UNKNOWN until landed |
| member repos | per `artifacts/members.toml` (lsp_math → `uscient/lsp_math`, private, needs `main`+`dev`) | registry; xor 2026-07-21 |
| rustc / cargo / rust-analyzer | **1.97.1** (2026-07-14 toolchain) | verify table, provisioning transcript |
| Claude Code | **2.1.216** — **DRIFT vs 2.1.215**, where the W3 flag surface was verified version-exact → **re-verify event (D38)** before first live launch | transcript vs 2026-07-19 record |
| codex CLI | **0.144.6** — **DRIFT vs 0.144.1**, where the `turn.completed` token field map was verified live → **re-verify event** at first generator run | transcript vs 2026-07-19 record |
| serena | **1.6.1** — trust trap (D36) closed by xor's paste, **but the globs were written pre-L31 to the old root: STALE** until the loopstrap-path re-paste runs (issued 2026-07-23); source of truth is the fleet-derived check — serena-fleet.sh compares the live line against globs computed from the actual root and prints PASS / STALE + corrective line (L35) | transcript · L31 · L35 |
| serena registrations | user-scope with codex (`--context=codex`) and claude-code (grok's went with `~/.grok`, L4) — **codex user-scope overlaps the planted project-scoped `[mcp_servers.serena]`; precedence at 0.144.6 UNKNOWN — verify, don't assume** | transcript; L4 |
| gh | **2.96.0**, authenticates as **xor-machine** (repo scope, no workflow scope — the missing scope is itself a wall) | xor's ruling 2026-07-21 |
| Grok Build | **RULED OUT (L4, 2026-07-21)** — removal paste issued; VERIFY: `command -v grok` fails and `.bashrc` carries no `.grok` line | xor's ruling |
| shared Rust tools | 38 at `/opt/rust-agent-tools/bin` (incl. cargo-deny 0.20.2, cargo-nextest, cargo-insta); cargo-flamegraph absent (optional, failed); **PATH inclusion for math-lsp UNKNOWN — verify `command -v cargo-deny`** | transcript |
| uv | 0.11.30 at `~/.local/bin` | transcript |
| shell | bash available; non-trivial pastes always `bash -c` or a script file | donor-era failure, lesson carried |

## Box 2 — xormania box

Any box that is NOT ubuntu-dev; carries xormania. Estate acts only.

| fact | value | evidence |
|---|---|---|
| user / host | `xor@xor` · HOME `/home/xor` · conda `(base)` | estate prompts |
| gh | authenticated as **xormania** (numeric id `127287135`) | estate scripts; protection dump |

## Identities (restated for scripts)

| identity | lives where | may do |
|---|---|---|
| xormania | Box 2 / browser only | admin: rulesets, repo settings, promotion |
| xor-machine | ubuntu-dev, the `math-lsp` session (`gh auth` + `GH_TOKEN` per session) | clone, push unit branches + `dev`, PRs; **no workflow scope by xor's choice — the missing scope is itself a wall**. Precision (L40): repo-write CAN delete/force-push an unprotected branch — `dev` protection SET (xor, 2026-07-23); `main` needs no note — xormania exists nowhere on this box |
| conductor (Claude Code) | ubuntu-dev, launched sessions only | per charter grant; deny-walled |
| generator (codex) | ubuntu-dev, per-invocation | zero-credential (env-scrubbed spawn) |

## The security model (L40)

The `math-lsp` user boundary is THE security boundary: everything inside it is
expendable by xor's declaration (courier re-lands · repos re-clone · docs
re-ratify). Nothing inside is structurally gated. What escapes the user keeps
its guard elsewhere: **origin/main** (server-side, Box-2 promote) and **spend**
(the breaker's uid-forgery-proof override lane — sovereign signals come from
xor's own account so automation can never write its own budget or pause).
In-user lane discipline is doctrinal, for record-truth, detected not prevented.

## Standing environmental rules

- Nothing here licenses touching auth plumbing (gitconfig, credential helpers,
  gh config, ssh). Credential mechanics are xor's exclusively — ruled 2026-07-19.
- Scripts prompt for secrets (`read -rsp`); placeholders-to-edit are banned.
- Planted config paths render from `__ROOT__` at install — never baked to a home.
