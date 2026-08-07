#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import sys


request = json.loads(sys.stdin.read())
requested = request["requested_role_treatment"]
configuration_digest = "sha256:" + hashlib.sha256(
    json.dumps(
        requested["configuration"],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
attestation = {
    "schema_version": 1,
    "issuer": "loopstrap-harness-wrapper-v1",
    "invocation_id": request["invocation_id"],
    "role_treatment_id": requested["id"],
    "role": requested["role"],
    "harness": requested["harness"],
    "requested_identity_digest": "sha256:" + hashlib.sha256(
        json.dumps(
            {**requested, "command": request["role_treatment_command"]},
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
        "models": [requested["model_route"]["allowed_resolved_models"][0]],
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
    "sanitized_argv": ["rich-mock-harness"],
    "configuration_digest": configuration_digest,
    "environment_names": [],
}
response = {
    "invocation_id": request["invocation_id"],
    "cell_revision": request["cell_revision"],
    "status": "completed",
    "launch_attestation": attestation,
    "artifacts": [
        {
            "kind": "analysis",
            "ref": "sha256:" + "a" * 64,
        }
    ],
    "claims": [
        {
            "claim_id": "model-claim-1",
            "status": "suspected",
            "proposition": "a seam may need review",
        }
    ],
    "usage": {
        "input_tokens": 11,
        "output_tokens": 7,
        "cost": None,
    },
    "cache_lineage": request.get("cache_lineage"),
}
print(json.dumps(response, sort_keys=True, separators=(",", ":")))
