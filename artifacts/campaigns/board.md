# Board

**Status.** The management surface (instance §2, §9). One row per member; the steward maintains it; states per instance §2; updated at transitions only — no silent transitions. Per-cell gates, never a queue.

**Last refresh:** 2026-07-21 — lsp_math port (Conductor = Claude Code runner + `codex exec` generator; single member).

| Member | Campaign | State | Blocker / prerequisite | Next act | Whose move |
|---|---|---|---|---|---|
| — fleet — | — | provisioning + prep gates | Loop-user standup: `math-lsp` created + provisioned ✓ (P4 ruled; P1–P3 open) · courier landed · repo cloned · install clean · provision verify table green | gh auth (Phase 3) · serena trust-patterns (v1.6.1, REQUIRED) · land · clone · install | xor |
| lsp_math | — | gated (spec-less — basis absent) | Read-only until the lsp_math docs (lexicon + contract set) ratify into `artifacts/contracts/`; never licensed until then (instance §4) | Author + ratify the lsp_math docs | xor + design session |
