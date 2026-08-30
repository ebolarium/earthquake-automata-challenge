from datetime import datetime, timezone
from pathlib import Path
import json
import unittest

from etas_challenge.prospective_bootstrap import auxiliary_start, calendar_year_windows
from etas_challenge.prospective_bootstrap import validate_contiguous_windows
from etas_challenge.prospective_catalog import CatalogSnapshot
from etas_challenge.prospective_persistence import snapshot_identity


class ProspectiveBootstrapTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        protocol = json.loads(
            (self.root / "configs/prospective/three-region-dry-run-v1.json").read_text()
        )
        self.regions = {region["region_id"]: region for region in protocol["regions"]}

    def test_auxiliary_starts_are_taken_from_locked_etas_models(self):
        starts = {
            region_id: auxiliary_start(region, self.root).date().isoformat()
            for region_id, region in self.regions.items()
        }
        self.assertEqual(
            starts,
            {
                "california-relm": "1971-01-01",
                "new-zealand-csep": "1987-01-01",
                "chile-subduction": "2000-01-01",
            },
        )

    def test_calendar_windows_include_a_partial_final_year(self):
        start = datetime(2024, 6, 1, tzinfo=timezone.utc)
        cutoff = datetime(2026, 8, 30, tzinfo=timezone.utc)
        windows = calendar_year_windows(start, cutoff)
        self.assertEqual(
            windows,
            [
                (start, datetime(2025, 1, 1, tzinfo=timezone.utc)),
                (
                    datetime(2025, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                ),
                (datetime(2026, 1, 1, tzinfo=timezone.utc), cutoff),
            ],
        )

    def test_snapshot_identity_separates_windows_and_collection_kinds(self):
        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        cutoff = datetime(2026, 8, 2, tzinfo=timezone.utc)
        snapshot = CatalogSnapshot("region", start, cutoff, "url", {}, b"", ())
        other_start = CatalogSnapshot(
            "region", datetime(2026, 7, 1, tzinfo=timezone.utc), cutoff, "url", {}, b"", ()
        )
        self.assertNotEqual(
            snapshot_identity(snapshot, "rolling"), snapshot_identity(other_start, "rolling")
        )
        self.assertNotEqual(
            snapshot_identity(snapshot, "rolling"), snapshot_identity(snapshot, "bootstrap")
        )

    def test_contiguous_window_validation_rejects_gaps_and_overlaps(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        middle = datetime(2025, 1, 1, tzinfo=timezone.utc)
        cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
        validate_contiguous_windows([(start, middle), (middle, cutoff)], start, cutoff)
        with self.assertRaisesRegex(ValueError, "gap"):
            validate_contiguous_windows(
                [(start, middle), (datetime(2025, 2, 1, tzinfo=timezone.utc), cutoff)],
                start,
                cutoff,
            )
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_contiguous_windows(
                [(start, middle), (datetime(2024, 12, 1, tzinfo=timezone.utc), cutoff)],
                start,
                cutoff,
            )


if __name__ == "__main__":
    unittest.main()
