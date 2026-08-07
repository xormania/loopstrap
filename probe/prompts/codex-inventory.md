# Codex CLI — Full Invocation-Surface Inventory (re-run instrument)

## Objective
Produce a complete, source-verified inventory of the Codex CLI's invocation
surface — every subcommand, flag, config key, and environment variable, plus
their precedence and interactions — as released today, and as changed by the
PR pipeline. This is the standing re-run instrument: a prior report exists;
your product diffs against it into a delta sheet.

## Ground rules
- Source over memory. Nothing asserted from prior knowledge of Codex. Every
  entry cites a repo path (file/symbol) or official doc section examined this
  session. Clone/update the `openai/codex` repo inside this scratch area if
  a local fork is not already available.
- Pin the ref. Header records: repo, examined commit SHA of main, latest
  release tag, today's date.
- Source beats docs. Doc/source disagreement is a finding, resolved to source.
- Negative evidence is not absence evidence: an option absent from docs or
  --help is only absent after the argument-parser definitions in source have
  been checked.
- No invented answers. Anything undeterminable goes under Open.

## Scope — current surface
1. Subcommand tree, complete, from source — every subcommand and alias.
2. Per subcommand: every flag — forms, value type/values, default, and the
   equivalent config key and env var where one exists.
3. Config surface: every recognized key, file locations, project-trust
   mechanics, and the full precedence chain, cited to source.
4. Environment variables recognized anywhere in the CLI.
5. AGENTS.md discovery rules — per mode, with size caps — verified separately
   for interactive and non-interactive paths.
6. Exit codes, output modes (plain / JSON / streaming), stdin handling.

## Priority subset — flag it distinctly
The non-interactive path is the consumer: `codex exec` — exact flags; whether
project config, trust, sandbox/approval modes, MCP servers, and AGENTS.md
load identically to interactive; session persistence/resume; machine-readable
output; exit-code semantics per outcome. Any mode divergence is a finding.

## Scope — pipeline
PRs merged since the latest release tag (unreleased on main) + open PRs,
filtered to CLI argument definitions, config parsing, exec paths, or
AGENTS.md handling. Per item: PR# · title · status · change · breaking-risk
note for staged project-scoped config. Deprecations/renames in flight get
their own list.

## Deliverable
One markdown inventory: pinned header · per-subcommand tables (option | forms
| type/values | default | config key | env var | status | citation | notes) ·
precedence chain stated once · priority subset self-contained · findings ·
**delta section vs the prior report where one exists** · Open.

## Protocol
Enumerate from source first; reconcile against docs and --help second. If one
pass can't cover everything, current-surface first, pipeline second, same
document, and say so.

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
