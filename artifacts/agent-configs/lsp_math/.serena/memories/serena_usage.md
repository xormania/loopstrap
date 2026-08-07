# serena_usage — symbolic workflow + diagnostics discipline (generator scope, Rust)

Serena is spawned with your invocation and dies with it. Your first tool call
blocks until rust-analyzer is ready (quiescence, ≤120 s cap) — that wait IS the
ready gate; there is no separate readiness check. The first cross-file reference
lookup pays a one-time ~2 s warmup this invocation. Budget accordingly; never
poll to "wait for" the index.

## Per unit, for a symbol S in file F

1. `get_symbols_overview(F)` — orient. Skip if F is already known this unit.
2. `find_symbol(S, relative_path=F, include_body=True)` — read before any edit.
   `include_info=True` only when you need a foreign signature/doc contract;
   never in bulk.
3. If S is public, or its signature or type changes:
   `find_referencing_symbols(S, F)` → blast radius R (the distinct files).
   If S is a trait or trait method: also `find_implementations(S, F)` — impls
   are not references; add their files to R.
4. Edit symbolically:
   - rename → `rename_symbol` (one workspace-wide edit, LS-synced; NEVER a
     textual rename)
   - delete → `safe_delete_symbol` (its refusal doubles as a free
     file→lines reference map)
   - else → `replace_symbol_body` / `insert_after_symbol` / `insert_before_symbol`
5. `get_diagnostics_for_file` on F and every file in R, `min_severity=1`.
   Act ONLY on entries with `source: "rust-analyzer"` — those are fresh.
   Entries with `source: "rustc"` are the cargo-check snapshot from invocation
   start — stale by construction after your edits. Never treat them as current;
   never "fix" them.
   (`get_diagnostics_for_symbol(S, check_symbol_references=True)` is the
   one-call variant when R is small.)
6. At most 2 fix iterations on native errors — each re-runs step 5 on the files
   it touched — then commit and hand to the judges.

## Hard lines

- **These diagnostics are pre-judge hygiene, never compilation evidence.**
  Never claim "compiles" or "passes" from Serena output — judges decide
  (mem:task_completion). Native coverage: type errors, unresolved names/imports,
  arity, missing match arms, missing fields. NOT covered: lints, borrowck,
  const-eval, tests — the judges' territory by construction.
- Diagnostics run on F and the blast radius R — never beyond that set, and
  never re-polled on clean files (every clean call costs a ~2.5 s wait floor).
  Once per file in F∪R per fix iteration.
- `search_for_pattern` is for non-code files and unknown-name cases only. On
  Rust, text hits are not semantic references in either direction — it misses
  macro-expanded use sites and matches strings/comments.
