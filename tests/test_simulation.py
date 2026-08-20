import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.daily_replay import DailyCatalog
from etas_challenge.parameters import ETASParameters
from etas_challenge.simulation import (
    ETASContinuationSimulator,
    destination_points,
    points_in_polygon,
)


PARAMETERS = ETASParameters(
    mu=0.1,
    k0=1e-4,
    a=1.0,
    c=0.01,
    omega=-0.1,
    tau=100.0,
    d=0.2,
    gamma=0.5,
    rho=0.7,
)
POLYGON = np.array(
    [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
)


class SimulationTests(unittest.TestCase):
    def test_issue_time_event_is_not_history(self):
        original = self._catalog(magnitude_at_issue=2.5)
        mutated = self._catalog(magnitude_at_issue=9.0)
        first = self._simulator(original).simulate(1.0, np.random.default_rng(42))
        second = self._simulator(mutated).simulate(1.0, np.random.default_rng(42))
        np.testing.assert_array_equal(first.times, second.times)
        np.testing.assert_array_equal(first.latitudes, second.latitudes)
        np.testing.assert_array_equal(first.longitudes, second.longitudes)
        np.testing.assert_array_equal(first.magnitudes, second.magnitudes)

    def test_simulation_is_deterministic_and_inside_contract(self):
        simulator = self._simulator(self._catalog())
        first = simulator.simulate(1.0, np.random.default_rng(7))
        second = simulator.simulate(1.0, np.random.default_rng(7))
        np.testing.assert_array_equal(first.times, second.times)
        np.testing.assert_array_equal(first.latitudes, second.latitudes)
        np.testing.assert_array_equal(first.longitudes, second.longitudes)
        self.assertTrue(np.all(first.times >= 1.0))
        self.assertTrue(np.all(first.times < 2.0))
        self.assertTrue(
            np.all(points_in_polygon(first.latitudes, first.longitudes, POLYGON))
        )
        self.assertTrue(np.all(first.magnitudes >= 2.5))

    def test_temporal_inverse_samples_stay_within_each_parent_window(self):
        simulator = self._simulator(self._catalog())
        lower = np.array([0.0, 0.25, 4.0])
        upper = np.array([0.1, 1.0, 10.0])
        samples = simulator._sample_temporal(lower, upper, np.random.default_rng(3))
        self.assertTrue(np.all(samples >= lower))
        self.assertTrue(np.all(samples <= upper))

    def test_destination_distance_uses_configured_sphere(self):
        lat, lon = destination_points(
            np.array([34.0]), np.array([-118.0]), np.array([100.0]),
            np.array([0.0]), 6_378.1,
        )
        self.assertGreater(lat[0], 34.0)
        self.assertAlmostEqual(lon[0], -118.0, places=12)

    @staticmethod
    def _catalog(magnitude_at_issue=2.5):
        return DailyCatalog(
            times=np.array([0.0, 1.0, 1.5]),
            latitudes=np.array([0.5, 0.5, 0.5]),
            longitudes=np.array([0.5, 0.5, 0.5]),
            magnitudes=np.array([3.0, magnitude_at_issue, 3.0]),
        )

    @staticmethod
    def _simulator(catalog):
        return ETASContinuationSimulator(
            catalog=catalog,
            polygon_lat_lon=POLYGON,
            area=10.0,
            m_ref=2.5,
            beta=2.0,
            parameters=PARAMETERS,
        )


if __name__ == "__main__":
    unittest.main()
