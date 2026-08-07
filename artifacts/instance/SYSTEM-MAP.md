# Loopstrap — System Map (steward reference)

*Ask me about any of this. I am root Fable, the steward: xor's eyes and voice
above the Conductor, never hands. This map is orientation, not authority — the
register (`registers/`) and `instance/process.md` are the dev lane's authorities;
the product's authorities are the ratified lsp_math docs in `contracts/` once
authored — each lane's documents win in their own lane, and no runtime lexicon
governs Loopstrap.*

---

## 1 · The one-sentence frame

**Loopstrap is the engine that builds its members.** A member is a deliverable
application, any language, defined entirely by its three-doc set; the registry
(`artifacts/members.toml`) names the members (current: lsp_math). No deliverable
lexicon governs Loopstrap; the wall is structural — a member never builds itself.

## 2 · The four agents (who runs what)

| Agent | Is | Started by | Doctrine | Hands? |
|---|---|---|---|---|
| **xor** | the owner; the steward session is **his interface (L21)** | — | — | the only recorded acts: **arm · rule · ratify · promote** — executed at his word through his console — warned, never approval-gated (L39; promote stays Box-2 by credential; sovereign stays his own uid) |
| **root Fable** (me) | staffing **xor's interface** — the steward session (L21): verifies (arm-gate), dispatches (prep handoffs + Conductor launch, L20), tracks the estate (board); standing acts autonomous, owner acts never initiated | xor, interactively | `agent-configs/root/CLAUDE.md` | none — reads all, writes `reports/`·`briefs/`·`campaigns/` only |
| **the Conductor** | a member's runner — delegates the trio, tracks its lane's run | steward-dispatched via `launch-loop.sh` (L20) | `repos/lsp_math/CLAUDE.md` | its repo's `plan/` + git; **hands-off source by wall** |
| **the generator** | per-unit worker | the Conductor (`codex exec`) | `repos/lsp_math/AGENTS.md` | local commits only; **zero-credential** |

## 3 · How work flows (one campaign)

Prepare (steward drafts kickoff + curated backlog, cited inputs hashed) → xor
**arms** (removes the breaker) → the Conductor runs unattended: per unit, brief →
generator → deterministic judges → finder + advocate → disposition → integrate
— to exhaustion or halt → retrospect → **sweep** (xor rules every DEFAULT and
finding by number) → absorb → xor **promotes** dev → main.

- **Backlog** = the campaign plan, ratified, cited by hash at kickoff; the Conductor
  plans *within* it, never beyond.
- **Footing license** (`process.md §4`): interior silences resolve in intent
  order; cross-cell silence **halts** — routed to xor.
- **The breaker** (`plan/HALTED.md`): sticky; only xor removes it.

## 4 · The estate (one repo + root)

Root `~/projects/loopstrap/` — LOCAL-ONLY, never a git repo. Corpus in
`artifacts/` (xor-managed by hand). Members clone under `repos/<member>/`
per the registry.

| Member | Role | Spec | Loop-runnable? |
|---|---|---|---|
| **lsp_math** | current member (description belongs to its docs) | **TO AUTHOR** — its three-doc set | **no — read-only until its docs-manifest verifies** |

Lanes (L16): within the member, prep-partitioned lanes (disjoint clauses + footprints) each run their own loop session in `.worktrees/<lane>/`, all integrating into `dev`; c1 defaults to one lane. Estate law (ruled 2026-07-21, register L2): `main` default + locked to
`xormania` — xor's promotion line, never the Conductor's. The Conductor's standing
integration line is **`dev`**: unit branches cut from `dev` (per the cited
`campaign.toml`), PRs target `dev`, merge on green judges; xor promotes
dev→main at campaign close.

## 5 · Authoritative documents (what governs)

- **`contracts/<member>/`** — each member's ratified doc set per the standard
  (L26/L28): the triad + machine exports + docs-manifest. **The owner's hand only.**
- **`registers/`** — append-only law; opens fresh (`design-decision-register.md`,
  L-series). **Never renumber; supersede by new entry.**
- **`instance/process.md`** — Loopstrap's campaign operations.
- **`intent/family.md`** — xor's advisory voice, force-leveled.
- **`methods/`** — the project-neutral methods (lexicon, contract, process,
  spec-CI): the discipline the lsp_math docs are built under.
- **`guidance/`** — segment map + per-segment memos (L6, advisory force):
  practices inform, contracts bind, judges gate; hash-cited at kickoff.

## 6 · The scripts (what to run, what it proves)

| Script | Run from | Does |
|---|---|---|
| **`launch-loop.sh <member> [cid]`** | root | opens the Conductor in the member repo, kickoff on stdin, bounded; refuses while spec-less |
| **`install-configs.sh [--check]`** | root | plants staged `agent-configs/` into the repo; `--check` = drift report |
| **`preflight.sh lsp_math [cid]`** | root | pre-pass wall battery |
| **`land.sh <courier.zip>`** | root | the ONLY update path: converge the tree to a courier by `lsp_math.manifest` |
| **`reset.sh [courier.zip]`** | root | scorched-earth: backup-verified → nuke → fresh land + clone + install |
| **`token-breaker.py`** | instance/tools | the live tripwire battery; spawned by the launcher every run |
| **`custody-sweep.sh lsp_math <cid>`** | root | plan/ → reports custody, hash-manifested |
| **`backup.sh [dest]`** | root | disk-only state → dated self-verifying tarball; move a copy OFF-machine |
| `serena-fleet.sh` · `probe.sh` · `wall.sh` · `ops/*` | root | fleet warm · comprehension probe · lane wall · operator console |
| `agent-configs/shared/regen-doctrine.sh` | root | regenerates the member's CLAUDE.md+AGENTS.md from templates |

## 7 · The run sequence (from a clean machine to the first campaign)

1. Stand up the Conductor user (loop-user-plan.md) · provision (verify table green)
2. Land the courier (`land.sh`) · member clones from the registry · `install-configs.sh`
3. `serena-fleet.sh` · `probe.sh` · `install-configs.sh --check` clean
4. **Author + ratify a member's doc set** into `contracts/<member>/` — that member's launch key
5. Segment map + per-segment guidance memos (L6) — derived from the ratified clauses; backlog spine
6. First campaign: prep → xor arms → `launch-loop.sh <member> <member>-c1` → sweep → promote

## 8 · Where the run state lives (my read map)

`repos/<member>/plan/` (never committed, excluded): `findings.md`, `backlog.md`
(Run-state table = resume entry point), `unit-*.md`, `claims/`, `HALTED.md`.
Board: `campaigns/board.md`. Owner acts: `reports/owner-records.md` +
`reports/<id>/owner-records.md` — **I quote owner records, never infer acts.**
Traces: `reports/<id>/traces/` — reasoning *summaries* only; telemetry, never
authority.
