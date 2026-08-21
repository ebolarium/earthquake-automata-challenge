import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.challenge_contract import (
    load_challenge_contract,
    validate_challenge_contract,
    verify_locked_inputs,
)


CONTRACT = ROOT / "configs" / "challenge" / "challenge-v1.json"


class ChallengeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_committed_contract_and_hashes_are_valid(self):
        payload = load_challenge_contract(CONTRACT)
        verify_locked_inputs(payload, ROOT)
        self.assertEqual(payload["status"], "frozen")

    def test_locked_test_model_selection_is_rejected(self):
        payload = copy.deepcopy(self.payload)
        payload["splits"][-1]["model_selection_allowed"] = True
        with self.assertRaisesRegex(ValueError, "model-selection policy changed"):
            validate_challenge_contract(payload)

    def test_split_gap_is_rejected(self):
        payload = copy.deepcopy(self.payload)
        payload["splits"][1]["start"] = "2019-01-02T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "frozen split bounds changed"):
            validate_challenge_contract(payload)

    def test_missing_locked_input_is_rejected(self):
        payload = copy.deepcopy(self.payload)
        payload["locked_inputs"].pop()
        with self.assertRaisesRegex(ValueError, "complete baseline set"):
            validate_challenge_contract(payload)

    def test_weakened_prospective_gate_is_rejected(self):
        payload = copy.deepcopy(self.payload)
        payload["prospective"]["minimum_issue_days"] = 30
        with self.assertRaisesRegex(ValueError, "at least 365"):
            validate_challenge_contract(payload)

    def test_changed_locked_input_is_rejected(self):
        payload = copy.deepcopy(self.payload)
        payload["locked_inputs"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            verify_locked_inputs(payload, ROOT)


if __name__ == "__main__":
    unittest.main()
