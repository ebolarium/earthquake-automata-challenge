import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.readiness_replay import (
    ObservedEvent,
    StateEvolutionParameters,
    advance_daily_state,
    balanced_particle_branches,
    branch_loading_vector,
    event_section_assignment,
)
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES


def section(section_id, longitude, slip, *, active=True):
    slip_rates = {
        branch: (slip if branch == "fm3_1_geologic" and active else None)
        for branch in SLIP_RATE_BRANCHES
    }
    terms = {branch: (0.0 if value is not None else None) for branch, value in slip_rates.items()}
    coupling = {branch: (1.0 if value is not None else None) for branch, value in slip_rates.items()}
    return FaultSection(
        section_id=section_id,
        name=f"Fault {section_id}",
        in_fault_model_3_1=active,
        in_fault_model_3_2=False,
        dip_degrees=90.0,
        upper_seismogenic_depth_km=0.0,
        lower_seismogenic_depth_km=12.0,
        trace_length_km=11.0,
        trace_lat_lon=((34.0, longitude), (34.1, longitude)),
        slip_rate_mm_per_year=slip_rates,
        aseismicity_factor=terms,
        coupling_coefficient=coupling,
    )


class ReadinessReplayTests(unittest.TestCase):
    def setUp(self):
        self.sections = [
            section(1, -118.0, 1.0),
            section(2, -117.8, 3.0),
            section(3, -117.6, 0.0, active=False),
        ]
        self.loading, self.active = branch_loading_vector(
            self.sections, "fm3_1_geologic"
        )

    def parameters(self, **updates):
        values = {
            "loading_gain_per_year": 0.0,
            "assimilation_gain": 0.0,
            "release_gain": 0.0,
            "release_magnitude_exponent": 0.5,
        }
        values.update(updates)
        return StateEvolutionParameters(**values)

    def test_loading_is_centered_unit_rms_and_branch_masked(self):
        np.testing.assert_allclose(np.mean(self.loading[self.active]), 0)
        np.testing.assert_allclose(np.sqrt(np.mean(self.loading[self.active] ** 2)), 1)
        np.testing.assert_array_equal(self.active, [True, True, False])
        self.assertEqual(self.loading[2], 0)

    def test_event_assignment_retains_off_fault_probability(self):
        assignment, off_fault = event_section_assignment(
            self.sections,
            self.active,
            latitude=34.05,
            longitude=-118.0,
            bandwidth_km=10.0,
            cutoff_km=40.0,
            fault_prior_odds=4.0,
        )
        self.assertGreater(assignment[0], assignment[1])
        self.assertEqual(assignment[2], 0)
        self.assertAlmostEqual(float(np.sum(assignment)) + off_fault, 1.0)

    def test_background_event_assimilates_more_than_triggered_event(self):
        state = np.zeros((2, 3))
        background = ObservedEvent(34.05, -118.0, 3.0, 1.0)
        triggered = ObservedEvent(34.05, -118.0, 3.0, 0.0)
        assimilated = advance_daily_state(
            state,
            self.loading,
            self.sections,
            self.active,
            [background],
            self.parameters(assimilation_gain=1.0),
        )
        ignored = advance_daily_state(
            state,
            self.loading,
            self.sections,
            self.active,
            [triggered],
            self.parameters(assimilation_gain=1.0),
        )
        self.assertGreater(assimilated[0, 0], ignored[0, 0])

    def test_rupture_depletes_near_section_and_preserves_inactive_state(self):
        state = np.array([[0.0, 0.0, 7.0]])
        event = ObservedEvent(34.05, -118.0, 4.0, 0.0)
        updated = advance_daily_state(
            state,
            self.loading,
            self.sections,
            self.active,
            [event],
            self.parameters(release_gain=1.0),
        )
        self.assertLess(updated[0, 0], updated[0, 1])
        self.assertEqual(updated[0, 2], 7.0)

    def test_zero_gain_empty_day_keeps_centered_state(self):
        state = np.array([[-1.0, 1.0, 5.0]])
        updated = advance_daily_state(
            state,
            self.loading,
            self.sections,
            self.active,
            [],
            self.parameters(),
        )
        np.testing.assert_allclose(updated, state)

    def test_particle_branches_are_balanced_and_locked(self):
        branches = balanced_particle_branches(256)
        unique, counts = np.unique(branches, return_counts=True)
        self.assertEqual(len(unique), 8)
        np.testing.assert_array_equal(counts, np.full(8, 32))

    def test_rejects_below_target_magnitude(self):
        with self.assertRaises(ValueError):
            advance_daily_state(
                np.zeros((1, 3)),
                self.loading,
                self.sections,
                self.active,
                [ObservedEvent(34.05, -118.0, 2.4, 1.0)],
                self.parameters(),
            )


if __name__ == "__main__":
    unittest.main()
