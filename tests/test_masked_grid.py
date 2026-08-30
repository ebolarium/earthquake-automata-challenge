import unittest

import numpy as np

from etas_challenge.masked_grid import masked_grid


class MaskedGridTest(unittest.TestCase):
    def test_mask_membership_aggregation_and_transition(self):
        origins = np.array([[170.0, -40.0], [170.1, -40.0], [170.5, -40.0]])
        grid = masked_grid(origins, 0.1, 0.5)
        np.testing.assert_array_equal(
            grid.cells(np.array([-39.95, -39.95, -39.95]), np.array([170.05, 170.55, 171.0])),
            [0, 1, -1],
        )
        self.assertEqual(len(grid.areas_km2), 2)
        np.testing.assert_allclose(np.asarray(grid.transition.sum(axis=1)).ravel(), 1.0)


if __name__ == "__main__":
    unittest.main()
