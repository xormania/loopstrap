# Vendor-local surface — read me

- This directory is a vendor tool surface: the tool may write machine-local state here.
- Everything here is planted or tool-written and must NEVER be committed — the install
  script excludes this directory via `.git/info/exclude`.
- The exact file names/locations this vendor currently scans were NOT verified against
  current vendor docs at authoring (the family's own rule requires that verification).
  Verify when tailoring: adjust `artifacts/agent-configs/<member>/`, re-run install.
- DO NOT EDIT FILES HERE — edit staging and re-run `./ops/install-configs.sh`.
