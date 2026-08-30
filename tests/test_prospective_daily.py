import unittest
import json
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix, identity

from etas_challenge.etas_native import event_rates
from etas_challenge.prospective_daily import advance_california_day
from etas_challenge.prospective_daily import advance_regional_day
from etas_challenge.prospective_daily import california_background_forecast
from etas_challenge.prospective_daily import incremental_event_rates
from etas_challenge.prospective_daily import regional_background_forecast
from etas_challenge.prospective_replay import CH008State
from etas_challenge.readiness_fit import SparseGeometry


PARENT = {
    "full_reset_magnitude": 4.0,
    "magnitude_exponent": 0.4,
    "bpt_aperiodicity": 1.0,
    "graph_neighborhood_mix": 0.5,
    "minimum_branch_consensus": 0.5,
    "background_mixture_fraction": 0.05,
    "renewal_sensitivity": 1.0,
}
CH008 = {
    "prior_exposure": 0.5,
    "memory_half_life_days": 100.0,
    "frailty_neighborhood_mix": 0.0,
    "minimum_log_frailty": 0.0,
    "frailty_weight": 1.0,
    "renewal_weight": 1.0,
    "background_mixture_fraction": 0.25,
}


class ProspectiveDailyTest(unittest.TestCase):
    def test_locked_runtime_keeps_lead_time_and_simulation_count(self):
        root = Path(__file__).resolve().parents[1]
        runtime = json.loads(
            (root / "configs/prospective/daily-runtime-v1.json").read_text()
        )
        self.assertEqual(runtime["california_etas_grid"]["simulations"], 10000)
        self.assertEqual(runtime["issue_schedule"]["minimum_lead_time_minutes"], 1425)
        self.assertFalse(runtime["activation"]["prospective_claim_started"])

    def test_regional_forecast_preserves_background_mass(self):
        state = CH008State(
            age=np.array([0.0, 2.0]),
            exposure=np.array([2.0, 1.0]),
            roots=np.array([2.0, 5.0]),
        )
        forecast = regional_background_forecast(
            state,
            background_mass=np.array([0.2, 0.8]),
            transition=csr_matrix(np.array([[0.0, 1.0], [1.0, 0.0]])),
            parent_parameters=PARENT,
            ch008_parameters=CH008,
        )
        self.assertAlmostEqual(float(np.sum(forecast.baseline_mass)), 1.0)
        self.assertAlmostEqual(float(np.sum(forecast.challenger_mass)), 1.0)
        self.assertFalse(np.allclose(forecast.baseline_mass, forecast.challenger_mass))

    def test_empty_day_advances_regional_exposure_without_observed_roots(self):
        state = CH008State(*(np.zeros(2) for _ in range(3)))
        advanced = advance_regional_day(
            state,
            event_cells=np.array([], dtype=np.int32),
            event_magnitudes=np.array([]),
            event_background_probabilities=np.array([]),
            background_mass=np.array([0.2, 0.3]),
            beta=2.0,
            magnitude_reference=2.5,
            renewal_scale=2.0,
            parent_parameters=PARENT,
            ch008_parameters=CH008,
        )
        np.testing.assert_allclose(advanced.exposure, [0.2, 0.3])
        np.testing.assert_allclose(advanced.roots, 0.0)
        self.assertTrue(np.all(advanced.age > 0))

    def test_california_forecast_and_update_use_branch_geometry(self):
        state = CH008State(
            age=np.array([[1.0, 0.1], [1.0, 0.1]]),
            exposure=np.ones((2, 2)),
            roots=np.array([[4.0, 1.0], [4.0, 1.0]]),
        )
        geometry = SparseGeometry(
            section_indexes=np.array([[0], [1]], dtype=np.int32),
            probabilities=np.ones((2, 1)),
        )
        forecast = california_background_forecast(
            state,
            background_grid=np.array([0.4, 0.6]),
            transitions=[identity(2, format="csr"), identity(2, format="csr")],
            grid_geometries=[geometry, geometry],
            parent_parameter_values=np.array(list(PARENT.values())),
            ch008_parameters=CH008,
        )
        self.assertAlmostEqual(float(np.sum(forecast.challenger_mass)), 1.0)
        event_geometry = SparseGeometry(
            section_indexes=np.array([[0]], dtype=np.int32),
            probabilities=np.array([[0.8]]),
        )
        advanced = advance_california_day(
            state,
            event_geometries=[event_geometry, event_geometry],
            event_magnitudes=np.array([4.0]),
            event_background_probabilities=np.array([0.5]),
            expected_section_background=np.full((2, 2), 0.1),
            beta=2.0,
            magnitude_reference=2.5,
            parent_parameters=PARENT,
            ch008_parameters=CH008,
        )
        self.assertGreater(advanced.roots[0, 0], advanced.roots[0, 1])

    def test_incremental_event_rates_match_full_replay(self):
        parameters = {
            "log10_mu": -2.0,
            "log10_k0": -2.5,
            "a": 1.0,
            "log10_c": -2.0,
            "omega": -0.05,
            "log10_tau": 2.0,
            "log10_d": 0.0,
            "gamma": 0.5,
            "rho": 1.0,
        }
        times = np.array([0.0, 1.0, 1.5, 3.0])
        latitudes = np.array([0.0, 0.1, 0.2, 0.3])
        longitudes = np.array([1.0, 1.1, 1.2, 1.3])
        magnitudes = np.array([3.0, 3.2, 3.1, 3.3])
        expected = event_rates(
            times, latitudes, longitudes, magnitudes,
            magnitude_reference=2.5, parameters=parameters,
        )[2:]
        actual = incremental_event_rates(
            times[:2], latitudes[:2], longitudes[:2], magnitudes[:2],
            times[2:], latitudes[2:], longitudes[2:], magnitudes[2:],
            magnitude_reference=2.5, parameters=parameters,
        )
        np.testing.assert_allclose(actual, expected, rtol=1e-14)


if __name__ == "__main__":
    unittest.main()
