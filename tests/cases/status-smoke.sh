source "$TROOT/cases/lib.inc"
# enforces: the wake surface renders (L36/L38)
OUT="$("$FAMILY/ops/steward-status.sh" 2>/dev/null)"
echo "$OUT" | grep -q 'LOOPSTRAP STATUS' && ok "steward-status: banner renders" || no "steward-status: no banner"
echo "$OUT" | grep -q 'members (registry)' && ok "steward-status: registry section renders" || no "steward-status: no registry section"
