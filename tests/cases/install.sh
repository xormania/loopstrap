source "$TROOT/cases/lib.inc"
# enforces: ops/install-configs.sh — plant · __ROOT__ render (L35) · manifest · idempotence ·
# drift detection · foreign-collision refusal — run against the REAL script
# (2026-07-23 scan F3: previously replaced by an always-success stub)
IW="$FIXROOT/inst"; rm -rf "$IW"; IR="$IW/root & value"
mkdir -p "$IR/artifacts/agent-configs/root" "$IR/artifacts/agent-configs/demo/.claude" "$IR/repos" "$IR/ops"
cp "$FAMILY/ops/install-configs.sh" "$IR/ops/"
printf '[demo]\nrepo = "example/demo"\nint_branch = "dev"\n' > "$IR/artifacts/members.toml"
printf '# root signpost\n' > "$IR/artifacts/agent-configs/root/ROOTMARK.md"
printf '{"deny":"__ROOT__/repos"}\n' > "$IR/artifacts/agent-configs/demo/.claude/settings.json"
printf '# demo doctrine\n' > "$IR/artifacts/agent-configs/demo/CLAUDE.md"
git init -q "$IR/repos/demo"
( cd "$IR" && bash ops/install-configs.sh > "$IW/i1.log" 2>&1 ); RC=$?
assert_eq "install: first plant exits 0" "$RC" "0"
grep -qF "\"deny\":\"$IR/repos\"" "$IR/repos/demo/.claude/settings.json" && ok "install: __ROOT__ rendered to the live root (L35)" || no "install: token unrendered" "$(cat "$IR/repos/demo/.claude/settings.json" 2>/dev/null)"
[ -f "$IR/repos/demo/.git/loopstrap-agent-config.manifest" ] && ok "install: agent-config manifest written" || no "install: no manifest"
[ -f "$IR/ROOTMARK.md" ] && ok "install: root signpost planted" || no "install: root signpost missing"
( cd "$IR" && bash ops/install-configs.sh --check > "$IW/c1.log" 2>&1 ); RC=$?
assert_eq "install: --check clean right after plant (exit 0)" "$RC" "0"
( cd "$IR" && bash ops/install-configs.sh > "$IW/i2.log" 2>&1 ); RC=$?
assert_eq "install: second run idempotent (exit 0)" "$RC" "0"
grep -q "REFUSE" "$IW/i2.log" && no "install: idempotent run refused its own plants" || ok "install: idempotent run refusal-free"
# ── drift on a planted file: --check must go red; re-plant must heal ──
printf 'tampered\n' >> "$IR/repos/demo/CLAUDE.md"
( cd "$IR" && bash ops/install-configs.sh --check > "$IW/c2.log" 2>&1 ); RC=$?
[ $RC -ne 0 ] && grep -q "DRIFT   demo/CLAUDE.md" "$IW/c2.log" && ok "install: --check detects planted-file drift (exit 1)" || no "install: drift undetected (rc=$RC)"
( cd "$IR" && bash ops/install-configs.sh > /dev/null 2>&1 )
( cd "$IR" && bash ops/install-configs.sh --check > "$IW/c3.log" 2>&1 ); RC=$?
assert_eq "install: re-plant heals drift (--check exit 0)" "$RC" "0"
# ── foreign collision: a dst we never planted must be REFUSED, exit 1 ──
printf 'foreign content\n' > "$IR/repos/demo/AGENTS.md"
printf '# staged agents doctrine\n' > "$IR/artifacts/agent-configs/demo/AGENTS.md"
( cd "$IR" && bash ops/install-configs.sh > "$IW/i3.log" 2>&1 ); RC=$?
[ $RC -ne 0 ] && grep -q "REFUSE  demo/AGENTS.md" "$IW/i3.log" && ok "install: foreign collision refused (exit 1)" || no "install: foreign file overwritten (rc=$RC)"
grep -qx 'foreign content' "$IR/repos/demo/AGENTS.md" && ok "install: refused file left untouched" || no "install: refusal still mutated the file"

# A registered member without a checkout is required missing state, never SKIP.
mv "$IR/repos/demo/.git" "$IR/repos/demo/.git.saved"
( cd "$IR" && bash ops/install-configs.sh --check > "$IW/missing-check.log" 2>&1 ); RC=$?
[ "$RC" -ne 0 ] && grep -q "MISSING demo" "$IW/missing-check.log" && ok "install: --check fails when a registered repo is absent" || no "install: check licensed absent repo"
( cd "$IR" && bash ops/install-configs.sh > "$IW/missing-install.log" 2>&1 ); RC=$?
[ "$RC" -ne 0 ] && grep -q "INCOMPLETE" "$IW/missing-install.log" && ok "install: normal mode fails instead of claiming all configs installed" || no "install: absent repo reported success"
mv "$IR/repos/demo/.git.saved" "$IR/repos/demo/.git"
