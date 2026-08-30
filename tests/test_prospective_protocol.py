import copy
import json
from pathlib import Path
import tempfile
import unittest

from etas_challenge.prospective_protocol import validate_protocol


class ProspectiveProtocolTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.path = self.root / "configs/prospective/three-region-dry-run-v1.json"

    def test_locked_three_region_protocol(self):
        protocol = validate_protocol(self.path, self.root)
        self.assertEqual(
            [region["region_id"] for region in protocol["regions"]],
            ["california-relm", "new-zealand-csep", "chile-subduction"],
        )
        self.assertFalse(protocol["counts_toward_prospective_claim"])

    def test_japan_cannot_enter_protocol(self):
        protocol = json.loads(self.path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(protocol)
        changed["regions"][0]["region_id"] = "japan-a"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as stream:
            json.dump(changed, stream)
            temporary = Path(stream.name)
        self.addCleanup(temporary.unlink)
        with self.assertRaisesRegex(ValueError, "exactly the three admitted regions"):
            validate_protocol(temporary, self.root)


if __name__ == "__main__":
    unittest.main()
