import json
import unittest
from pathlib import Path

import numpy as np

from scripts.fit_ch006_frailty_renewal import transformed_candidates


ROOT = Path(__file__).resolve().parents[1]


class BoundarySensitivityTest(unittest.TestCase):
    def test_only_requested_bounds_change_and_unit_points_match(self):
        original = json.loads(
            (ROOT / "configs/challenge/ch006-frailty-renewal-fit-v1.json").read_text()
        )
        sensitivity = json.loads(
            (ROOT / "configs/challenge/ch008-boundary-sensitivity-fit-v1.json").read_text()
        )
        for key in ("seed", "sobol_power", "sobol_candidates"):
            self.assertEqual(
                original["candidate_protocol"][key],
                sensitivity["candidate_protocol"][key],
            )
        self.assertEqual(original["parameter_order"], sensitivity["parameter_order"])
        self.assertEqual(original["parameter_scales"], sensitivity["parameter_scales"])
        np.testing.assert_array_equal(
            np.asarray(original["parameter_bounds"])[:5],
            np.asarray(sensitivity["parameter_bounds"])[:5],
        )
        self.assertEqual(sensitivity["parameter_bounds"][5], [0.25, 4.0])
        self.assertEqual(sensitivity["parameter_bounds"][6], [0.02, 0.5])

        original_candidates = transformed_candidates(original)
        sensitivity_candidates = transformed_candidates(sensitivity)
        np.testing.assert_array_equal(original_candidates[:, :5], sensitivity_candidates[:, :5])
        for column in (5, 6):
            original_low, original_high = original["parameter_bounds"][column]
            sensitivity_low, sensitivity_high = sensitivity["parameter_bounds"][column]
            original_unit = (
                original_candidates[1:, column] - original_low
            ) / (original_high - original_low)
            sensitivity_unit = (
                sensitivity_candidates[1:, column] - sensitivity_low
            ) / (sensitivity_high - sensitivity_low)
            np.testing.assert_allclose(original_unit, sensitivity_unit)


if __name__ == "__main__":
    unittest.main()
