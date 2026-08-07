# .codex/ — verified surface (2026-07-11, developers.openai.com/codex)

- Project config here loads ONLY after xor trusts the repo (first-run prompt); machine-local
  keys (model_provider, profiles, notify, otel, base URLs) are ignored here by design.
- AGENTS.md discovery: ~/.codex/AGENTS.md (global, xor's) -> git root down to cwd, each level
  AGENTS.override.md then AGENTS.md, concatenated root->down, later overrides earlier;
  combined cap project_doc_max_bytes = 32 KiB (our doctrine file is well under).
- No-attribution (D23) is mechanized loop-side (`includeCoAuthoredBy: false`); no Codex key exists for it (verified against source, D34).
- MCP: [mcp_servers.serena] is project-scoped — one Serena per repo root, our rule exactly.
- Local tool state written here stays uncommitted — the install script excludes this dir.
- DO NOT EDIT FILES HERE — edit staging and re-run ./ops/install-configs.sh.
