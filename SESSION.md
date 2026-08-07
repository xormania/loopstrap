# SESSION.md — continuity log

## 2026-07-30 (second entry — harness seam)

**Requested:** assume basic harness CLI usage now; leave the seam — wrapper + profiles — for later improvement.

**Changed:**
- `loopstrap_core/profiles.py` added: profile loader/renderer; built-in defaults byte-identical to the certified argv.
- `config/harness-profiles.v1.json` added: THE tweak seam. Per harness: `argv` (certified wrapper skeleton — changing it means re-certification), `smoke_argv` (assumed-basic usage), env templates, `version_pin`, `basis` with D38 notes.
- `loopstrap_core/wrappers.py`: the three compile() bodies now render from the profile; no vendor flag is hardcoded in Python anymore.
- `harness-smoke.sh` added: one bounded invocation, mock mode default (zero tokens), `--live` for the real CLI; a live flag rejection is the D38 drift signal and the fix is the profile file.

**Frozen:** untouched; certification 26/26 green with the seam in place (argv exactness preserved).

**Red:** nothing.

**Not done:** stream-adapter completion against live vendor output, compiled-context generator, license-gate rewire, handoff dispatch, launcher — unchanged queue.

**Not read:** unchanged from the first entry, minus wrappers.py (now read in full) and tests/mocks/* (read).

**Open questions:** none — later owner direction supersedes.

## 2026-07-30

**Requested:** Get the pilot's document set done and the kernel ready to run locally; name ruling: proper name LanguageServerFixture, identifier `fixture_langserv` for repo + directory; RC-10 branch (a); proceed with recorded defaults rather than clause-by-clause review.

**Changed:**
- `artifacts/contracts/fixture_langserv/` added: lexicon (Draft 4) · contracts (Draft 2, 81 clauses) · experience spec · clause-index.txt · term-export.txt · parties.txt · docs-manifest.toml. `docs-verify.sh fixture_langserv`: 12 PASS · 0 FAIL — ratifiable; `ratified` left empty for the owner's date.
- `artifacts/members.toml`: `[fixture_langserv]` row appended (repo xormania/fixture_langserv, int_branch main — the repository's only branch today).
- `loopstrap.manifest` regenerated (seal-tree.py) to cover the landed set and this file.
- `SESSION.md` added (this file).

**Frozen:** all six suite FROZEN.sha256 seals untouched and verifying; no test inputs edited.

**Red:** nothing red; battery green from a fresh extraction of the repacked archive (output in the conversation record).

**Not done:** owner's `ratified` date in the member docs-manifest; removal of `repo/plan/HALTED.md` (sticky — owner-only); the first-prep build queue: launcher (current launch-loop.sh is the fail-closed signpost), vendor stream adapters + wrapper correction (activation-receipt-gated), compiled-context generator, handoff dispatch, license-gate rewire + posture flip; fixture-language name/extension and assertion keyword (due at corpus stage, deferrals D-1/D-2).

**Not read:** loopstrap_core module bodies beyond cli/wrappers surface greps; ops/*.sh; tests case bodies beyond the battery's own execution; artifacts/registers/design-decision-register.md; most of artifacts/methods prose.

**Open questions:** none pending — later owner direction supersedes recorded defaults.
