source "$TROOT/cases/lib.inc"
# Validation-only mode exercises the destructive target gate without reaching
# backup or deletion. The allowed reset root is a non-symlink descendant of the
# dedicated account home, never HOME itself or a path that resolves outside it.
RW="$FIXROOT/reset"; mkdir -p "$RW/inside" "$RW/outside"
ZIP="$RW/courier.zip"; : > "$ZIP"

RESET_VALIDATE_ONLY=1 LOOPSTRAP_ROOT="$HOME" bash "$FAMILY/ops/reset.sh" "$ZIP" > "$RW/home.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "may not equal HOME" "$RW/home.log" \
  && ok "reset: refuses HOME as destructive target" || no "reset: accepted HOME itself"

RESET_VALIDATE_ONLY=1 LOOPSTRAP_ROOT="$RW/outside" bash "$FAMILY/ops/reset.sh" "$ZIP" > "$RW/outside.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "escapes the account boundary" "$RW/outside.log" \
  && ok "reset: refuses a target outside account HOME" || no "reset: accepted an out-of-bound target"

mkdir -p "$HOME/projects/loopstrap"
RESET_VALIDATE_ONLY=1 LOOPSTRAP_ROOT="$HOME/projects/loopstrap" bash "$FAMILY/ops/reset.sh" "$ZIP" > "$RW/inside.log" 2>&1; RC=$?
[ "$RC" -eq 0 ] && grep -q "RESET ROOT VALID" "$RW/inside.log" \
  && ok "reset: accepts a non-symlink descendant of HOME" || no "reset: rejected the declared safe boundary"

ln -s "$HOME/projects/loopstrap" "$HOME/projects/linked-loopstrap"
RESET_VALIDATE_ONLY=1 LOOPSTRAP_ROOT="$HOME/projects/linked-loopstrap" bash "$FAMILY/ops/reset.sh" "$ZIP" > "$RW/link.log" 2>&1; RC=$?
[ "$RC" -ne 0 ] && grep -q "may not be a symlink" "$RW/link.log" \
  && ok "reset: refuses a symlink target" || no "reset: accepted a symlink target"

