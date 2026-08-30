import unittest

import numpy as np

from etas_challenge.prospective_etas import california_daily_etas_grid
from etas_challenge.training_matrix import GridDefinition


class ProspectiveETASTest(unittest.TestCase):
    def test_daily_grid_is_deterministic_and_keeps_analytical_background(self):
        grid = GridDefinition(
            grid_id="one-cell",
            units_per_degree=10,
            origin_units=np.array([[0, 0]]),
            neighbors=np.full((1, 8), -1, dtype=np.int32),
        )
        arguments = {
            "issue_time": np.datetime64("2026-01-02T00:00:00", "ns"),
            "history_origin_time_ns": np.array(
                [np.datetime64("2026-01-01T00:00:00", "ns").astype(np.int64)]
            ),
            "history_latitudes": np.array([0.05]),
            "history_longitudes": np.array([0.05]),
            "history_magnitudes": np.array([3.0]),
            "grid": grid,
            "background_rates": np.array([0.1]),
            "polygon_lat_lon": np.array(
                [[0.0, 0.0], [0.0, 0.1], [0.1, 0.1], [0.1, 0.0], [0.0, 0.0]]
            ),
            "area_km2": 100.0,
            "beta": 2.0,
            "magnitude_reference": 2.5,
            "magnitude_bin_width": 0.1,
            "parameters": {
                "log10_mu": -3.0,
                "log10_k0": -5.0,
                "a": 1.0,
                "log10_c": -2.0,
                "omega": -0.05,
                "log10_tau": 2.0,
                "log10_d": 0.0,
                "gamma": 0.5,
                "rho": 1.0,
            },
            "simulations": 8,
            "random_seed": 123,
        }
        first = california_daily_etas_grid(**arguments)
        second = california_daily_etas_grid(**arguments)
        np.testing.assert_array_equal(first.rates, second.rates)
        self.assertGreaterEqual(first.rates[0], 0.1)
        self.assertEqual(first.sampled_nonbackground_events, second.sampled_nonbackground_events)


if __name__ == "__main__":
    unittest.main()
