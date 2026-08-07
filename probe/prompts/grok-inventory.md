# Grok Build CLI — Invocation-Surface Inventory (LAUNCHER UNVERIFIED)

Status: prompt authored; **no launcher ships** — the Grok Build invocation
surface has never been verified against current vendor docs, and this kit
refuses to guess flags. First act of the first session: verify how to start
a session, load a project-scoped config, and run non-interactively — from
current official docs, never memory — then copy the claude stanza in run.sh.

Then run the same inventory shape as the sibling prompts, adapted:

1. Full command tree from --help + docs, tabled (option | forms | values |
   default | config key | env var | status | source | notes).
2. Config/settings surface, file locations, precedence, project trust.
3. Permission / sandbox / approval machinery and what non-interactive mode
   forces or ignores.
4. Doctrine-file discovery (GROK.md or equivalent; any AGENTS.md/CLAUDE.md
   cross-discovery is a finding — a role split depends on which files
   binding to one reader each).
5. Env vars; credential handling; env passthrough to child processes (probe
   with PROBE_TOKEN only).
6. Exit codes, output modes, stdin handling; headless-vs-interactive parity.
7. Pipeline: changelog/deprecations since the pinned version.

Ground rules, deliverable shape, and probe discipline: identical to
claude-inventory.md — pinned header, [probed]/[docs] labels, probe-log
appendix, Open section, no invented answers.

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
