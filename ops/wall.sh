#!/usr/bin/env bash
# ops/wall.sh — THE WALL, executable (D87). Deterministic lane-collapse tripwire.
# Loopstrap (the engine) and its members (the deliverables) are never the
# same thing. This filter fires — loudly — on defined collision signatures, in
# either direction. Same input, same verdict, every time.
#
#   ops/wall.sh <file...>                      lane auto-detected by path
#   ops/wall.sh --sweep                        courier dev-spine + runtime contracts
#   ops/wall.sh --lane dev|runtime <file...>   force direction
#   cat text | ops/wall.sh -                   stdin (defaults dev — this chat IS dev)
#
# FP-12 law: every hit is a QUESTION routed to reasoning, never a verdict alone.
# A clean pass is BOUNDED evidence (these rules, these lines) — never proof.
# Exit: 0 = wall holds · 1 = breach(es).
set -uo pipefail
LANE=""; SWEEP=0; FILES=()
while [ $# -gt 0 ]; do case "$1" in
  --lane)
    [ $# -ge 2 ] || { echo "wall: --lane requires dev|runtime" >&2; exit 2; }
    LANE="$2"; shift 2;;
  --sweep) SWEEP=1; shift;;
  *) FILES+=("$1"); shift;;
esac; done
[ -z "$LANE" ] || [ "$LANE" = dev ] || [ "$LANE" = runtime ] \
  || { echo "wall: invalid lane '$LANE'" >&2; exit 2; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "$SWEEP" = "1" ]; then
  while IFS= read -r f; do FILES+=("$f"); done < <(
    { find "$ROOT/artifacts" -name '*.md' -type f 2>/dev/null
      ls "$ROOT"/*.md 2>/dev/null; } | sort )   # full corpus (2026-07-23 scan: partial sweep was silent)
fi
[ ${#FILES[@]} -gt 0 ] || { echo "usage: ops/wall.sh <file...> | --sweep"; exit 2; }

# Members derive from parsed TOML and are regex-escaped before interpolation.
MEMBERS="$(python3 - "$ROOT/artifacts/members.toml" <<'PY' 2>/dev/null
import re, sys, tomllib
data=tomllib.load(open(sys.argv[1], "rb"))
print("|".join(re.escape(name) for name in sorted(data)))
PY
)" || { echo "wall: member registry is missing or unparseable" >&2; exit 2; }
[ -n "$MEMBERS" ] || { echo "wall: member registry is empty" >&2; exit 2; }
DEVMACH='loop|conductor|campaign|courier|breaker|preflight|judges?|backlog|kickoff|steward'
OUT="$(mktemp)"; trap 'rm -f "$OUT" "$OUT.g" "$OUT.sup"' EXIT

ALLOW="${WALL_ALLOW:-$ROOT/ops/wall-allow.txt}"; SUP=0
allowed(){ # exact TSV: rule-id<TAB>fixed line marker<TAB>L-citation
  [ -f "$ALLOW" ] || return 1
  while IFS=$'\t' read -r rule marker citation extra; do
    case "$rule" in ""|\#*) continue;; esac
    if [ -z "${extra:-}" ] && [ "$rule" = "$1" ] && [ -n "$marker" ] \
       && [[ "$citation" =~ ^L[0-9]+$ ]]; then
      case "$2" in *"$marker"*) return 0;; esac
    fi
  done < "$ALLOW"
  return 1
}
hit(){ if allowed "$1" "$4"; then SUP=$((SUP+1)); echo "$SUP" > "$OUT.sup"; else
  printf '⛔ FUCK YOU — LANE BREACH  [%s]  %s:%s\n    %s\n    wall: %s\n' "$1" "$2" "$3" "$4" "$5" >> "$OUT"; fi; }
scan(){ # $1=rule-id $2=file $3=regex $4=wall-text
  grep -nEi "$3" "$2" 2>/dev/null > "$OUT.g" || return 0
  while IFS=: read -r n line; do hit "$1" "$2" "$n" "$line" "$4"; done < "$OUT.g"
}
scan_r3(){ # R3 with a negation guard: lines ASSERTING the wall ("never ... build") are the wall itself
  grep -nEi "\b($MEMBERS)\b[^.]{0,30}\b(build|builds|building|develops?)\b[^.]{0,25}\b($MEMBERS|itself|loopstrap)\b|\buse[sd]? ($MEMBERS) to (build|run|develop)" "$1" 2>/dev/null \
    | grep -viE '\bnever\b' > "$OUT.g" || return 0
  while IFS=: read -r n line; do hit "R3 product-builds-itself" "$1" "$n" "$line" \
    "A member is never used to build itself. Loopstrap builds; members are built."; done < "$OUT.g"
}
check_dev(){
  # R1 retired 2026-07-22 (L19): 'conductor' is claimed by the dev lane as the runner's
  # name; the slot is reserved for future product-lexicon reserved terms.
  scan "R2 member-as-actor" "$1" \
    "\\b($MEMBERS)\\b[^.]{0,40}\\b(runs|watches|monitors|governs|manages|drives|orchestrates|conducts|controls|gates)\\b[^.]{0,60}\\b($DEVMACH)\\b" \
    "Members are the PRODUCT. A member never acts on Loopstrap machinery."
  scan_r3 "$1"
  scan "R4 parked-as-authority" "$1" \
    "\b(($MEMBERS)[- ]lexicon|($MEMBERS)[- ]docs|($MEMBERS) contract (set|doc)s?)\b[^.]{0,60}\b(govern|governs|authoritative|authority|according|must|requires|binds)" \
    "A member's docs govern that member. No deliverable lexicon governs Loopstrap."
  scan "R5 dev-inside-product" "$1" \
    "\\b($DEVMACH)\\b[^.]{0,30}\\b(inside|within|part of|component of|feature of)\\b[^.]{0,30}\\b($MEMBERS)\\b" \
    "Loopstrap machinery is scaffolding. It is never a component of the product."
}
check_runtime(){
  scan "R6 dev-vocab-in-contract" "$1" \
    '\b(campaign|backlog|kickoff|courier|steward|fable|codex|claude code)\b' \
    "Runtime contracts describe the PRODUCT. Dev-lane machinery does not appear in them."
}
LINES=0; INPUT_FAIL=0
for f in "${FILES[@]}"; do
  if [ "$f" = "-" ]; then t="$OUT.stdin"; cat > "$t"; f="$t"; fi
  [ -f "$f" ] || { echo "wall input missing or non-regular: $f" >&2; INPUT_FAIL=1; continue; }
  LINES=$((LINES + $(wc -l < "$f")))
  lane="$LANE"
  [ -z "$lane" ] && case "$f" in
    */artifacts/contracts/*) lane=runtime;; *) lane=dev;; esac
  case "$lane" in dev) check_dev "$f";; runtime) check_runtime "$f";; esac
done
if [ "$INPUT_FAIL" = 1 ]; then
  echo "WALL REFUSED — one or more requested inputs were not regular files." >&2
  exit 2
fi
if [ -s "$OUT" ]; then
  cat "$OUT"
  N=$(grep -c '^⛔' "$OUT")
  echo; echo "══ WALL BREACHED: $N hit(s) over ${#FILES[@]} file(s), $LINES lines. Every hit is a QUESTION (FP-12) — Fable reasons over each; xor rules."
  exit 1
else
  S=$(cat "$OUT.sup" 2>/dev/null || echo 0)
  echo "WALL HOLDS — no lane breach over ${#FILES[@]} file(s), $LINES lines, rules R2–R6 (R1 retired, L19)."
  [ "$S" != "0" ] && echo "($S hit(s) suppressed by wall-allow.txt — ruled exceptions, citations in the file.)"
  echo "Bounded evidence: these rules, these lines. Not proof of anything beyond them."
  exit 0
fi
