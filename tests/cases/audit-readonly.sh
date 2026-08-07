source "$TROOT/cases/lib.inc"
# The consistency audit may report red, but judging the tree must never rewrite
# the tree. Snapshot every regular file's mode and digest around a real run.
AW="$FIXROOT/audit"; mkdir -p "$AW"
cp -a "$FAMILY" "$AW/root"
fingerprint() {
  local root="$1"
  while IFS= read -r -d '' path; do
    printf '%s\t%s\t%s\n' \
      "$(stat -c %a "$path")" "${path#"$root"/}" "$(sha256sum "$path" | cut -d' ' -f1)"
  done < <(find "$root" -type f -print0 | sort -z)
}
fingerprint "$AW/root" > "$AW/before"
( cd "$AW/root" && bash artifacts/instance/tools/audit-consistency.sh > "$AW/audit.log" 2>&1 ); RC=$?
fingerprint "$AW/root" > "$AW/after"
cmp -s "$AW/before" "$AW/after" \
  && ok "audit: a real run leaves every source byte and mode untouched" || no "audit: judging the tree rewrote source state"
[ "$RC" -eq 0 ] || [ "$RC" -eq 1 ] \
  && ok "audit: returns a normalized verdict code" || no "audit: returned an unbounded failure count (rc=$RC)"

