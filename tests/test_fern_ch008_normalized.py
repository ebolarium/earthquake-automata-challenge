import unittest

import numpy as np

from etas_challenge.fern_ch008_normalized import prevalidation_exposure_scale


class FernCh008NormalizedTest(unittest.TestCase):
    def test_scale_targets_one_mean_training_exposure(self):
        background = np.array([0.01, 0.02, 0.03])
        scale = prevalidation_exposure_scale(background, 100.0)
        self.assertAlmostEqual(np.mean(scale * background * 100.0), 1.0)

    def test_scale_rejects_invalid_background(self):
        with self.assertRaises(ValueError):
            prevalidation_exposure_scale(np.array([0.0, 1.0]), 100.0)


if __name__ == "__main__":
    unittest.main()
