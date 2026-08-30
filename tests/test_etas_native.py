import unittest

import numpy as np

from etas_challenge.etas_native import event_rates


class NativeEtasTest(unittest.TestCase):
    def test_rate_uses_only_prior_events(self):
        parameters = {
            "log10_mu": -2.0, "log10_k0": -1.0, "a": 1.0,
            "log10_c": -1.0, "omega": 0.0, "log10_tau": 3.0,
            "log10_d": 0.0, "gamma": 0.0, "rho": 1.0,
        }
        rates = event_rates(
            np.array([0.0, 1.0]), np.array([40.0, 40.0]), np.array([140.0, 140.0]),
            np.array([5.0, 5.0]), magnitude_reference=5.0, parameters=parameters,
        )
        self.assertEqual(rates[0], 0.01)
        self.assertGreater(rates[1], rates[0])


if __name__ == "__main__":
    unittest.main()
