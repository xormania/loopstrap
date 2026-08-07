source "$TROOT/cases/lib.inc"
# enforces: THE WALL R2–R6 (L17/L19/L25 vocabulary lanes) · WALL_ALLOW mechanism (L19)
WF="$FIXROOT/wall-t"; mkdir -p "$WF"
# must-fire set: one line per rule
printf 'lsp_math watches the loop for stalls.\n' > "$WF/f2"; "$FAMILY/wall.sh" "$WF/f2" >/dev/null 2>&1; assert_eq "wall R2 fires (member-as-actor)" "$?" "1"
printf 'We use lsp_math to build lsp_math.\n' > "$WF/f3"; "$FAMILY/wall.sh" "$WF/f3" >/dev/null 2>&1; assert_eq "wall R3 fires (product-builds-itself)" "$?" "1"
printf 'Per the lsp_math lexicon the loop must halt.\n' > "$WF/f4"; "$FAMILY/wall.sh" "$WF/f4" >/dev/null 2>&1; assert_eq "wall R4 fires (runtime-doc-as-authority)" "$?" "1"
printf 'The breaker is a component of lsp_math.\n' > "$WF/f5"; "$FAMILY/wall.sh" "$WF/f5" >/dev/null 2>&1; assert_eq "wall R5 fires (dev-inside-product)" "$?" "1"
printf 'The campaign backlog ships in the courier.\n' > "$WF/f6"; "$FAMILY/wall.sh" --lane runtime "$WF/f6" >/dev/null 2>&1; assert_eq "wall R6 fires (dev-vocab-in-contract)" "$?" "1"
# must-NOT-fire set: legitimate mentions + THE WALL'S OWN TEXT (the FP-12 regression, locked)
printf 'cloned repos/lsp_math cleanly.\nlsp_math-spec.md ratified.\nledger: member=lsp_math cid=c1.\nLoopstrap builds lsp_math; this repo is the product and never builds itself.\nlsp_math is never used to build lsp_math.\n' > "$WF/c1"
"$FAMILY/wall.sh" "$WF/c1" >/dev/null 2>&1; assert_eq "wall holds on legit mentions + the wall's own text (FP-12 regression)" "$?" "0"
# allowlist mechanism: exact rule + fixed marker + register citation. A marker
# cannot suppress another rule, and malformed prose is not an allow entry.
printf 'R5 dev-inside-product\truled-exception-marker\tL19\n' > "$WF/allow"
printf 'The breaker is a component of lsp_math. ruled-exception-marker\n' > "$WF/a1"
WALL_ALLOW="$WF/allow" "$FAMILY/wall.sh" "$WF/a1" > "$WF/a1.out" 2>&1; assert_eq "wall-allow suppresses ruled exception" "$?" "0"
grep -q "suppressed by wall-allow" "$WF/a1.out" && ok "suppression is audited in output" || no "suppression not audited"

printf 'lsp_math watches the loop for stalls. ruled-exception-marker\n' > "$WF/a2"
WALL_ALLOW="$WF/allow" "$FAMILY/wall.sh" "$WF/a2" >/dev/null 2>&1; RC=$?
assert_eq "wall-allow is scoped to its named rule" "$RC" "1"

printf 'R5 dev-inside-product\truled-exception-marker\tmissing-citation\n' > "$WF/bad-allow"
WALL_ALLOW="$WF/bad-allow" "$FAMILY/wall.sh" "$WF/a1" >/dev/null 2>&1; RC=$?
assert_eq "wall-allow rejects malformed uncited entries" "$RC" "1"

"$FAMILY/wall.sh" "$WF/does-not-exist" >/dev/null 2>&1; RC=$?
assert_eq "wall refuses missing requested inputs" "$RC" "2"
"$FAMILY/wall.sh" --lane invented "$WF/c1" >/dev/null 2>&1; RC=$?
assert_eq "wall refuses an invalid lane" "$RC" "2"

# Registry keys are parsed as TOML and regex-escaped. A metacharacter-bearing
# member name must match literally, without broadening the wall expression.
WR="$WF/regex-root"; mkdir -p "$WR/artifacts"
cp "$FAMILY/wall.sh" "$WR/wall.sh"
cat > "$WR/artifacts/members.toml" <<'T'
["demo+one"]
repo = "example/demo"
int_branch = "dev"
T
printf 'demo+one watches the loop for stalls.\n' > "$WR/literal"
"$WR/wall.sh" "$WR/literal" >/dev/null 2>&1; RC=$?
assert_eq "wall escapes registry names before regex interpolation" "$RC" "1"
printf 'demooooone watches the loop for stalls.\n' > "$WR/near"
"$WR/wall.sh" "$WR/near" >/dev/null 2>&1; RC=$?
assert_eq "wall does not broaden metacharacter-bearing member names" "$RC" "0"
