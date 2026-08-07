# probe — vendor-surface interrogation

One kit, re-run at every vendor release, producing a versioned fact sheet per CLI
and a machine-readable surface the contract ingests.

```shell
./probe/run.sh <claude|codex|grok>
python3 artifacts/instance/tools/probe-ingest.py --surface <reports>/<vendor>-surface.json
python3 artifacts/instance/tools/seal-tree.py .
bash artifacts/instance/tools/contract-check.sh
```

## Why this exists

`spec/cue/` proves documents are coherent. It cannot prove a vendor binary
accepts the flags a profile passes it — that is a claim about someone else's
program. The nearest checkable thing is a snapshot of the command-line surface,
and then unification does the rest.

An earlier generation of this system solved the same problem by grepping the
vendor's `--help` output inside the launcher, at launch time, pinned to one
version. That works until the grep is the only thing that knows, and it spends
tokens to discover a flag was renamed. This moves the check to gate time and
makes its provenance explicit.

## Two deliverables per run

| file | audience |
| --- | --- |
| `reports/<vendor>-report.md` | a human. Pinned header, tables per scope area, divergences, probe log appendix. Diffing two runs is the delta sheet. |
| `reports/<vendor>-surface.json` | the contract. Validated against `#HarnessSurface` and folded into `config/harness-cli.v1.json`. |

**The markdown is never parsed.** A probe result enters the system only by
satisfying `contract/schema_harness_surface.cue`, checked with the pinned CUE
binary. The JSON example inside each prompt is a hint; the CUE definition is the
authority, and if they disagree the prompt is wrong.

## Evidence tags

Every flag carries a `status`, weakest last:

- `probed` — the binary was run and the behaviour observed
- `docs` — official documentation is the authority
- `derived` — a binary string grep was the only evidence

Only `probed` licenses arming a treatment. A surface claiming `probed` for any
flag must carry `binary_sha256` and `probed_at`; the schema rejects it otherwise,
and `C-CLI-004` rejects it again on the ingested side. **Never upgrade a tag you
did not earn.**

## Safety

- **Runs outside any git working tree.** A probe repo git-walks upward and must
  never run near real project state. The kit's source lives in this repository,
  so `run.sh` stages a copy to a neutral directory and re-executes there;
  `lib/setup.sh` refuses independently if it finds itself inside a work tree.
- Scratch git repo per run, with a nested `sub/` for doctrine-walk probes.
- Repo-credential class scrubbed (`GH_TOKEN`, `GITHUB_TOKEN`, enterprise
  variants); `PROBE_TOKEN=probe123` planted for env-passthrough probes. Vendor
  auth is untouched — the tool needs its own login to run at all.
- Claude autoupdater pinned off for the window.
- The rendered prompt's sha256, the binary path and the binary sha256 all print
  at launch. That is the run's provenance line.

**Sessions are attended.** This is owner-run research, not something the loop
invokes: it spends real tokens against a real vendor account and writes a file
you approve at the ask-gate.

## Grok

No launcher is authored, on purpose. Its invocation surface has never been
verified against current vendor docs and this kit refuses to guess flags — which
is also why `config/harness-profiles.v1.json` pins it `ruled-out`. The prompt
exists; the first session verifies the launch shape from current documentation,
never from memory, and then a stanza mirroring claude's can be added.

## Cadence

Re-run at every vendor release that could touch flags, settings, permissions,
doctrine discovery or headless output. Ingest, re-seal, run the gate. A flag the
vendor dropped becomes `C-CLI-001`; a version that moved becomes `C-CLI-003`.
