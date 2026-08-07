#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time


parser = argparse.ArgumentParser()
parser.add_argument(
    "--behavior",
    choices=("echo", "malformed", "empty", "duplicate", "slow", "large", "mismatch", "stale", "write"),
    default="echo",
)
args = parser.parse_args()
request = json.loads(sys.stdin.read())

if args.behavior == "malformed":
    print("{not-json")
    raise SystemExit(0)
if args.behavior == "empty":
    raise SystemExit(0)
if args.behavior == "slow":
    time.sleep(5)
if args.behavior == "large":
    print("x" * 200_000)
    raise SystemExit(0)
if args.behavior == "write":
    Path("agent-output.txt").write_text("written only in workspace\n", encoding="utf-8")

requested = dict(request["requested_role_treatment"])
revision = request["cell_revision"]
configuration_digest = "sha256:" + hashlib.sha256(
    json.dumps(
        requested["configuration"],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
observed_model = requested["model_route"]["allowed_resolved_models"][0]
if args.behavior == "mismatch":
    observed_model = "silently-substituted-model"
if args.behavior == "stale":
    revision -= 1

attestation = {
    "schema_version": 1,
    "issuer": "loopstrap-harness-wrapper-v1",
    "invocation_id": request["invocation_id"],
    "role_treatment_id": requested["id"],
    "role": requested["role"],
    "harness": requested["harness"],
    "requested_identity_digest": "sha256:" + hashlib.sha256(
        json.dumps(
            {
                **requested,
                "command": request["role_treatment_command"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest(),
    "sent": {
        "model_selector": requested["model_route"]["selector"],
        "model_provider": requested["model_route"]["provider"],
        "reasoning_control": requested["reasoning"]["control"],
        "reasoning_value": requested["reasoning"]["requested"],
        "expected_wire_reasoning": requested["reasoning"]["expected_wire"],
        "orchestration": requested["reasoning"]["orchestration"],
        "configuration_digest": configuration_digest,
    },
    "observed": {
        "models": [observed_model],
        "reasoning": requested["reasoning"]["expected_wire"],
        "orchestration": requested["reasoning"]["orchestration"],
        "fallback_detected": False,
        "hidden_config_detected": False,
    },
    "proof": {
        "model": "runtime_event",
        "reasoning": "runtime_event",
        "configuration": "sanitized_argv_and_digests",
        "mapping_evidence_ref": None,
    },
    "sanitized_argv": ["mock-harness"],
    "configuration_digest": configuration_digest,
    "environment_names": [],
}

response = {
    "invocation_id": request["invocation_id"],
    "cell_revision": revision,
    "status": "completed",
    "launch_attestation": attestation,
    "artifacts": [],
    "claims": [],
    "usage": {
        "input_tokens": None,
        "output_tokens": None,
        "cost": None,
        "observed_env": sorted(
            key for key in os.environ if key in {"SAFE_VALUE", "SUPER_SECRET", "GH_TOKEN"}
        ),
    },
    "cache_lineage": request.get("cache_lineage"),
}
print(json.dumps(response, sort_keys=True, separators=(",", ":")))
if args.behavior == "duplicate":
    print(json.dumps(response, sort_keys=True, separators=(",", ":")))
