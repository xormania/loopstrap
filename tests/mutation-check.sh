#!/usr/bin/env bash
# mutation-check.sh v11 — curated, isolated evidence that each sampled defect
# changes the verdict for its own witness. This is not a mutation score and does
# not claim the sample is complete.
set -uo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULT=0
LOG="$(mktemp)"
SCRATCH="$(mktemp -d)"
BASE_REC="$SCRATCH/base.tsv"
BASE_SUM="$SCRATCH/base-summary.tsv"
MUT_REC="$SCRATCH/mut.tsv"
MUT_SUM="$SCRATCH/mut-summary.tsv"
trap 'rm -rf "$SCRATCH" "$LOG"' EXIT

say(){ printf '%s\n' "$*"; }
verify_source() {
  python3 "$SRC/artifacts/instance/tools/verify-tree.py" "$SRC" >/dev/null 2>&1
}
verify_source || {
  say "ABORT: source tree is not exhaustively hash/mode sealed — reseal before mutation-check."
  exit 8
}
fresh(){ cp -a "$SRC" "$1"; }

run_leg(){ # root leg
  local root="$1" leg="$2"
  : > "$MUT_REC"; : > "$MUT_SUM"
  case "$leg" in
    suite)
      ( cd "$root" && LS_ASSERTION_RECORD="$MUT_REC" LS_SUITE_SUMMARY="$MUT_SUM" \
        bash tests/run-tests.sh ${SUITE_SELECTOR:+"$SUITE_SELECTOR"} ) >"$LOG" 2>&1 ;;
    wall)
      ( cd "$root" && bash ops/wall.sh --sweep ) >"$LOG" 2>&1 ;;
    audit)
      ( cd "$root" && bash artifacts/instance/tools/audit-consistency.sh ) >"$LOG" 2>&1 ;;
    syntax)
      ( cd "$root" && bash tests/check-syntax.sh ) >"$LOG" 2>&1 ;;
    map)
      ( cd "$root" \
        && LS_ASSERTION_RECORD="$MUT_REC" LS_SUITE_SUMMARY="$MUT_SUM" bash tests/run-tests.sh >/dev/null 2>&1 \
        && bash tests/check-register-map.sh "$MUT_REC" "$MUT_SUM" ) >"$LOG" 2>&1 ;;
    battery)
      ( cd "$root" && bash tests/battery.sh ) >"$LOG" 2>&1 ;;
    acceptance)
      ( cd "$root" && bash tests/run-acceptance.sh ) >"$LOG" 2>&1 ;;
    active)
      ( cd "$root" && bash tests/run-active.sh ) >"$LOG" 2>&1 ;;
    integration)
      ( cd "$root" && bash tests/run-integration.sh ) >"$LOG" 2>&1 ;;
    telemetry)
      ( cd "$root" && bash tests/run-telemetry.sh ) >"$LOG" 2>&1 ;;
    readiness)
      ( cd "$root" && PYTHONDONTWRITEBYTECODE=1 python3 tests/readiness/verify_freeze.py \
        && PYTHONDONTWRITEBYTECODE=1 python3 tests/readiness/run.py ) >"$LOG" 2>&1 ;;
    certification)
      ( cd "$root" && PYTHONDONTWRITEBYTECODE=1 python3 tests/certification/verify_freeze.py \
        && PYTHONDONTWRITEBYTECODE=1 python3 tests/certification/run.py ) >"$LOG" 2>&1 ;;
    *)
      say "FATAL: unknown mutation leg $leg"; return 2 ;;
  esac
}

status_of(){ # record case|label
  local file="$1" spec="$2" case_name="${2%%|*}" label="${2#*|}"
  awk -F'\t' -v c="$case_name" -v l="$label" \
    '$2==c && $3==l {print $4; exit}' "$file"
}
failure_line(){ # leg signature
  local leg="$1" signature="$2"
  case "$leg" in
    suite)  grep -F "$signature" "$LOG" | grep -Eq '✗|FATAL' ;;
    wall)   grep -F "$signature" "$LOG" | grep -q '⛔' ;;
    audit)  grep -F "$signature" "$LOG" | grep -q 'FAIL' ;;
    syntax) grep -F "$signature" "$LOG" | grep -q 'SYNTAX' ;;
    map)    grep -qF "$signature" "$LOG" && grep -q 'violation(s)' "$LOG" ;;
    battery) grep -qF "$signature" "$LOG" ;;
    acceptance) grep -qF "$signature" "$LOG" && grep -Eq 'FAIL|ERROR|FREEZE FAILURE' "$LOG" ;;
    active) grep -qF "$signature" "$LOG" && grep -Eq 'FAIL|ERROR|ACTIVE FREEZE FAILURE' "$LOG" ;;
    integration) grep -qF "$signature" "$LOG" && grep -Eq 'FAIL|ERROR|INTEGRATION FREEZE FAILURE' "$LOG" ;;
    telemetry) grep -qF "$signature" "$LOG" && grep -Eq 'FAIL|ERROR|TELEMETRY FREEZE FAILURE' "$LOG" ;;
    readiness) grep -qF "$signature" "$LOG" && grep -Eq 'FAIL|ERROR|READINESS FREEZE FAILURE' "$LOG" ;;
    certification) grep -qF "$signature" "$LOG" && grep -Eq 'FAIL|ERROR|CERTIFICATION FREEZE FAILURE' "$LOG" ;;
  esac
}
assess(){ # name leg label|sig expected
  local name="$1" leg="$2" kind="$3" expected="$4"
  SUITE_SELECTOR=""
  if [ "$leg" = suite ] && [ "$kind" = label ]; then
    SUITE_SELECTOR="${expected%%|*}"
  fi
  if run_leg "$COPY" "$leg"; then
    say "  MISS  $name — $leg stayed GREEN under the broken guard"
    RESULT=1
    return
  fi
  if [ "$kind" = label ]; then
    local before after
    before="$(status_of "$BASE_REC" "$expected")"
    after="$(status_of "$MUT_REC" "$expected")"
    if [ "$before" != PASS ]; then
      say "  FATAL $name — baseline witness [$expected] was not PASS"
      RESULT=1
    elif [ "$after" = PASS ]; then
      say "  DRIFT $name — leg went red but its own witness still PASSED"
      RESULT=1
    else
      say "  ok    $name — [$expected] PASS→${after:-ABSENT}"
    fi
  elif failure_line "$leg" "$expected"; then
    say "  ok    $name — $leg reported [$expected] on a failing line"
  else
    say "  DRIFT $name — $leg went red for another reason; expected [$expected]"
    tail -8 "$LOG" | sed 's/^/        /'
    RESULT=1
  fi
}
mut(){ # file sed-expr name leg kind expected
  local file="$1" expression="$2" name="$3" leg="$4" kind="$5" expected="$6"
  COPY="$SCRATCH/m.$RANDOM.$RANDOM"
  fresh "$COPY"
  sed -i "$expression" "$COPY/$file"
  if cmp -s "$COPY/$file" "$SRC/$file"; then
    say "  FATAL $name — mutation anchor did not apply"
    RESULT=1
    rm -rf "$COPY"
    return
  fi
  local deleted added
  deleted="$(diff -U0 "$SRC/$file" "$COPY/$file" | grep -c '^-[^-]' || true)"
  added="$(diff -U0 "$SRC/$file" "$COPY/$file" | grep -c '^+[^+]' || true)"
  if [ "$deleted" -ne 1 ] || [ "$added" -ne 1 ]; then
    say "  FATAL $name — expected one replaced source line, saw -$deleted/+$added"
    RESULT=1
    rm -rf "$COPY"
    return
  fi
  assess "$name" "$leg" "$kind" "$expected"
  rm -rf "$COPY"
}
env_mut(){ # snippet target name leg kind expected
  local snippet="$1" target="$2" name="$3" leg="$4" kind="$5" expected="$6"
  COPY="$SCRATCH/m.$RANDOM.$RANDOM"
  fresh "$COPY"
  ( cd "$COPY" && eval "$snippet" ) || {
    say "  FATAL $name — mutation snippet failed"
    RESULT=1
    rm -rf "$COPY"
    return
  }
  if cmp -s "$COPY/$target" "$SRC/$target"; then
    say "  FATAL $name — $target did not change"
    RESULT=1
    rm -rf "$COPY"
    return
  fi
  assess "$name" "$leg" "$kind" "$expected"
  rm -rf "$COPY"
}

say "════ mutation check v11 — sampled causal witnesses, isolated copies ════"
BASE="$SCRATCH/baseline"
fresh "$BASE"
if ! run_leg "$BASE" battery; then
  say "ABORT: pristine-copy battery is RED; mutation evidence would be meaningless."
  tail -12 "$LOG" | sed 's/^/    /'
  exit 8
fi
( cd "$BASE" && LS_ASSERTION_RECORD="$BASE_REC" LS_SUITE_SUMMARY="$BASE_SUM" \
  bash tests/run-tests.sh >/dev/null 2>&1 ) || {
  say "ABORT: could not collect the protected green baseline record."
  exit 8
}
say "  baseline: battery GREEN; $(wc -l < "$BASE_REC") protected assertion events"
rm -rf "$BASE"

say "── product guards: break one; its own witness must stop passing ──"
mut ops/wall.sh 's/^  scan "R5 dev-inside-product"/  : scan "R5 dev-inside-product"/' \
  "wall R5 disabled" suite label "wall-filter|wall R5 fires (dev-inside-product)"
mut artifacts/instance/tools/docs_verify.py \
  's/^        elif Counter(document_ids) != Counter(index_ids):/        elif False:/' \
  "docs bijection disabled" suite label \
  "docs-standard|docs-standard: an unindexed clause FAILS the bijection (hashes true — decontaminated)"
mut ops/sovereign.sh \
  's/^    cp -p -- "$backup" "$target" || fail "restore failed: $target"/    true # mutation: restore disabled/' \
  "sovereign restore disabled" suite label \
  "sovereign-walls|sovereign walls on: guard restored byte-exact"
mut ops/land.sh \
  's/^    rm -f -- "$stale" || fail "stale removal failed: $stale"/    true # mutation: stale removal disabled/' \
  "landing stale removal disabled" suite label \
  "landing|landing: stale regular file removed"
mut ops/install-configs.sh \
  's/^    missing_repos=.*; fail=1; drift=1/    missing_repos=$((missing_repos+1)); : # mutation: absence licensed/' \
  "installer absence requirement disabled" suite label \
  "install|install: --check fails when a registered repo is absent"
mut artifacts/instance/tools/token-breaker.py \
  's/^        "turns": len(per),/        "turns": len(per) + 1,/' \
  "summary turn dedup disabled" suite label \
  "breaker-wires|summary: turns count unique assistant message ids"
mut artifacts/instance/tools/token-breaker.py \
  '84c\    print(os.path.join(os.path.dirname(os.path.abspath(sys.argv[2])), sys.argv[3], "override.env"))' \
  "breaker override path disconnected" suite label \
  "breaker-wires|override path: breaker consumes sovereign's canonical file"
mut ops/custody-sweep.sh \
  's|^SNAP="$(mktemp -d "$DST/plan-sweep-$STAMP.XXXXXX")"|SNAP="$DST/plan-sweep-fixed"; mkdir "$SNAP"|' \
  "custody snapshot uniqueness disabled" suite label \
  "custody-sweep|custody: second sweep exits 0"
mut ops/reset.sh \
  's|^  "$HOME_REAL") die "LOOPSTRAP_ROOT may not equal HOME; xor/ could not be set aside safely" ;;|  "$HOME_REAL") : ;;|' \
  "reset HOME refusal disabled" suite label \
  "reset-boundary|reset: refuses HOME as destructive target"
mut ops/wall.sh \
  '91c\  [ -f "$f" ] || { echo "wall input missing or non-regular: $f" >&2; continue; }' \
  "wall missing-input refusal disabled" suite label \
  "wall-filter|wall refuses missing requested inputs"
mut tests/mocks/claude \
  '17c\    *) exit 0 ;;' \
  "Claude mock made permissive" suite label \
  "breaker-wires|strict mock: claude rejects unsupported invocation"
mut loopstrap_core/authority.py \
  '79c\    COORDINATION_ACTS: ClassVar[set[str]] = {"dispatch", "advance", "park", "reopen", "promote"}' \
  "Conductor granted promotion authority" acceptance sig \
  "test_conductor_authorization_cannot_grant_write_or_git_acts"
mut loopstrap_core/workflow.py \
  '216c\        if False: # mutation: incomplete obligation map accepted' \
  "test-basis obligation coverage disabled" acceptance sig \
  "test_planning_is_impossible_before_frozen_obligation_mapped_tests"
mut loopstrap_core/workspace.py \
  '170c\        if False: # mutation: executor permit disabled' \
  "executor-only promotion disabled" acceptance sig \
  "test_direct_or_failed_promotion_is_refused"
mut loopstrap_core/wrappers.py \
  's/^        if not models or not set(models).issubset($/        if False and ( # mutation: model substitution accepted/' \
  "observed model allowlist disabled" acceptance sig \
  "test_malformed_empty_duplicate_stale_and_config_drift_responses_refuse"
mut loopstrap_core/ledger.py \
  '95c\            if False: # mutation: event hash mismatch accepted' \
  "ledger tamper check disabled" acceptance sig \
  "test_ledger_is_sequence_numbered_hash_chained_and_tamper_evident"
mut loopstrap_core/budget.py \
  's/^        if self._hard_limit_breached(prospective):/        if False: # mutation: hard limit ignored/' \
  "hard budget limit disabled" acceptance sig \
  "test_hard_limit_overrides_positive_expected_value"
mut loopstrap_core/corpus.py \
  '125c\        if assessment.sufficient: # mutation: contract impact may auto-resolve' \
  "corpus contract-impact boundary disabled" acceptance sig \
  "test_only_interior_nonobservable_choice_can_auto_resolve"
mut loopstrap_core/system.py \
  's/^        if authorization.act != "dispatch":/        if False: # mutation: any coordination act may dispatch/' \
  "dispatch act boundary disabled" integration sig \
  "test_dispatch_rejects_non_dispatch_authorization"
mut loopstrap_core/harness.py \
  's/^        if not isinstance(row\["enabled"\], bool):/        if False: # mutation: enablement coercion restored/' \
  "Role-Treatment boolean schema disabled" integration sig \
  "test_configuration_rejects_boolean_coercion_and_bad_containers"
mut loopstrap_core/workflow.py \
  's/^            if overlap:/            if False: # mutation: overlapping obligations accepted/' \
  "decomposition overlap check disabled" integration sig \
  "test_decomposition_rejects_overlapping_obligation_ownership"
mut loopstrap_core/workflow.py \
  's/^        if leaf and unresolved_seams:/        if False: # mutation: invalid review can mutate state/' \
  "pre-review seam refusal disabled" integration sig \
  "test_rejected_pre_review_is_atomic"
mut loopstrap_core/system.py \
  's/^        if role not in self.router.roles:/        if True: # mutation: configured provenance bypassed/' \
  "configured review provenance disabled" integration sig \
  "test_configured_reviews_require_job_provenance_and_see_candidate"
mut loopstrap_core/system.py \
  's/^            return candidates\[0\]/            return self.current_snapshot() # mutation: reviewer sees old candidate/' \
  "result reviewer candidate footing disabled" integration sig \
  "test_configured_reviews_require_job_provenance_and_see_candidate"
mut loopstrap_core/system.py \
  's/^        if blocking:/        if False: # mutation: verified claim cannot stop promotion/' \
  "promotion claim blocker disabled" integration sig \
  "test_verified_claim_blocks_promotion"
mut loopstrap_core/system.py \
  's/^            "integration.recorded",/            "integration.unrecorded",/' \
  "integration event disconnected" integration sig \
  "test_recursive_child_then_parent_integration_is_ledgered"
mut loopstrap_core/system.py \
  's/^            plan.visible_digest != cell.visible_tests_digest$/            False/' \
  "visible test-basis binding disabled" integration sig \
  "test_digest_bound_visible_and_holdout_verification_plan"
mut loopstrap_core/harness.py \
  's/^            "artifacts": list(self.artifacts),/            "artifacts_removed": list(self.artifacts),/' \
  "structured harness artifacts dropped" integration sig \
  "test_structured_harness_artifacts_and_claims_are_persisted"
mut loopstrap_core/budget.py \
  's/^    if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:/    if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or False:/' \
  "negative continuous resource values accepted" integration sig \
  "test_invalid_resource_values_cannot_reduce_or_invert_budget_accounting"
mut loopstrap_core/telemetry.py \
  's/PRAGMA journal_mode=WAL/PRAGMA journal_mode=DELETE/' \
  "telemetry WAL durability disabled" telemetry sig \
  "test_versioned_wal_store_is_idempotent_append_only_and_tamper_evident"
mut loopstrap_core/telemetry.py \
  's/^        _reject_sensitive(payload)$/        pass # mutation: sensitive payload accepted/' \
  "telemetry credential refusal disabled" telemetry sig \
  "test_sensitive_payload_is_refused_before_persistence"
mut loopstrap_core/telemetry.py \
  '0,/^                    "unavailable" if value is None else "observed",$/s//                    "observed", # mutation: missing usage converted to observation/' \
  "telemetry unavailable status erased" telemetry sig \
  "test_raw_usage_identity_references_paths_and_relationships_are_lossless"
mut loopstrap_core/system.py \
  's/^        self.telemetry.capture_available_references($/        if False: self.telemetry.capture_available_references( # mutation: byte capture disconnected/' \
  "telemetry artifact byte capture disconnected" telemetry sig \
  "test_successful_attempt_mirrors_ledger_process_paths_bytes_and_lineage"
mut loopstrap_core/bounded.py \
  's/^        duration_ns=ended_monotonic_ns - started_monotonic_ns,$/        duration_ns=ended_monotonic_ns - started_monotonic_ns + 1, # mutation: duration relationship corrupted/' \
  "process duration relationship corrupted" telemetry sig \
  "test_successful_attempt_mirrors_ledger_process_paths_bytes_and_lineage"
mut loopstrap_core/system.py \
  '0,/^            "harness.started",$/s//            "harness.unstarted", # mutation: attempt-start boundary disconnected/' \
  "harness start telemetry disconnected" telemetry sig \
  "test_successful_attempt_mirrors_ledger_process_paths_bytes_and_lineage"
mut loopstrap_core/specification.py \
  's/^        if digest != self.pin.sha256:/        if False: # mutation: CUE executable digest ignored/' \
  "CUE executable pin disabled" readiness sig \
  "test_cue_tool_pin_rejects_wrong_digest_or_version"
mut loopstrap_core/contracts.py \
  's/^                if source.schema_ref != target.schema_ref:/                if False: # mutation: incompatible connection accepted/' \
  "composite connection compatibility disabled" readiness sig \
  "test_composite_rejects_incompatible_connection"
mut loopstrap_core/driver.py \
  's/^                return DriverOutcome(\"parked\", actions, root.cell_id)/                return DriverOutcome(\"complete\", actions, root.cell_id)/' \
  "driver refusal reported complete" readiness sig \
  "test_invalid_role_result_parks_without_guessing"
mut loopstrap_core/system.py \
  's/^        if existing is not None:/        if False: # mutation: completed dispatch cannot be reused/' \
  "completed dispatch reuse disabled" readiness sig \
  "test_resume_reuses_completed_dispatch"
mut loopstrap_core/evidence.py \
  's/^                or evidence.producer_id not in evidence.subject_producer_ids$/                or True # mutation: self-authored evidence accepted/' \
  "evidence independence disabled" readiness sig \
  "test_independence_rejects_self_authored_evidence"
mut loopstrap_core/evidence.py \
  's/^            and current_revisions.get(evidence.cell_id) == evidence.cell_revision$/            and True # mutation: stale evidence accepted/' \
  "evidence revision binding disabled" readiness sig \
  "test_stale_wrong_incomplete_or_findings_block_acceptance"
mut loopstrap_core/evidence.py \
  '433c\                f"{match.group(1)}{match.group(2)}[VISIBLE]"' \
  "raw evidence redaction marker disabled" readiness sig \
  "test_raw_execution_is_retained_with_secret_redaction"
mut loopstrap_core/system.py \
  's/^            execution_custodian=RawExecutionCustodian(artifacts),/            execution_custodian=None, # mutation: dispatcher raw custody disconnected/' \
  "harness raw custody disconnected" readiness sig \
  "test_raw_execution_is_retained_with_secret_redaction"
mut loopstrap_core/certification.py \
  's/^            if any(receipt.layer_results\[layer\] != "PASS" for layer in REQUIRED_LAYERS):/            if False: # mutation: non-PASS receipt accepted/' \
  "certification status gate disabled" certification sig \
  "test_nonpass_layer_cannot_become_certified"
mut loopstrap_core/certification.py \
  's/^            if not all(item.matches_current_bytes() for item in receipt.executables):/            if False: # mutation: executable drift ignored/' \
  "certified executable byte binding disabled" certification sig \
  "test_complete_identity_and_executable_drift_invalidate"
mut loopstrap_core/harness.py \
  's/^            or not self.certification_authority.is_certified(role_treatment)$/            or False # mutation: receipt gate bypassed/' \
  "role router receipt requirement disabled" certification sig \
  "test_router_requires_enabled_and_matching_receipt"
mut loopstrap_core/harness.py \
  's/^            if key not in {"enabled", "command"}$/            if key not in {"enabled", "command", "role"} # mutation: Role omitted/' \
  "Role-Treatment Role identity omitted" certification sig \
  "test_every_identity_bearing_role_treatment_field_changes_its_digest"
mut loopstrap_core/harness.py \
  's/^            if role_treatment.role != role:/            if False: # mutation: wrong Role-Treatment assignment accepted/' \
  "Role-Treatment Role binding disabled" certification sig \
  "test_router_rejects_a_role_treatment_for_a_different_role"
mut loopstrap_core/wrappers.py \
  's/^        if configuration\["user_config_policy"\] != "exclude":/        if False: # mutation: hidden user config accepted/' \
  "wrapper hidden-config exclusion disabled" certification sig \
  "test_wrapper_refuses_hidden_config_and_unapproved_invocation_override"
mut config/harness-profiles.v1.json \
  's/^        "--strict-config",/        "--not-strict-config",/' \
  "Codex native strict-config control removed" certification sig \
  "test_one_contract_compiles_three_harness_native_interfaces"
mut loopstrap_core/wrappers.py \
  's/^        if observed\["fallback_detected"\] is not False:/        if False: # mutation: observed fallback accepted/' \
  "wrapper fallback refusal disabled" certification sig \
  "test_launch_attestation_separates_requested_sent_and_observed"
mut loopstrap_core/wrappers.py \
  's/^        if reasoning_proof not in role_treatment.reasoning.proof_sources:/        if False: # mutation: unproved reasoning accepted/' \
  "wrapper reasoning proof-source guard disabled" certification sig \
  "test_launch_attestation_separates_requested_sent_and_observed"
mut loopstrap_core/certification.py \
  's/^            if lineage in lineages:/            if False: # mutation: reused inference context accepted/' \
  "fresh inference lineage requirement disabled" certification sig \
  "test_inference_requires_complete_t0_t8_fresh_evidence"
mut loopstrap_core/certification.py \
  's/^            and row\["restoration_verified"\]$/            and True # mutation: restoration evidence ignored/' \
  "mutation restoration requirement disabled" certification sig \
  "test_mutation_requires_verification_and_restoration"
mut loopstrap_core/harness.py \
  '0,/^            if self.execution_custodian is not None:$/s//            if False: # mutation: failed-stream custody disconnected/' \
  "failed harness partial custody disabled" certification sig \
  "test_partial_stream_failures_are_custodied_and_refused"
mut loopstrap_core/certification.py \
  's/^            if existing.usage_digest != usage_digest:/            if False: # mutation: conflicting repeat charge accepted/' \
  "usage charge conflict check disabled" certification sig \
  "test_restart_reuses_completion_without_double_charge"
mut loopstrap_core/certification.py \
  's/^            if all($/            if True or all( # mutation: incomplete conformance accepted/' \
  "conformance obligation verdict disabled" certification sig \
  "test_real_cell_path_custodies_charges_and_accepts"
mut loopstrap_core/system.py \
  's/^        self._checkpoint(f"job.completed:{job.job_id}")$/: # mutation: durable completion checkpoint disabled/' \
  "pre-completion durable job checkpoint disabled" certification sig \
  "test_real_cell_path_custodies_charges_and_accepts"

say "── harness and evidence channel: corrupt them; they must accuse themselves ──"
env_mut ': > tests/cases/status-smoke.sh' tests/cases/status-smoke.sh \
  "case emptied" suite sig "produced ZERO assertions"
env_mut 'sed -i "2i exit 0" tests/cases/status-smoke.sh' tests/cases/status-smoke.sh \
  "case exits early with zero" suite sig "did not reach the end of its file"
env_mut 'sed -i "2i no(){ :; }" tests/cases/status-smoke.sh' tests/cases/status-smoke.sh \
  "case shadows protected helper" suite sig "attempted to shadow an assertion helper"
mut tests/run-tests.sh \
  '39c\  : # mutation: pass helper no longer counts' \
  "canonical pass helper made vacuous" suite sig "canonical assertion-helper self-test failed"
env_mut 'printf "\\nif then fi\\n" >> ops/steward-status.sh' ops/steward-status.sh \
  "operator syntax broken" syntax sig "SYNTAX ops/steward-status.sh"
env_mut 'printf "\\nThe steward runs preflight inside lsp_math to gate the campaign backlog.\\n" >> artifacts/methods/deliverable-docs-standard.md' \
  artifacts/methods/deliverable-docs-standard.md \
  "lane breach planted" wall sig "LANE BREACH"
env_mut 'printf "x" >> README.md' README.md \
  "sealed byte corrupted" audit sig "tree verification failed"
env_mut 'printf "\n# post-freeze drift\n" >> tests/acceptance/claims.toml' \
  tests/acceptance/claims.toml \
  "frozen acceptance claim drifted" acceptance sig \
  "FREEZE FAILURE: drift: tests/acceptance/claims.toml"
env_mut 'printf "\n# post-freeze drift\n" >> tests/active/claims.toml' \
  tests/active/claims.toml \
  "frozen active claim drifted" active sig \
  "ACTIVE FREEZE FAILURE: drift: tests/active/claims.toml"
env_mut 'printf "\n# post-freeze drift\n" >> tests/integration/claims.toml' \
  tests/integration/claims.toml \
  "frozen integration claim drifted" integration sig \
  "INTEGRATION FREEZE FAILURE: drift: tests/integration/claims.toml"
env_mut 'printf "\n# post-freeze drift\n" >> tests/telemetry/claims.toml' \
  tests/telemetry/claims.toml \
  "frozen telemetry claim drifted" telemetry sig \
  "TELEMETRY FREEZE FAILURE: drift: tests/telemetry/claims.toml"
env_mut 'printf "\n# post-freeze drift\n" >> tests/readiness/claims.toml' \
  tests/readiness/claims.toml \
  "frozen readiness claim drifted" readiness sig \
  "READINESS FREEZE FAILURE: drift: tests/readiness/claims.toml"
env_mut 'printf "\n# post-freeze drift\n" >> tests/certification/claims.toml' \
  tests/certification/claims.toml \
  "frozen certification claim drifted" certification sig \
  "CERTIFICATION FREEZE FAILURE: drift: tests/certification/claims.toml"
mut config/roles.v1.json \
  '0,/"role_treatment": "planner-v1"/s//"role_treatment": "implementer-v1"/' \
  "owner role assignment guessed" active sig \
  "test_role_policy_uses_owner_assignments_and_keeps_independence_rules"
mut config/roles.v1.json \
  '0,/"different_context_lineage": true/s//"different_context_lineage": false/' \
  "context-lineage independence disabled" active sig \
  "test_role_policy_uses_owner_assignments_and_keeps_independence_rules"
mut config/role-treatments.v1.json \
  '0,/"enabled": false/s//"enabled": true/' \
  "uncertified Role-Treatment owner-enabled" active sig \
  "test_role_treatment_config_is_exact_owner_selection_and_uncertified"
mut launch-loop.sh \
  '7c\codex >/dev/null 2>\&1; echo "NOT ARMED — governing inputs incomplete" >\&2' \
  "unarmed launcher invokes a vendor" active sig \
  "test_old_launcher_fails_closed_as_unarmed_before_any_vendor_call"
mut loopstrap_core/cli.py \
  '85c\    events = []  # mutation: ledger verification and replay bypassed' \
  "status ledger verification disabled" active sig \
  "test_cli_status_verifies_ledger_and_replays_observed_state"
env_mut 'sed -i "/summary: permission denials are reported/d" tests/REGISTER-MAP.tsv' \
  tests/REGISTER-MAP.tsv "map row deleted" map sig "RAN BUT UNMAPPED"
mut tests/battery.sh \
  's/^run_leg wall /: # mutation: wall dispatch deleted #/' \
  "battery dispatcher line deleted" battery sig "required leg 'wall' did not run"
mut tests/battery.sh \
  's/^run_leg acceptance /: # mutation: acceptance dispatch deleted #/' \
  "acceptance battery dispatch deleted" battery sig \
  "required leg 'acceptance' did not run"
mut tests/battery.sh \
  's/^run_leg active /: # mutation: active dispatch deleted #/' \
  "active battery dispatch deleted" battery sig \
  "required leg 'active' did not run"
mut tests/battery.sh \
  's/^run_leg integration /: # mutation: integration dispatch deleted #/' \
  "integration battery dispatch deleted" battery sig \
  "required leg 'integration' did not run"
mut tests/battery.sh \
  's/^run_leg telemetry /: # mutation: telemetry dispatch deleted #/' \
  "telemetry battery dispatch deleted" battery sig \
  "required leg 'telemetry' did not run"
mut tests/battery.sh \
  's/^run_leg readiness /: # mutation: readiness dispatch deleted #/' \
  "readiness battery dispatch deleted" battery sig \
  "required leg 'readiness' did not run"
mut tests/battery.sh \
  's/^run_leg certification /: # mutation: certification dispatch deleted #/' \
  "certification battery dispatch deleted" battery sig \
  "required leg 'certification' did not run"

if [ "$RESULT" -eq 0 ]; then
  if verify_source; then
    say "════ MUTATIONS DETECTED — every sampled break changed its own witness; source tree untouched ════"
  else
    say "════ ISOLATION FAILURE — source seal changed during mutation-check ════"
    RESULT=1
  fi
else
  say "════ MUTATION CHECK FAILED — missed, vacuous, or misattributed witness above ════"
fi
exit "$RESULT"
