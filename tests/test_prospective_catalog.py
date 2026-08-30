from datetime import datetime, timezone
from pathlib import Path
import unittest

from etas_challenge.prospective_catalog import parse_and_filter
from etas_challenge.prospective_catalog import request_parameters


HEADER = "#EventID|Time|Latitude|Longitude|Depth/km|Magnitude|MagnitudeType|EventType\n"


class ProspectiveCatalogTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        protocol = __import__("json").loads(
            (self.root / "configs/prospective/three-region-dry-run-v1.json").read_text()
        )
        self.regions = {region["region_id"]: region for region in protocol["regions"]}
        self.start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        self.cutoff = datetime(2026, 8, 31, tzinfo=timezone.utc)

    def test_chile_filters_depth_time_and_rectangle(self):
        body = HEADER + "\n".join(
            [
                "ok|2026-08-10T00:00:00Z|-30|-71|20|5.0|mww|earthquake",
                "deep|2026-08-10T00:00:00Z|-30|-71|120|5.0|mww|earthquake",
                "outside|2026-08-10T00:00:00Z|-10|-71|20|5.0|mww|earthquake",
                "late|2026-09-01T00:00:00Z|-30|-71|20|5.0|mww|earthquake",
            ]
        )
        events = parse_and_filter(self.regions["chile-subduction"], self.root, body.encode(), self.start, self.cutoff)
        self.assertEqual([event.event_id for event in events], ["ok"])

    def test_region_requests_preserve_threshold_contracts(self):
        california = request_parameters(self.regions["california-relm"], self.root, self.start, self.cutoff)
        new_zealand = request_parameters(self.regions["new-zealand-csep"], self.root, self.start, self.cutoff)
        chile = request_parameters(self.regions["chile-subduction"], self.root, self.start, self.cutoff)
        self.assertEqual(california["minmagnitude"], "2.5")
        self.assertNotIn("maxdepth", california)
        self.assertEqual(new_zealand["maxdepth"], "39.999999999")
        self.assertEqual(chile["maxdepth"], "99.999999999")


if __name__ == "__main__":
    unittest.main()
