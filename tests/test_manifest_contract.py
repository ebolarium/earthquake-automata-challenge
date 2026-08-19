import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.contracts import load_manifest, validate_reference_manifest


MANIFEST = ROOT / "data" / "manifests" / "reference-comcat25.json"


class ReferenceManifestTests(unittest.TestCase):
    def test_committed_manifest_is_valid(self):
        payload = load_manifest(MANIFEST)
        self.assertEqual(payload["experiment_id"], "etas-reference-comcat25-v1")

    def test_unpinned_reference_is_rejected(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        payload["repositories"]["etas_reference"]["commit"] = "main"
        with self.assertRaisesRegex(ValueError, "full Git commit"):
            validate_reference_manifest(payload)

    def test_committed_source_database_is_rejected(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        payload["local_source_snapshot"]["committed"] = True
        with self.assertRaisesRegex(ValueError, "never be committed"):
            validate_reference_manifest(payload)


if __name__ == "__main__":
    unittest.main()
