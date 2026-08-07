source "$TROOT/cases/lib.inc"
# enforces: Deliverable Docs Standard gate (L26/L28) · profile binding (L33)
# 2026-07-23 scan repair: every negative check runs on its OWN fresh fixture with
# TRUE hashes except the one property under test — no cross-contamination possible.
DSR="$FIXROOT/docsets"; rm -rf "$DSR"; mkdir -p "$DSR"
mkset(){ local d="$1"; mkdir -p "$d"
  cat > "$d/tm-lexicon.md" <<'L'
# tm — Lexicon
canonical: snapshot — the immutable view. banned: valid.
L
  printf '[INV-1] One owner.\n\n[C-A-1] The owner MUST publish.\n' > "$d/tm-contracts.md"
  printf '[X-1] Diagnostics read calmly.\n' > "$d/tm-experience.md"
  printf 'INV-1 A INV\nC-A-1 A MUST\n' > "$d/clause-index.txt"
  printf 'CANON snapshot\nBANNED valid\n' > "$d/term-export.txt"
  printf 'A\n' > "$d/parties.txt"
}
seal(){ python3 - "$1" "${2:-}" <<'PY'
import hashlib, os, sys
d, prof = sys.argv[1], sys.argv[2]
files=["tm-lexicon.md","tm-contracts.md","tm-experience.md","clause-index.txt","term-export.txt","parties.txt"]
lines=['member = "tm"','version = "1"','ratified = "2026-07-22"','[files]']
for f in files: lines.append(f'"{f}" = "{hashlib.sha256(open(os.path.join(d,f),"rb").read()).hexdigest()}"')
lines += ['[law]','[judges]']
if prof: lines.append(f'profile = "{prof}"')
lines += ['failure_vocab = "refusal=1"','fixture_corpus = "none"','[deferrals]']
open(os.path.join(d,'docs-manifest.toml'),'w').write("\n".join(lines)+"\n")
PY
}
DV="$FAMILY/artifacts/instance/tools/docs-verify.sh"
# ── conformant set verifies ──
mkset "$DSR/a"; seal "$DSR/a"
"$DV" "$DSR/a" > "$DSR/a.log" 2>&1
assert_eq "docs-standard: a conformant set verifies (exit 0)" "$?" "0"
# ── hash drift alone fails, attributed to the hash check ──
mkset "$DSR/b"; seal "$DSR/b"; sed -i 's/immutable/mutable/' "$DSR/b/tm-lexicon.md"
"$DV" "$DSR/b" > "$DSR/b.log" 2>&1; RC=$?
[ $RC -ne 0 ] && grep -q "manifest hash failures" "$DSR/b.log" && ok "docs-standard: hash drift FAILS via the hash check" || no "docs-standard: drift missed or misattributed (rc=$RC)" "$(cat "$DSR/b.log")"
# ── unindexed clause alone (hashes TRUE) fails, attributed to the bijection ──
mkset "$DSR/c"; printf '[C-A-2] Unindexed clause.\n' >> "$DSR/c/tm-contracts.md"; seal "$DSR/c"
"$DV" "$DSR/c" > "$DSR/c.log" 2>&1; RC=$?
if [ $RC -ne 0 ] && grep -q "clause-index ↔ contracts mismatch" "$DSR/c.log" && grep -q "C-A-2" "$DSR/c.log" \
  && grep -q "every required manifest file present + hash-true" "$DSR/c.log"; then
  ok "docs-standard: an unindexed clause FAILS the bijection (hashes true — decontaminated)"
else no "docs-standard: bijection missed it or hashes leaked in (rc=$RC)" "$(cat "$DSR/c.log")"; fi
# ── L33: a real profile verifies ──
mkset "$DSR/d"; seal "$DSR/d" rust
"$DV" "$DSR/d" > "$DSR/d.log" 2>&1; RC=$?
[ $RC -eq 0 ] && grep -q "judge profile 'rust' resolves" "$DSR/d.log" && ok "docs-standard: real judge profile (rust) verifies" || no "docs-standard: rust profile failed (rc=$RC)" "$(cat "$DSR/d.log")"
# ── L33: named-but-missing profile fails, attributed ──
mkset "$DSR/e"; seal "$DSR/e" nope
"$DV" "$DSR/e" > "$DSR/e.log" 2>&1; RC=$?
[ $RC -ne 0 ] && grep -q "judge profile 'nope' named but" "$DSR/e.log" && ok "docs-standard: named-but-missing profile FAILS (L33)" || no "docs-standard: missing profile passed (rc=$RC)"

# ── every previously licensed malformed set gets an independent hash-true fixture ──
mkset "$DSR/f"
printf '[C-B-1] Unknown party clause.\n' >> "$DSR/f/tm-contracts.md"
printf 'C-B-1 B MUST\n' >> "$DSR/f/clause-index.txt"
seal "$DSR/f"
"$DV" "$DSR/f" > "$DSR/f.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "unknown=.*B" "$DSR/f.log" && ok "docs-standard: undeclared index party FAILS" || no "docs-standard: unknown party licensed (rc=$RC)"

mkset "$DSR/g"; seal "$DSR/g"
sed -i '/"tm-lexicon.md"/d' "$DSR/g/docs-manifest.toml"
"$DV" "$DSR/g" > "$DSR/g.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "enumerate exactly the six required files" "$DSR/g.log" && ok "docs-standard: omitted required manifest entry FAILS" || no "docs-standard: incomplete manifest licensed (rc=$RC)"

mkset "$DSR/h"
printf '\n[C-A-1] Conflicting duplicate.\n' >> "$DSR/h/tm-contracts.md"
seal "$DSR/h"
"$DV" "$DSR/h" > "$DSR/h.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "duplicate clause ids" "$DSR/h.log" && ok "docs-standard: duplicate clause id FAILS" || no "docs-standard: duplicate clause licensed (rc=$RC)"

mkset "$DSR/i"; seal "$DSR/i" '../../../README'
"$DV" "$DSR/i" > "$DSR/i.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "judge profile path is invalid" "$DSR/i.log" && ok "docs-standard: profile traversal FAILS" || no "docs-standard: profile traversal licensed (rc=$RC)"

mkset "$DSR/j"; printf 'REVIEW absent-review-term\n' >> "$DSR/j/term-export.txt"; seal "$DSR/j"
"$DV" "$DSR/j" > "$DSR/j.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "exported terms absent" "$DSR/j.log" && ok "docs-standard: every tier term must appear in lexicon" || no "docs-standard: missing REVIEW term licensed (rc=$RC)"
