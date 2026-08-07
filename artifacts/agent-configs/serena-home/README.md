Fleet-wide Serena home surfaces (~/.serena) — HUMAN-AUTHORED policy, never planted
into repos. serena-fleet.sh installs contexts/ into ~/.serena/contexts/ (refuses on
divergence; refuses while a paste-me marker remains). Register D26.

Upgrade check — codex shadow (verified against source @ serena v1.5.3, 2449313c;
re-run this whole list on every serena upgrade):
- Resolve the installed built-in (serena is a uv tool — ambient python3 can't import it;
  use the tool venv's python, which survives python-version bumps):
    ~/.local/share/uv/tools/serena-agent/bin/python -c \
      "import serena, pathlib; print(pathlib.Path(serena.__file__).parent / 'resources/config/contexts/codex.yml')"
- Diff it against contexts/codex.yml. The ONLY allowed deltas: `description` and
  `single_project`. The prompt is byte-verbatim, trailing whitespace included. Any other
  delta = upstream drift — re-splice prompt/tools from the built-in, keep the two deltas.
- Contexts are FULL-REPLACE (no inherit/extend): the shadow must carry every built-in
  field. Omitted prompt = startup failure; unknown key = TypeError at load (fails loud).
- Never rename the file, never add a `name:` key — OpenAI schema sanitization keys off
  the context NAME (mcp.py: name in ["chatgpt","codex","oaicompat-agent"]); the name
  derives from the filename. Renamed shadow = Codex gets raw, incompatible schemas.
- single_project only bites when a startup project resolves (agent.py: `and project is
  not None`); --project-from-cwd walks up for .serena/project.yml then .git. Member
  repos carry both. Launcher guard worth keeping: refuse to start outside a repo.
- v1.5.3 quirks, re-check after upgrade: a file literally named `codex` in the launch
  cwd hijacks context resolution (fixed upstream @ e4af86be); `structured_tool_output`
  is an unknown key until 011edec4 — keep it OUT of the shadow until past that commit.
- Stale excluded_tools names degrade soft (legacy remap + warning, not a crash) — but
  re-verify the six names against the tool registry anyway.
