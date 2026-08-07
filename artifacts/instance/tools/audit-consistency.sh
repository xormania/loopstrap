#!/usr/bin/env bash
# Read-only consistency audit for the active Loopstrap kernel.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
PASS=0
FAIL=0

ok() {
  printf '  \033[32mPASS\033[0m  %s\n' "$1"
  PASS=$((PASS+1))
}

no() {
  printf '  \033[31mFAIL\033[0m  %s\n' "$1"
  FAIL=$((FAIL+1))
}

echo "═══ 1. SEALED SOURCE ═══"
if python3 artifacts/instance/tools/verify-tree.py --allow-runtime "$ROOT" >/dev/null 2>&1; then
  ok "sealed source: exhaustive hashes, modes, paths, and file types"
else
  no "sealed source: tree verification failed"
fi

echo "═══ 2. ACCEPTANCE FREEZE ═══"
if PYTHONDONTWRITEBYTECODE=1 python3 tests/acceptance/verify_freeze.py >/dev/null 2>&1; then
  ok "acceptance freeze: core claim inputs match their independent hash manifest"
else
  no "acceptance freeze: core claim inputs drifted"
fi
if PYTHONDONTWRITEBYTECODE=1 python3 tests/active/verify_freeze.py >/dev/null 2>&1; then
  ok "acceptance freeze: active-surface inputs match their independent hash manifest"
else
  no "acceptance freeze: active-surface inputs drifted"
fi
if PYTHONDONTWRITEBYTECODE=1 python3 tests/integration/verify_freeze.py >/dev/null 2>&1; then
  ok "acceptance freeze: kernel-integration inputs match their independent hash manifest"
else
  no "acceptance freeze: kernel-integration inputs drifted"
fi
if PYTHONDONTWRITEBYTECODE=1 python3 tests/telemetry/verify_freeze.py >/dev/null 2>&1; then
  ok "acceptance freeze: exhaustive telemetry inputs match their independent hash manifest"
else
  no "acceptance freeze: exhaustive telemetry inputs drifted"
fi
if PYTHONDONTWRITEBYTECODE=1 python3 tests/readiness/verify_freeze.py >/dev/null 2>&1; then
  ok "acceptance freeze: CUE and lifecycle readiness inputs match their independent hash manifest"
else
  no "acceptance freeze: CUE and lifecycle readiness inputs drifted"
fi
if PYTHONDONTWRITEBYTECODE=1 python3 tests/certification/verify_freeze.py >/dev/null 2>&1; then
  ok "acceptance freeze: harness certification inputs match their independent hash manifest"
else
  no "acceptance freeze: harness certification inputs drifted"
fi

echo "═══ 3. ACTIVE CONFIGURATION ═══"
CONFIG_RESULT="$(
  PYTHONDONTWRITEBYTECODE=1 python3 -m loopstrap_core.cli validate \
    --workflow config/workflow.v1.json \
    --role-treatments config/role-treatments.v1.json \
    --roles config/roles.v1.json 2>&1
)"
CONFIG_RC=$?
if [ "$CONFIG_RC" -eq 0 ] \
   && grep -q '"workflow_version":1' <<<"$CONFIG_RESULT" \
   && grep -q '"role_treatments":6' <<<"$CONFIG_RESULT" \
   && grep -q '"assigned_roles":6' <<<"$CONFIG_RESULT" \
   && grep -q '"armed":false' <<<"$CONFIG_RESULT"; then
  ok "active configuration: six owner-assigned Role-Treatments validate and remain disabled, uncertified, and unarmed"
else
  no "active configuration: parse or fail-closed state mismatch"
fi

echo "═══ 4. KERNEL SOURCE ═══"
KERNEL_FILES=(
  authority.py
  artifacts.py
  atomic.py
  budget.py
  certification.py
  cli.py
  context.py
  contracts.py
  corpus.py
  driver.py
  evidence.py
  executor.py
  harness.py
  ledger.py
  recovery.py
  specification.py
  state.py
  system.py
  telemetry.py
  verification.py
  workflow.py
  wrappers.py
  workspace.py
)
KERNEL_MISSING=0
for name in "${KERNEL_FILES[@]}"; do
  [ -f "loopstrap_core/$name" ] || KERNEL_MISSING=$((KERNEL_MISSING+1))
done
if [ "$KERNEL_MISSING" -eq 0 ]; then
  ok "kernel source: all deterministic control modules are present"
else
  no "kernel source: $KERNEL_MISSING required module(s) missing"
fi
if PYTHONDONTWRITEBYTECODE=1 bash tests/check-syntax.sh >/dev/null 2>&1; then
  ok "kernel source: every shell/Python source parses and every executable is classified"
else
  no "kernel source: syntax or executable classification failed"
fi
if grep -R -E -q \
  'GPT56Sol|Grok4\.5|depth_cap|child_count|invocation_cap|generator_retry_cap' \
  loopstrap_core; then
  no "kernel source: runtime selection or fixed recursion literal leaked into code"
else
  ok "kernel source: model selections remain data and recursion has no fixed task/depth cap"
fi

echo "═══ 5. ACTIVE ROOT ═══"
if cmp -s AGENTS.md artifacts/agent-configs/root/AGENTS.md \
   && cmp -s CLAUDE.md artifacts/agent-configs/root/CLAUDE.md \
   && cmp -s README.md artifacts/agent-configs/root/README.md; then
  ok "active root: instructions match staged copies"
else
  no "active root: top-level instructions drift from staged copies"
fi
LAUNCH_RESULT="$(bash launch-loop.sh 2>&1)"
LAUNCH_RC=$?
if [ "$LAUNCH_RC" -ne 0 ] \
   && grep -q 'NOT ARMED' <<<"$LAUNCH_RESULT" \
   && grep -qi 'governing' <<<"$LAUNCH_RESULT"; then
  ok "active root: launcher fails closed before any vendor invocation"
else
  no "active root: launcher did not provide the unarmed refusal"
fi

echo "═══ 6. BATTERY WIRING ═══"
if grep -q 'run_leg acceptance ' tests/battery.sh \
   && grep -q 'run_leg active ' tests/battery.sh \
   && grep -q 'run_leg integration ' tests/battery.sh \
   && grep -q 'run_leg telemetry ' tests/battery.sh \
   && grep -q 'run_leg readiness ' tests/battery.sh \
   && grep -q 'run_leg certification ' tests/battery.sh \
   && grep -q 'REQUIRED=(.*acceptance.*active.*integration.*telemetry.*readiness.*certification' tests/battery.sh; then
  ok "battery wiring: core, active, integration, telemetry, readiness, and certification legs have distinct required receipts"
else
  no "battery wiring: acceptance or telemetry receipt/dispatch missing"
fi

echo
echo "═══════════════════════════════════════════"
echo "  $PASS PASS · $FAIL FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "  ACTIVE KERNEL INTERNALLY CONSISTENT"
  echo "═══════════════════════════════════════════"
  exit 0
fi
echo "  $FAIL INCONSISTENCIES — see FAIL above"
echo "═══════════════════════════════════════════"
exit 1
