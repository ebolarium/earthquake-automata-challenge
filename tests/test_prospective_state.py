from datetime import datetime, timezone
import unittest

import numpy as np

from etas_challenge.prospective_state import BootstrapCatalog
from etas_challenge.prospective_state import catalog_history_sha256
from etas_challenge.prospective_state import model_state_id


class ProspectiveStateTest(unittest.TestCase):
    def test_state_identity_is_stable_and_boundary_sensitive(self):
        as_of = datetime(2026, 8, 19, tzinfo=timezone.utc)
        cutoff = datetime(2026, 8, 30, tzinfo=timezone.utc)
        first = model_state_id(
            "protocol", "region", as_of, cutoff, "c" * 64, "a" * 64, "b" * 64
        )
        second = model_state_id(
            "protocol", "region", as_of, cutoff, "c" * 64, "a" * 64, "b" * 64
        )
        changed = model_state_id(
            "protocol", "region", datetime(2026, 8, 20, tzinfo=timezone.utc),
            cutoff, "c" * 64, "a" * 64, "b" * 64,
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(len(first), 64)

    def test_catalog_identity_is_stable_and_event_sensitive(self):
        catalog = BootstrapCatalog(
            (1,),
            np.array(["event-a", "event-b"]),
            np.array([1, 2], dtype=np.int64),
            np.array([1.0, 2.0]),
            np.array([3.0, 4.0]),
            np.array([5.0, 6.0]),
            np.array([2.5, 3.0]),
        )
        first = catalog_history_sha256(catalog)
        same_events_other_snapshot = BootstrapCatalog(
            (99,), catalog.event_ids, catalog.origin_time_ns, catalog.latitudes,
            catalog.longitudes, catalog.depths_km, catalog.magnitudes,
        )
        self.assertEqual(first, catalog_history_sha256(same_events_other_snapshot))
        changed = BootstrapCatalog(
            (1,), catalog.event_ids, catalog.origin_time_ns, catalog.latitudes,
            catalog.longitudes, catalog.depths_km, np.array([2.5, 3.1]),
        )
        self.assertNotEqual(first, catalog_history_sha256(changed))


if __name__ == "__main__":
    unittest.main()
