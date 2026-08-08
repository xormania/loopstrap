source "$TROOT/cases/lib.inc"
# Every control must have a path from red to green.
#
# Not "some good input passes" — that is weaker and it is what these controls
# already had. The property is reachability: from a RED state, the documented
# remedy must reach GREEN. A control without such a path is not strict, it is
# broken, and it is worse than no control because the only way past it is to
# disable it. The first --no-verify retires it permanently while leaving it in
# the tree looking alive.
#
# This repository has shipped that defect three times:
#
#   acceptance-check   CUE required treatment_id, Python required
#                      role_treatment_id, both ran over the same document. The
#                      intersection was empty, so NO input could be accepted,
#                      for a week, behind a green battery (REVISION-008).
#   the CI body check  pull_request did not fire on `edited`, so a red body
#                      could never be made green — the remedy existed and was
#                      unreachable.
#   publication-check  scanned added lines only, so any edit to a line already
#                      carrying a term was refused. For a term appearing in a
#                      path, no correct commit could pass at all.
#
# Each assertion below is a pair: force red, apply the documented remedy, assert
# green. The red half also proves the control is alive, so a control that
# admitted everything would fail here rather than pass silently.

CR="$FIXROOT/reachable"; rm -rf "$CR"; mkdir -p "$CR"
PUBCHECK="$FAMILY/artifacts/instance/tools/publication-check.py"
printf 'zzq-sentinel-term\n' > "$CR/deny.txt"
export PUBLICATION_DENYLIST="$CR/deny.txt"

# --- publication check ------------------------------------------------------
# Red: a new mention. Remedy: remove it. Green must follow.

cat > "$CR/red.diff" <<'D'
diff --git a/doc.md b/doc.md
--- a/doc.md
+++ b/doc.md
@@ -1,1 +1,2 @@
 context
+a brand new mention of zzq-sentinel-term
D
python3 "$PUBCHECK" --stdin < "$CR/red.diff" >/dev/null 2>&1
assert_eq "reachable: publication check fires on a new mention" "$?" "1"

cat > "$CR/green.diff" <<'D'
diff --git a/doc.md b/doc.md
--- a/doc.md
+++ b/doc.md
@@ -1,1 +1,2 @@
 context
+a brand new line naming nothing private
D
python3 "$PUBCHECK" --stdin < "$CR/green.diff" >/dev/null 2>&1
assert_eq "reachable: publication check clears once the mention is gone" "$?" "0"

# The remedy must also be reachable WITHOUT deleting content that has to stay:
# editing a line that already carried the term is ordinary work, not a leak.
cat > "$CR/edit.diff" <<'D'
diff --git a/doc.md b/doc.md
--- a/doc.md
+++ b/doc.md
@@ -1,3 +1,3 @@
 context
-run ./thing.sh against zzq-sentinel-term
+run ./ops/thing.sh against zzq-sentinel-term
 context
D
python3 "$PUBCHECK" --stdin < "$CR/edit.diff" >/dev/null 2>&1
assert_eq "reachable: publication check leaves an existing mention editable" "$?" "0"

# And removal, which is the cure, must never itself be refused.
cat > "$CR/cure.diff" <<'D'
diff --git a/doc.md b/doc.md
--- a/doc.md
+++ b/doc.md
@@ -1,2 +1,1 @@
-a mention of zzq-sentinel-term
 context
D
python3 "$PUBCHECK" --stdin < "$CR/cure.diff" >/dev/null 2>&1
assert_eq "reachable: publication check does not refuse the cure" "$?" "0"

# --- the commit hooks, through git rather than by invoking the scripts ------
# Red: a term in the message. Remedy: rewrite the message. Green must follow,
# with the same staged content — otherwise the remedy is "abandon the work".

HR="$CR/hookrepo"; mkdir -p "$HR/artifacts/instance/tools"
# The hooks resolve the checker relative to the repository root, so the synthetic
# repository must carry it. Without this the hook fails because the tool is
# absent, and the RED assertion below passes for the wrong reason — a refusal
# that proves only that a path was missing.
cp "$PUBCHECK" "$HR/artifacts/instance/tools/publication-check.py"
git -C "$HR" init -q
git -C "$HR" config user.email "case@example.invalid"
git -C "$HR" config user.name "case"
git -C "$HR" config core.hooksPath "$FAMILY/ops/hooks"
printf "ordinary content\n" > "$HR/file.txt"
git -C "$HR" add file.txt

printf 'subject mentioning zzq-sentinel-term\n' > "$CR/bad-msg.txt"
( cd "$HR" && git commit -F "$CR/bad-msg.txt" >/dev/null 2>&1 )
assert_eq "reachable: the commit hooks refuse a message naming a term" "$?" "1"

printf 'an ordinary subject line\n' > "$CR/good-msg.txt"
( cd "$HR" && git commit -F "$CR/good-msg.txt" >/dev/null 2>&1 )
assert_eq "reachable: the same staged work commits once the message is fixed" "$?" "0"

# --- the seal ---------------------------------------------------------------
# Red: an unlisted file. Remedy: remove it, or reseal. Both must reach green.

SR="$CR/sealroot"; mkdir -p "$SR"
cp "$FAMILY/artifacts/instance/tools/verify-tree.py" "$SR/verify-tree.py"
mkdir -p "$SR/artifacts/instance/tools"
cp "$FAMILY/artifacts/instance/tools/seal-tree.py" "$SR/artifacts/instance/tools/seal-tree.py"
cp "$FAMILY/artifacts/instance/tools/verify-tree.py" "$SR/artifacts/instance/tools/verify-tree.py"
printf 'sealed content\n' > "$SR/kept.txt"
python3 "$SR/artifacts/instance/tools/seal-tree.py" "$SR" >/dev/null 2>&1
python3 "$SR/verify-tree.py" "$SR" >/dev/null 2>&1
assert_eq "reachable: a freshly sealed tree verifies" "$?" "0"

printf 'unlisted\n' > "$SR/stray.txt"
python3 "$SR/verify-tree.py" "$SR" >/dev/null 2>&1
assert_eq "reachable: the seal refuses an unlisted file" "$?" "1"

rm "$SR/stray.txt"
python3 "$SR/verify-tree.py" "$SR" >/dev/null 2>&1
assert_eq "reachable: removing the stray file restores the seal" "$?" "0"

printf 'unlisted again\n' > "$SR/stray.txt"
python3 "$SR/artifacts/instance/tools/seal-tree.py" "$SR" >/dev/null 2>&1
python3 "$SR/verify-tree.py" "$SR" >/dev/null 2>&1
assert_eq "reachable: resealing also restores it, so the remedy is not only deletion" "$?" "0"

# --- the lane detector's vocabulary -----------------------------------------
# A detector whose vocabulary names something that no longer exists is dead in
# that dimension, and dead silently. DEV_PATHS held "skills/dev/" for a while
# after the skills moved; nothing failed, and C-LANE-002 went on passing while
# covering less than it claimed.

python3 "$FAMILY/artifacts/instance/tools/lane-vocabulary-live.py" "$FAMILY" >/dev/null 2>&1
assert_eq "reachable: every path the lane detector knows about still exists" "$?" "0"

# --- the compiled seal rules ------------------------------------------------
# Red would require editing config/seal.v1.json in the live tree, which this
# case must not do. The reachable half is asserted where it is safe: the shipped
# tools are current with their own config, which is the state the remedy
# produces. C-SEAL-001 in the gate owns the red half against real edits.

python3 "$FAMILY/artifacts/instance/tools/gen-seal-rules.py" --check >/dev/null 2>&1
assert_eq "reachable: the compiled seal rules are current with their config" "$?" "0"
