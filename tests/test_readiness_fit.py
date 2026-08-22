import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.readiness_fit import (
    ReplayParameters,
    ReadinessFitEvaluator,
    adjusted_background_at_events,
    advance_sparse_group,
    information_gain_per_event,
    sparse_geometry,
)
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES


def test_section(section_id, slip):
    rates = {branch: slip for branch in SLIP_RATE_BRANCHES}
    aseismicity = {branch: 0.0 for branch in SLIP_RATE_BRANCHES}
    coupling = {branch: 1.0 for branch in SLIP_RATE_BRANCHES}
    return FaultSection(
        section_id=section_id,
        name=f"Fault {section_id}",
        in_fault_model_3_1=True,
        in_fault_model_3_2=True,
        dip_degrees=90.0,
        upper_seismogenic_depth_km=0.0,
        lower_seismogenic_depth_km=12.0,
        trace_length_km=10.0,
        trace_lat_lon=((34.0, -118.0), (34.1, -118.0)),
        slip_rate_mm_per_year=rates,
        aseismicity_factor=aseismicity,
        coupling_coefficient=coupling,
    )


class ReadinessFitTests(unittest.TestCase):
    def setUp(self):
        self.ids = np.array([10, 20, 30])
        self.nearest = np.array([[10, 20], [20, 30]])
        self.distances = np.array([[0.0, 10.0], [0.0, 10.0]])

    def test_sparse_geometry_retains_off_fault_and_masks_branch(self):
        geometry = sparse_geometry(
            self.nearest,
            self.distances,
            self.ids,
            np.array([True, True, False]),
            bandwidth_km=10.0,
            cutoff_km=40.0,
            fault_prior_odds=4.0,
        )
        self.assertTrue(np.all(np.sum(geometry.probabilities, axis=1) < 1))
        self.assertEqual(geometry.section_indexes[1, 1], -1)
        self.assertEqual(geometry.probabilities[1, 1], 0)

    def test_zero_sensitivity_reproduces_background_exactly(self):
        geometry = sparse_geometry(
            self.nearest,
            self.distances,
            self.ids,
            np.ones(3, dtype=bool),
            bandwidth_km=10.0,
            cutoff_km=40.0,
            fault_prior_odds=4.0,
        )
        adjusted = adjusted_background_at_events(
            np.array([[2.0, -1.0, 0.5], [-3.0, 1.0, 2.0]]),
            geometry,
            np.array([0.1, 0.2]),
            np.array([0, 1]),
            0.0,
        )
        np.testing.assert_allclose(adjusted, [[0.1, 0.2], [0.1, 0.2]])

    def test_sparse_replay_loading_and_event_are_next_state_only(self):
        geometry = sparse_geometry(
            np.array([[10, 20]]),
            np.array([[0.0, 10.0]]),
            self.ids,
            np.ones(3, dtype=bool),
            bandwidth_km=10.0,
            cutoff_km=40.0,
            fault_prior_odds=4.0,
        )
        state = np.zeros((2, 3))
        updated = advance_sparse_group(
            state,
            np.array([-1.0, 0.0, 1.0]),
            np.ones(3, dtype=bool),
            geometry,
            np.array([1.0]),
            np.array([3.0]),
            ReplayParameters(1.0, 1.0, 0.0, 0.5, 1.0),
        )
        self.assertTrue(np.all(state == 0))
        self.assertGreater(updated[0, 0], updated[0, 1])

    def test_information_gain_is_log_rate_ratio(self):
        gain = information_gain_per_event(np.array([2.0, 1.0]), np.ones(2))
        np.testing.assert_allclose(gain, [np.log(2.0), 0.0])

    def test_underflowed_zero_rate_receives_finite_log_penalty(self):
        gain = information_gain_per_event(np.array([0.0]), np.array([1.0]))
        self.assertTrue(np.isfinite(gain[0]))
        self.assertLess(gain[0], -700)

    def test_full_zero_candidate_exactly_matches_etas(self):
        evaluator = ReadinessFitEvaluator(
            sections=[test_section(10, 1.0), test_section(20, 3.0)],
            section_ids=np.array([10, 20]),
            initial_state=np.tile([-1.0, 1.0], (8, 1)),
            particle_branches=np.asarray(SLIP_RATE_BRANCHES),
            grid_nearest_ids=np.array([[10, 20], [20, 10]]),
            grid_nearest_distances_km=np.array([[0.0, 10.0], [0.0, 10.0]]),
            event_nearest_ids=np.array([[10, 20]]),
            event_nearest_distances_km=np.array([[0.0, 10.0]]),
            background_grid=np.array([0.1, 0.2]),
            all_issue_days=np.array([1], dtype=np.int32),
            event_days=np.array([1], dtype=np.int32),
            event_cells=np.array([0], dtype=np.int32),
            event_magnitudes=np.array([3.0]),
            event_etas_rates=np.array([0.6]),
            event_background_rates=np.array([0.1]),
            event_background_probabilities=np.array([1 / 6]),
        )
        result = evaluator.evaluate(np.zeros(5))
        np.testing.assert_allclose(result.challenger_event_rates, [0.6])
        np.testing.assert_allclose(result.event_gains, [0.0], atol=1e-15)


if __name__ == "__main__":
    unittest.main()
