import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.ucerf3_faults import SLIP_RATE_BRANCHES, parse_ucerf3_rows


def loading_row(name="Test Fault", section_id=42):
    return [name, section_id, 10.0, 120.0] + [
        1.0,
        2.0,
        3.0,
        4.0,
        "null",
        "null",
        "null",
        "null",
    ] + [0.1] * 8 + [0.9] * 8 + [None] * 11


class Ucerf3FaultTests(unittest.TestCase):
    def setUp(self):
        self.geometry = [
            ["Name", "ID"],
            [
                "Test Fault",
                42,
                True,
                False,
                90.0,
                0.0,
                12.0,
                10.0,
                34.0,
                -118.0,
                34.1,
                -117.9,
            ],
        ]
        self.loading = [
            ["group"],
            ["U3 Section Name", "U3 Sect ID"],
            loading_row(),
        ]

    def test_parses_geometry_and_preserves_loading_branches(self):
        section = parse_ucerf3_rows(
            self.geometry, self.loading, expected_sections=1
        )[0]
        self.assertEqual(section.section_id, 42)
        self.assertEqual(section.trace_lat_lon, ((34.0, -118.0), (34.1, -117.9)))
        self.assertEqual(tuple(section.slip_rate_mm_per_year), SLIP_RATE_BRANCHES)
        self.assertEqual(section.slip_rate_mm_per_year["fm3_1_geologic"], 3.0)
        self.assertIsNone(section.slip_rate_mm_per_year["fm3_2_zeng"])

    def test_rejects_geometry_loading_name_mismatch(self):
        self.loading[2][0] = "Different Fault"
        with self.assertRaises(ValueError):
            parse_ucerf3_rows(self.geometry, self.loading)

    def test_rejects_values_for_absent_fault_model(self):
        self.loading[2][8] = 1.0
        with self.assertRaises(ValueError):
            parse_ucerf3_rows(self.geometry, self.loading)


if __name__ == "__main__":
    unittest.main()
