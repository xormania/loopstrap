source "$TROOT/cases/lib.inc"
# Real landing: exhaustive courier, hashes, modes, stale-set convergence, runtime
# preservation, and loud refusal on ambiguity.
LW="$FIXROOT/land"; rm -rf "$LW"; mkdir -p "$LW/root" "$LW/stage/sub"
mkdir -p "$LW/stage/artifacts/instance/tools"
cp "$FAMILY/land.sh" "$LW/root/land.sh"
cp "$FAMILY/land.sh" "$LW/stage/land.sh"
cp "$FAMILY/artifacts/instance/tools/verify-tree.py" "$LW/stage/artifacts/instance/tools/verify-tree.py"
chmod 0755 "$LW/root/land.sh" "$LW/stage/land.sh" "$LW/stage/artifacts/instance/tools/verify-tree.py"
mkzip(){
  python3 "$FAMILY/artifacts/instance/tools/seal-tree.py" "$LW/stage" >/dev/null
  rm -f "$1"
  ( cd "$LW/stage" && zip -qr "$1" . )
}

printf 'alpha-v1\n' > "$LW/stage/alpha.txt"
printf 'beta-v1\n' > "$LW/stage/sub/beta.txt"
mkzip "$LW/courierA.zip"
( cd "$LW/root" && bash land.sh "$LW/courierA.zip" > "$LW/a.log" 2>&1 ); RC=$?
assert_eq "landing: exhaustive courier A lands clean (exit 0)" "$RC" "0"
grep -q "LANDED CLEAN" "$LW/a.log" && ok "landing: post-landing exhaustive verification ran" || no "landing: no clean receipt"
cmp -s "$LW/stage/alpha.txt" "$LW/root/alpha.txt" && ok "landing: installed file is byte-exact" || no "landing: alpha differs"
[ "$(stat -c %a "$LW/root/land.sh")" = 755 ] && ok "landing: manifested executable mode applied" || no "landing: executable mode drifted"

mkdir -p "$LW/root/xor"; printf 'keep\n' > "$LW/root/xor/scratch.txt"
rm "$LW/stage/sub/beta.txt"; printf 'alpha-v2\n' > "$LW/stage/alpha.txt"
mkzip "$LW/courierB.zip"
( cd "$LW/root" && bash land.sh "$LW/courierB.zip" > "$LW/b.log" 2>&1 ); RC=$?
assert_eq "landing: courier B converges clean (exit 0)" "$RC" "0"
[ ! -e "$LW/root/sub/beta.txt" ] && ok "landing: stale regular file removed" || no "landing: stale beta survived"
grep -qx 'alpha-v2' "$LW/root/alpha.txt" && ok "landing: changed file converged to courier bytes" || no "landing: alpha not converged"
[ -f "$LW/root/xor/scratch.txt" ] && ok "landing: declared runtime custody path preserved" || no "landing: runtime custody destroyed"

# A managed stale file changed into a directory: refuse before installation,
# never print convergence and never recursively delete unknown contents.
printf 'obsolete\n' > "$LW/stage/obsolete"
mkzip "$LW/courierC.zip"
( cd "$LW/root" && bash land.sh "$LW/courierC.zip" >/dev/null 2>&1 )
rm "$LW/stage/obsolete"; printf 'alpha-v3\n' > "$LW/stage/alpha.txt"; mkzip "$LW/courierD.zip"
rm "$LW/root/obsolete"; mkdir "$LW/root/obsolete"; printf 'unknown\n' > "$LW/root/obsolete/keep"
( cd "$LW/root" && bash land.sh "$LW/courierD.zip" > "$LW/d.log" 2>&1 ); RC=$?
[ "$RC" -ne 0 ] && grep -q "changed type" "$LW/d.log" && ok "landing: stale file→directory refuses loudly" || no "landing: stale directory ambiguity accepted"
[ -f "$LW/root/obsolete/keep" ] && ok "landing: refusal does not recursively delete unmanifested contents" || no "landing: ambiguous directory destroyed"
grep -qx 'alpha-v2' "$LW/root/alpha.txt" && ok "landing: preflight refusal occurs before new bytes install" || no "landing: refusal partially installed courier D"

# Extra archive member omitted from the manifest is rejected.
rm -rf "$LW/extra"; mkdir "$LW/extra"; ( cd "$LW/extra" && unzip -q "$LW/courierB.zip" )
printf 'unlisted\n' > "$LW/extra/extra.txt"
( cd "$LW/extra" && zip -qr "$LW/courier-extra.zip" . )
( cd "$LW/root" && bash land.sh "$LW/courier-extra.zip" > "$LW/extra.log" 2>&1 ); RC=$?
[ "$RC" -ne 0 ] && grep -q "not exhaustive" "$LW/extra.log" && ok "landing: unmanifested courier entry refused" || no "landing: extra courier entry accepted"

# Archive topology is checked before extraction: traversal and duplicate entries
# are both ambiguous couriers, regardless of whether hashes might later match.
python3 - "$LW/courier-traversal.zip" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w") as archive:
    archive.writestr("../escape", b"outside\n")
PY
( cd "$LW/root" && bash land.sh "$LW/courier-traversal.zip" > "$LW/traversal.log" 2>&1 ); RC=$?
[ "$RC" -ne 0 ] && grep -q "unsafe archive path" "$LW/traversal.log" \
  && ok "landing: archive traversal entry refused before extraction" || no "landing: archive traversal accepted"

cp "$LW/courierB.zip" "$LW/courier-duplicate.zip"
PYTHONWARNINGS=ignore python3 - "$LW/courier-duplicate.zip" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1], "a") as archive:
    archive.writestr("alpha.txt", b"duplicate\n")
PY
( cd "$LW/root" && bash land.sh "$LW/courier-duplicate.zip" > "$LW/duplicate.log" 2>&1 ); RC=$?
[ "$RC" -ne 0 ] && grep -q "duplicate archive path" "$LW/duplicate.log" \
  && ok "landing: duplicate archive entry refused" || no "landing: duplicate archive entry accepted"

# Hash tampering and missing manifest both refuse.
rm -rf "$LW/tamper"; mkdir "$LW/tamper"; ( cd "$LW/tamper" && unzip -q "$LW/courierB.zip" )
printf 'evil\n' >> "$LW/tamper/alpha.txt"; ( cd "$LW/tamper" && zip -qr "$LW/courier-tamper.zip" . )
( cd "$LW/root" && bash land.sh "$LW/courier-tamper.zip" > "$LW/tamper.log" 2>&1 ); RC=$?
[ "$RC" -ne 0 ] && grep -q "hash manifest" "$LW/tamper.log" && ok "landing: hash-tampered courier refused" || no "landing: tampered courier accepted"
rm -rf "$LW/noman"; mkdir "$LW/noman"; printf 'x\n' > "$LW/noman/stray.txt"
( cd "$LW/noman" && zip -qr "$LW/courier-noman.zip" . )
( cd "$LW/root" && bash land.sh "$LW/courier-noman.zip" > "$LW/noman.log" 2>&1 ); RC=$?
[ "$RC" -ne 0 ] && grep -q "no loopstrap.manifest" "$LW/noman.log" && ok "landing: manifest-less courier refused" || no "landing: manifest-less courier accepted"
