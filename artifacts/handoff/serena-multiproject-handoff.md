# Serena multi-project hand-off packet
Configure Serena the way its maintainers do to steer the coding agent, and run N projects
concurrently with no shared-state hazards. Facts hold against oraios/serena @ `ad2e83e2`
(2026-07-08). `[derived]` marks claims inferred from documented mechanisms rather than stated
outright — verify before relying on them adversarially.
## 1. Process model — what "concurrent" means here
- One `SerenaAgent` per process; one active project per agent. Context and language backend are
  fixed for the session; the exposed toolset is frozen at startup. Every tool call and LS init is
  serialized through one `TaskExecutor` thread — there is no intra-instance parallelism to manage.
- Therefore: **concurrent multi-project = one Serena process per project.** stdio transport gives
  you this for free — each client session spawns its own server.
- Do **not** share one SSE/streamable-http server across projects: the lifespan runs per
  connection but the agent is a singleton, so every connection shares the same active project and
  the same serialized executor.
- `activate_project` is sequential switching inside one instance, not concurrency. `single_project`
  contexts (e.g. `claude-code`) remove it entirely.
- Read-only cross-project access without switching: `serena start-project-server` plus the
  optional `list_queryable_projects` / `query_project` tools (the `query-projects` mode enables
  them).
## 2. Shared-state map
Everything cross-instance lives under the Serena home (`~/.serena`, or `$SERENA_HOME`).
| Surface | Scope | Concurrent behavior | Discipline |
|---|---|---|---|
| `serena_config.yml` | global | Saves are atomic (temp + `os.replace`, Windows retry). A session persists only the `projects` list and re-reads the on-disk file first; CLI overrides are never written back. Unsynchronized read-modify-write remains: two registrations in the same instant can drop one `[derived]`. | Register all projects up front, serially. Don't hand-edit while the fleet runs — comments survive saves, but your edit can lose the race. |
| `.serena/project.yml` + `project.local.yml` | per project | Disjoint across projects. Two instances on the *same* project can clobber it (older versions regenerate it from template) and race the LS caches. | **One live instance per project root.** Machine-local tweaks → `project.local.yml`. |
| LS symbol caches (`<project data>/cache/<lang>/`) | per project | Pickled after every successful tool call; loaded once at startup. | Covered by the one-instance rule. |
| LS binaries (`~/.serena/language_servers/static`) | global | Install dirs are versioned per pinned version; no cross-process install lock is documented → first-run race if two fresh instances install the same server simultaneously `[derived]`. | Pre-warm serially before fan-out: `serena project index <path>` per project. |
| User contexts / modes / prompt-template overrides (`~/.serena/contexts`, `~/.serena/modes`, `SerenaPaths().user_prompt_templates_dir`) | global | Name-shadowing applies to every instance at its next start. | Treat as fleet-wide policy. Per-project steering belongs in `project.yml` + memories, not here. |
| Global memories (`global/` topic) | global | One shared namespace; concurrent same-name writes are last-write-wins, no lock documented `[derived]`. | Keep globals read-mostly; agents write per-project memories; lock with `read_only_memory_patterns`. |
| Dashboard API | per instance | Binds the first free port from 24282 upward. | Nothing needed. Headless/CI: `web_dashboard: false`, `gui_log_window: false`. |
| Tray | one fixed-port process (0x5EA0) | A registry that registers and health-checks all live agents — the intended fleet view. | None. |
| Hook state (`~/.serena/hook_data/<session_id>`) | per session | Keyed by session id. | None. |
| Godot LS | fixed TCP 6008 | Attaches to a running editor; one port. | At most one live GDScript project. |
| JetBrains plugin | port scan from 0x5EA2 | Scans and matches by project path — multi-instance aware. | None. |
Hard isolation lever: a distinct `SERENA_HOME` per instance removes every global row above (the
test suite's `SERENA_HOME=$(mktemp -d)` pattern). Cost: duplicate LS installs, separate
config/contexts/memories. Use only when you need zero coupling.
## 3. Steering the agent — the maintainer playbook
Resolution order first; everything hangs off it:
- **Tools:** `ToolSet.default()` ← `serena_config` ← context ← modes ← project config. Any
  `fixed_tools` replaces the whole set; `read_only: true` strips every `ToolMarkerCanEdit` tool
  last — including `execute_shell_command`.
- **Scalars:** project beats global. Lists (`ignored_paths`, memory patterns) merge; dicts
  (`ls_specific_settings`) merge project-wins, trust-gated.
- **Modes:** `base_modes` (global only; default `interactive` + `editing`) ∪ `default_modes`
  (replaced by later layers — project `[]` kills global defaults; `--mode` beats both) ∪
  `added_modes` (accumulate across project and `--add-mode`).
**Contexts** — one per session, per client. What the maintainers do in `claude-code.yml`:
- Exclude tools the host already has natively (`read_file`, `create_text_file`,
  `execute_shell_command`, `find_file`, `list_dir`, `search_for_pattern`) — no duplicate surface
  competing with the host's.
- `single_project: true` — locks the session, drops `activate_project`/`get_current_config`,
  shrinks the toolset.
- `structured_tool_output: false` — pinned to a measured client bug, not a preference. Design to
  the model's observed behavior.
- The prompt argues the host model out of its defaults: Read/Edit marked FORBIDDEN for discovery,
  with the model's own rationalizations enumerated and pre-empted. Write context prompts against
  the host's actual failure modes, not generic advice.
- Custom: drop `~/.serena/contexts/<name>.yml` (shadows a built-in of the same name) or pass a
  YAML path to `--context`.
**Modes** — composable, hot-switchable task posture: `editing`, `planning` (strips editing tools),
`interactive`, `one-shot`, `onboarding`/`no-onboarding`, `no-memories`, `query-projects`. Project
`default_modes` sets posture per project. A diagnosis-only harness = `planning` + `one-shot`; note
this is tool denial, not prompt denial — the tools are gone, which is the strong form.
**`project.yml` knobs that steer:** `languages`, `read_only`, `excluded_tools` /
`included_optional_tools` (line-based edit tools are off by default deliberately — symbolic and
regex editing are the preferred surface), `default_modes`, `ignored_paths`,
`ls_specific_settings`, `activation_command`.
**Trust gates:** `trusted_project_path_patterns` in `serena_config.yml`. The template ships `[]` —
nothing is trusted until you say so. `activation_command` and project `ls_specific_settings` apply
only to trusted paths. For a fleet: one glob per workspace root.
**Memories are the primary steering surface.** The maintainers guide agents through in-repo
`.serena/memories/`: `conventions`, `task_completion`, `suggested_commands`,
`adding_new_language_support_guide` — the agent onboards from these. Replicate per project: seed
via the onboarding tool, write terse ops memories, cross-link with `mem:<name>`, verify with
`serena memories check`, protect with `read_only_memory_patterns`.
**Tool contract:** descriptions come from `apply()` docstrings — single source of truth.
`tool_description_overrides` exists in contexts only for length-capped clients (the `chatgpt`
context); it is not a steering channel.
**Prompt overrides:** `serena prompts create-override` — user dir shadows internal templates.
Per §2: fleet-wide, not per-project.
**Hooks (Claude Code):** `serena-hooks` — the remind hook denies grep/read-of-code-file calls with
a steer to symbolic tools; auto-approve removes permission friction for Serena's own tools.
Session-scoped state, concurrency-safe.
## 4. Fleet recipe
1. `serena_config.yml`: set `trusted_project_path_patterns` for your workspace roots; disable
   dashboard/GUI if headless.
2. Register every project (add to `projects`, or activate each once) — serially, before fan-out.
3. Warm serially, once per project: `serena project index <path>` — starts each language server
   (installing dependencies into the shared static dir on first run `[derived]`) and pre-warms the
   symbol cache. This eliminates the only first-run race.
4. Seed per-project memories and `project.yml` (posture via `default_modes`, `read_only` where
   appropriate).
5. Launch one process per project per client session:
   `serena start-mcp-server --context claude-code --project-from-cwd` (stdio). Hold the
   one-instance-per-project-root rule.
6. Cross-project queries, if needed: `serena start-project-server` + the query tools.
## 5. Pinned invariants
- Exposed toolset frozen at startup; context and backend immutable per session — mid-session
  posture changes go through modes only.
- No intra-instance parallelism: one serialized executor per agent.
- One live Serena instance per project root; N concurrent projects = N processes.
- Everything global lives under the Serena home; `SERENA_HOME` is the full-isolation escape hatch.
