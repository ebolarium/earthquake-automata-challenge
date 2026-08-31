from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

from etas_challenge.prospective_forecast import forecast_run_id


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/ch008-three-region-dry-run-activation-v1.json"


class DryRunActivationManifestTest(unittest.TestCase):
    def test_activation_identity_matches_locked_files_and_run_ids(self):
        manifest = json.loads(MANIFEST.read_text())
        self.assertEqual(manifest["purpose"], "non_claim_operational_dry_run")
        self.assertFalse(manifest["counts_toward_prospective_claim"])
        self.assertFalse(
            manifest["promotion_boundary"]["prospective_365_day_test_started"]
        )
        for key in ("protocol", "runtime"):
            record = manifest[key]
            digest = hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, record["sha256"])

        target = datetime.fromisoformat(manifest["first_issue"]["target_start"])
        protocol_id = manifest["protocol"]["protocol_id"]
        self.assertEqual(len(manifest["regions"]), 3)
        for region in manifest["regions"]:
            self.assertEqual(
                region["forecast_run_id"],
                forecast_run_id(protocol_id, region["region_id"], target),
            )
            self.assertEqual(region["forecast_artifacts"], 6)


if __name__ == "__main__":
    unittest.main()
