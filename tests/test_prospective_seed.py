from pathlib import Path
import unittest

from etas_challenge.prospective_seed import build_seed_records


class ProspectiveSeedTest(unittest.TestCase):
    def test_seed_contains_three_regions_and_five_models(self):
        root = Path(__file__).resolve().parents[1]
        records = build_seed_records(
            root / "configs/prospective/three-region-dry-run-v1.json", root
        )
        self.assertEqual(len(records["regions"]), 3)
        self.assertEqual(len(records["models"]), 5)
        self.assertEqual(
            {record["region_id"] for record in records["regions"]},
            {"california-relm", "new-zealand-csep", "chile-subduction"},
        )
        self.assertEqual(len({record["model_id"] for record in records["models"]}), 5)


if __name__ == "__main__":
    unittest.main()
