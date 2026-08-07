# Claude Code — Loop-Runner Invocation-Surface Inventory (current + pipeline)

## Objective
Produce a complete, verified inventory of the Claude Code CLI surface consumed
by an unattended per-repo loop runner: invocation shape, permission machinery,
doctrine-file discovery, settings/env/config, exit semantics — as installed
today, plus the near-term change pipeline.

## Ground rules
- No readable vendor source exists; the authorities are (1) the installed
  binary's actual behavior, (2) official docs, (3) the vendor repo's
  CHANGELOG/release notes — reconciled in that order. Installed behavior wins.
- Pin the ref. Deliverable header records: `claude --version`, npm package
  version, docs URLs + access date, CHANGELOG head examined.
- **Probe discipline.** Behavioral probes are encouraged and mandatory for any
  docs/behavior divergence. You are already inside a scratch git repo under
  a scratch directory with a nested `sub/`, repo credentials scrubbed, and a probe token
  (`PROBE_TOKEN=probe123`) planted for passthrough probes — never introduce a
  real credential. Record every probe verbatim. A claim resolved by probe is
  labeled [probed]; by docs alone, [docs]; by bundle grep, [derived] (last
  resort, re-verified by probe where feasible).
- Negative evidence is not absence evidence: a flag absent from --help is
  absent only after the docs and a probe agree.
- Nothing undeterminable is filled; it goes under Open.

## Scope — current surface
1. Full command tree: every subcommand and flag from a --help sweep, each
   reconciled against docs. Table per command: option | forms | values |
   default | settings key | env var | status | source | notes.
2. Settings surface: every recognized key across all settings files; file
   locations and the full precedence chain (managed/enterprise > CLI flags >
   local project > shared project > user); `settings.local.json` semantics.
3. Permission machinery, exhaustively: rule grammar for allow/deny/ask
   (Tool, Tool(specifier), Bash prefix patterns and their evasion limits,
   path patterns for Edit/Write/Read); precedence among allow/deny/ask;
   permission modes and their exact effects; `--dangerously-skip-permissions`
   scope; hooks as deterministic gates (events, matchers, exit-code semantics,
   which settings files may define them).
4. Doctrine discovery: CLAUDE.md lookup order (project walk, user-level,
   CLAUDE.local.md), import syntax and depth, size handling/budgets — and the
   leak check: **does the current version discover AGENTS.md natively or via
   any fallback?** Probe both interactive and -p modes; any parity divergence
   between the two modes is a finding.
5. Env and credential handling: every recognized env var (auth, proxy,
   telemetry, autoupdate, Bedrock/Vertex toggles); env passthrough to Bash
   tool children — does a session-env token (probe with PROBE_TOKEN, never a
   real one) reach child processes unfiltered; any scrubbing or injection.
6. Session/config hygiene for unattended runs: autoupdate mechanics and the
   pin/disable switch; telemetry and network-touch surface and its off
   switches; where session state and history land on disk; `claude config`
   vs settings files; MCP config scopes (`.mcp.json`, user, project) and the
   trust/approval flow for project-scoped servers; `.claude/commands/`
   frontmatter currency; `includeCoAuthoredBy` key currency.

## Priority subset — flag it distinctly (the launcher consumes this)
Unattended headless operation: exact invocation for "start in this cwd with
this kickoff and run to completion" — `-p/--print` semantics with tool use
(does it loop to task completion), stdin vs arg prompt, `--output-format
json`/`stream-json` event and field inventory, `--max-turns`-class limits,
context-exhaustion behavior headless, `--continue`/`--resume` semantics,
`--model` selection, `--add-dir`, `--append-system-prompt`-class injection,
exit codes per outcome (success / error / limit / interrupt), and which
permission mode + settings combination yields a fully unattended session whose
walls still bind (bypass modes vs deny rules: what does bypass actually
bypass?). Interactive-vs-headless parity for: doctrine loading, settings,
permissions, MCP. Any divergence is a finding.

## Scope — pipeline
CHANGELOG entries since the pinned version plus announced deprecations:
anything touching flags, settings keys, permission grammar, doctrine
discovery, or headless output. Per item: version · what changes · breaking
risk for staged per-repo config. Open vendor-repo issues only where they
document confirmed behavior changes in flight.

## Deliverable
One markdown inventory: pinned header · sections per scope area with tables ·
the priority subset self-contained · divergences (docs vs probed, interactive
vs headless) · probe log appendix · deprecations in flight · Open
(undeterminable). Re-verify explicitly against current syntax: the staged
deny/allow rule set previously validated on 2.1.207.

## Protocol
--help sweep first, docs reconciliation second, probes for every divergence
or load-bearing claim third, pipeline last. If one pass can't cover all,
deliver current-surface first, pipeline second, same document, and say so.

## Output — mandatory
Write the finished inventory to the absolute path **{{REPORT_PATH}}** (rendered by the launcher) — one file, overwrite
on re-run. The probe log is an appendix inside it, every probe verbatim
(command · version · cwd · relevant output). Nothing else is a deliverable.

## Output — mandatory, second file

Also write **{{SURFACE_PATH}}** — the machine-readable half. The markdown above
is for a human; this is what the contract ingests, so it never has to parse
prose. One JSON object, exactly this shape:

```json
{
  "schema": "loopstrap.harness-surface/v1",
  "harness": "{{HARNESS_ID}}",
  "version": "<exact --version string, the version alone>",
  "binary_path": "<absolute path to the resolved executable>",
  "binary_sha256": "<sha256 of that file>",
  "probed_at": "<UTC RFC3339, e.g. 2026-08-07T14:03:00Z>",
  "flags": [
    {"name": "--model", "takes_value": true,  "status": "probed"},
    {"name": "--verbose", "takes_value": false, "status": "docs"}
  ]
}
```

Rules, and they matter more than completeness:

- `status` is `probed` only when you ran the binary and observed the behaviour.
  Use `docs` when official documentation is the authority, and `derived` when a
  binary string grep is the only evidence. Never upgrade a tag you did not earn.
- Include every flag you found, including ones this system does not use. A flag
  absent from this list is treated as unsupported, and a profile passing it
  fails the gate.
- `takes_value` is whether the flag consumes a following argument.
- If you cannot determine `binary_sha256`, write `null` rather than guessing.
  A snapshot claiming to be probed without that evidence is rejected.

Write both files. Either one alone is an incomplete run.
