from __future__ import annotations

from copy import deepcopy
import unittest

from support import load_contract


class CertificationMethodAcceptance(unittest.TestCase):
    def test_contract_has_shared_versioned_obligations(self) -> None:
        contract = load_contract()
        self.assertEqual(contract.version, 1)
        self.assertEqual(contract.required_layers, ("mechanical", "inference", "loopstrap"))
        self.assertEqual(contract.inference_task_ids, tuple(f"T{i}" for i in range(9)))
        self.assertTrue(contract.digest.startswith("sha256:"))

    def test_mechanical_plan_covers_required_boundaries(self) -> None:
        contract = load_contract()
        required = {
            "binary_identity",
            "headless_launch",
            "structured_protocol",
            "permission_boundary",
            "timeout",
            "malformed_output",
            "usage_reporting",
            "state_preservation",
            "cleanup",
        }
        self.assertTrue(required.issubset(set(contract.mechanical_obligation_ids)))

    def test_inference_requires_complete_t0_t8_fresh_evidence(self) -> None:
        from loopstrap_core.certification import CertificationEvaluator
        from loopstrap_core.errors import CertificationError

        contract = load_contract()
        observations = [
            {
                "task_id": task_id,
                "status": "PASS",
                "context_lineage": f"fresh-{task_id}",
                "calls": [{"name": "tool", "params": {"task": task_id}, "status": "PASS"}],
                "retries": 0,
                "friction": [],
                "evidence_refs": [f"sha256:{index:064x}"],
            }
            for index, task_id in enumerate(contract.inference_task_ids, 1)
        ]
        self.assertEqual(
            CertificationEvaluator(contract).evaluate_inference(observations),
            "PASS",
        )
        with self.assertRaises(CertificationError):
            CertificationEvaluator(contract).evaluate_inference(observations[:-1])
        duplicated = deepcopy(observations)
        duplicated[-1]["context_lineage"] = duplicated[0]["context_lineage"]
        with self.assertRaises(CertificationError):
            CertificationEvaluator(contract).evaluate_inference(duplicated)

    def test_mutation_requires_verification_and_restoration(self) -> None:
        from loopstrap_core.certification import CertificationEvaluator

        evaluator = CertificationEvaluator(load_contract())
        record = {
            "baseline_digest": "sha256:" + "1" * 64,
            "final_digest": "sha256:" + "1" * 64,
            "mutation_observed": True,
            "verification_ran": True,
            "restoration_verified": True,
        }
        self.assertEqual(evaluator.evaluate_mutation(record), "PASS")
        for field in ("mutation_observed", "verification_ran", "restoration_verified"):
            broken = dict(record)
            broken[field] = False
            self.assertEqual(evaluator.evaluate_mutation(broken), "FAIL")
        broken = dict(record)
        broken["final_digest"] = "sha256:" + "2" * 64
        self.assertEqual(evaluator.evaluate_mutation(broken), "FAIL")
