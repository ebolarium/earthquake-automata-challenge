import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.evaluation import validate_pycsep_manifest


class PyCSEPEvaluationContractTests(unittest.TestCase):
    def test_committed_manifest_is_valid(self):
        path = ROOT / "data" / "manifests" / "pycsep-day7-v1.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        validate_pycsep_manifest(manifest)
        self.assertEqual(manifest["protocol"]["n_simulations"], 10_000)
        self.assertEqual(manifest["protocol"]["region_nodes"], 7_682)
        self.assertFalse(
            manifest["results"]["etas"]["number"][
                "rejected_at_two_sided_5_percent"
            ]
        )

    def test_complete_manifest_contract(self):
        validate_pycsep_manifest(self._manifest())

    def test_missing_test_is_rejected(self):
        manifest = self._manifest()
        del manifest["results"]["etas"]["spatial"]
        with self.assertRaisesRegex(ValueError, "incomplete etas tests"):
            validate_pycsep_manifest(manifest)

    def test_frozen_config_uses_documented_day_seven_and_relm_grid(self):
        path = ROOT / "configs" / "evaluation" / "comcat25-pycsep-day7-v1.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["earthquakenpp_test_day"], 7)
        self.assertEqual(config["issue_time"], "2007-01-08T00:00:00Z")
        self.assertEqual(config["n_simulations"], 10_000)
        self.assertEqual(config["pycsep"]["expected_spatial_nodes"], 7_682)
        self.assertEqual(config["expected_observation"]["history_event_count"], 31_886)
        self.assertEqual(config["expected_observation"]["event_count"], 3)

    @staticmethod
    def _manifest():
        tests = {
            name: {"status": "normal", "quantile": 0.5}
            for name in ("number", "spatial", "pseudolikelihood", "magnitude")
        }
        return {
            "schema_version": 1,
            "status": "completed",
            "tool": {},
            "inputs": {},
            "protocol": {"n_simulations": 10_000},
            "outputs": {"forecast_sha256": "a" * 64},
            "results": {"etas": copy.deepcopy(tests), "poisson": tests},
        }


if __name__ == "__main__":
    unittest.main()
