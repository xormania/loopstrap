# task_completion — definition of done (generator scope)

You are the generator. "Done" for you = the brief implemented and returned; you never
push, PR, or merge — the loop does that.

1. Code + tests committed **locally** on your unit branch — `<unit_prefix>/<id>`, named
   by the brief from the cited `campaign.toml` (D40). You hold no credential and never
   push. Never touch `main`, the campaign's int branch, or dormant `dev` directly.
2. Commits are records: detailed, frequent, unattributed. Imperative subject; what/why
   body; trailers Unit: / Pass: / Brief: / Config:. No co-author lines, no tool mentions.
3. Judges are deterministic (see mem:suggested_commands). Passing judges are a
   PREREQUISITE of the gate, not the gate — never certify your own work as passing.
4. Where Serena is present: before writing claims, run `get_diagnostics_for_file`
   (`min_severity=1`) on every file you touched plus the blast radius R
   (mem:serena_usage step 3); fix `source: "rust-analyzer"` errors
   (≤2 iterations — workflow in mem:serena_usage). `source: "rustc"` entries are the
   startup snapshot, stale by construction — ignore them. This is pre-judge hygiene,
   not certification; item 3 stands untouched.
5. Write the claims report: what you did · what you verified · what you could not.
   Your statements are recorded untrusted claims; the loop and the human verify.
6. Spec conflict or ambiguity discovered while implementing = a FINDING: halt the unit,
   report it in claims, do not patch around the contract.
7. Return. Integration (push, PR, merge on green) is the loop's, not yours.
