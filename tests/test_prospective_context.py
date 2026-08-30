from pathlib import Path
import unittest

import numpy as np

from etas_challenge.prospective_context import load_california_runtime_context


class ProspectiveContextTest(unittest.TestCase):
    def test_locked_california_context_matches_seed_shape(self):
        root = Path(__file__).resolve().parents[1]
        context = load_california_runtime_context(root)
        self.assertEqual(context.expected_section_background.shape, (8, 350))
        self.assertEqual(context.baseline_background_grid.shape, (7682,))
        self.assertEqual(len(context.grid_geometries), 8)
        self.assertTrue(np.all(context.expected_section_background >= 0))
        self.assertAlmostEqual(
            float(np.sum(context.state_background_grid)),
            float(np.sum(context.baseline_background_grid)),
            places=6,
        )

    def test_event_geometry_is_branch_complete(self):
        root = Path(__file__).resolve().parents[1]
        context = load_california_runtime_context(root)
        geometries = context.event_geometries(
            np.array([34.05]), np.array([-118.25])
        )
        self.assertEqual(len(geometries), 8)
        self.assertTrue(all(item.section_indexes.shape == (1, 4) for item in geometries))


if __name__ == "__main__":
    unittest.main()
