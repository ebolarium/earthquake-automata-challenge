import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.fault_grid import (
    nearest_fault_sections,
    nearest_fault_sections_for_points,
    point_to_trace_distance_km,
    project_section_margin,
)
from etas_challenge.training_matrix import GridDefinition
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES


def section(section_id, longitude):
    branch = {name: 1.0 for name in SLIP_RATE_BRANCHES}
    return FaultSection(
        section_id=section_id,
        name=f"Fault {section_id}",
        in_fault_model_3_1=True,
        in_fault_model_3_2=True,
        dip_degrees=90.0,
        upper_seismogenic_depth_km=0.0,
        lower_seismogenic_depth_km=12.0,
        trace_length_km=11.0,
        trace_lat_lon=((34.0, longitude), (34.1, longitude)),
        slip_rate_mm_per_year=branch,
        aseismicity_factor=branch,
        coupling_coefficient=branch,
    )


class FaultGridTests(unittest.TestCase):
    def setUp(self):
        self.grid = GridDefinition.from_payload(
            {
                "schema_version": 1,
                "grid_id": "test",
                "coordinate_units_per_degree": 10,
                "cell_size_degrees": 0.1,
                "num_cells": 2,
                "origin_units": [[-1180, 340], [-1170, 340]],
            }
        )

    def test_point_to_trace_uses_segment_not_only_vertices(self):
        distance = point_to_trace_distance_km(
            np.array([34.05]),
            np.array([-118.0]),
            ((34.0, -118.0), (34.1, -118.0)),
        )
        self.assertLess(distance[0], 1e-9)

    def test_nearest_sections_are_stable_and_distance_sorted(self):
        ids, distances = nearest_fault_sections(
            self.grid, [section(20, -117.0), section(10, -118.0)], neighbors=2
        )
        np.testing.assert_array_equal(ids[0], [10, 20])
        np.testing.assert_array_equal(ids[1], [20, 10])
        self.assertTrue(np.all(np.diff(distances, axis=1) >= 0))

    def test_arbitrary_point_nearest_matches_grid_center_case(self):
        sections = [section(20, -117.0), section(10, -118.0)]
        ids, distances = nearest_fault_sections_for_points(
            np.array([34.05]), np.array([-117.95]), sections, neighbors=2
        )
        self.assertEqual(ids[0, 0], 10)
        self.assertLess(distances[0, 0], distances[0, 1])

    def test_projection_normalizes_and_leaves_unsupported_cells_neutral(self):
        projected = project_section_margin(
            np.array([[10, 20], [10, 20]]),
            np.array([[0.0, 10.0], [100.0, 110.0]]),
            np.array([10, 20]),
            np.array([2.0, 8.0]),
            bandwidth_km=10.0,
            cutoff_km=50.0,
        )
        self.assertGreater(projected[0], 2.0)
        self.assertLess(projected[0], 8.0)
        self.assertEqual(projected[1], 0.0)


if __name__ == "__main__":
    unittest.main()
