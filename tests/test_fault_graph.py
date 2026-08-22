import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.fault_graph import (
    axial_strike_degrees,
    build_fault_graph,
    condition_ensemble_on_branch_masks,
    polyline_distance_km,
    sample_initial_state_ensemble,
)
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES


def section(section_id, trace, *, fm31=True, fm32=False):
    branches = {name: (1.0 if name.startswith("fm3_1") else None) for name in SLIP_RATE_BRANCHES}
    return FaultSection(
        section_id=section_id,
        name=f"Fault {section_id}",
        in_fault_model_3_1=fm31,
        in_fault_model_3_2=fm32,
        dip_degrees=90.0,
        upper_seismogenic_depth_km=0.0,
        lower_seismogenic_depth_km=12.0,
        trace_length_km=10.0,
        trace_lat_lon=trace,
        slip_rate_mm_per_year=branches,
        aseismicity_factor=branches,
        coupling_coefficient=branches,
    )


class FaultGraphTests(unittest.TestCase):
    def test_crossing_segments_have_zero_distance(self):
        distance = polyline_distance_km(
            ((34.0, -118.1), (34.2, -117.9)),
            ((34.0, -117.9), (34.2, -118.1)),
        )
        self.assertEqual(distance, 0.0)

    def test_axial_strike_ignores_trace_direction(self):
        forward = axial_strike_degrees(((34.0, -118.0), (34.2, -118.0)))
        reverse = axial_strike_degrees(((34.2, -118.0), (34.0, -118.0)))
        self.assertAlmostEqual(forward, 0.0)
        self.assertAlmostEqual(reverse, 0.0)

    def test_graph_is_symmetric_and_respects_fault_model_alternatives(self):
        sections = [
            section(20, ((34.0, -118.0), (34.1, -118.0))),
            section(10, ((34.0, -117.99), (34.1, -117.99))),
            section(
                30,
                ((34.0, -117.98), (34.1, -117.98)),
                fm31=False,
                fm32=True,
            ),
        ]
        graph = build_fault_graph(sections)
        np.testing.assert_array_equal(graph.section_ids, [10, 20, 30])
        np.testing.assert_allclose(graph.adjacency, graph.adjacency.T)
        self.assertGreater(graph.adjacency[0, 1], 0)
        self.assertEqual(graph.adjacency[0, 2], 0)
        self.assertTrue(np.all(np.diag(graph.adjacency) == 0))

    def test_initial_ensemble_is_deterministic_centered_and_identifiable(self):
        adjacency = np.array(
            [[0.0, 0.8, 0.0], [0.8, 0.0, 0.4], [0.0, 0.4, 0.0]]
        )
        first = sample_initial_state_ensemble(adjacency, particles=32, seed=7)
        second = sample_initial_state_ensemble(adjacency, particles=32, seed=7)
        np.testing.assert_allclose(first.criticality_margin, second.criticality_margin)
        np.testing.assert_allclose(
            first.criticality_margin,
            first.stress_component - first.effective_strength_component,
        )
        np.testing.assert_allclose(np.mean(first.criticality_margin, axis=1), 0, atol=1e-15)
        np.testing.assert_allclose(np.std(first.criticality_margin, axis=1), 1)

    def test_branch_conditioning_zeros_inactive_and_scales_active_sections(self):
        ensemble = sample_initial_state_ensemble(
            np.ones((4, 4)) - np.eye(4), particles=8, seed=3
        )
        masks = np.tile([True, True, True, False], (8, 1))
        conditioned = condition_ensemble_on_branch_masks(ensemble, masks)
        self.assertTrue(np.all(conditioned.criticality_margin[:, 3] == 0))
        np.testing.assert_allclose(
            np.mean(conditioned.criticality_margin[:, :3], axis=1), 0, atol=1e-15
        )
        np.testing.assert_allclose(
            np.std(conditioned.criticality_margin[:, :3], axis=1), 1
        )


if __name__ == "__main__":
    unittest.main()
