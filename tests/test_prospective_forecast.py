from datetime import datetime, timezone
import io
import unittest

import numpy as np
from scipy.sparse import identity

from etas_challenge.prospective_forecast import build_regional_artifacts
from etas_challenge.prospective_forecast import deterministic_npz_bytes
from etas_challenge.prospective_forecast import enforce_publication_deadline
from etas_challenge.prospective_forecast import forecast_run_id
from etas_challenge.prospective_replay import CH008State
from scripts.advance_prospective_daily_states import append_completed_day
from scripts.advance_prospective_daily_states import parse_args as parse_advance_args


PARENT = {
    "parameters": {
        "full_reset_magnitude": 4.0,
        "magnitude_exponent": 0.4,
        "bpt_aperiodicity": 1.0,
        "graph_neighborhood_mix": 0.5,
        "minimum_branch_consensus": 0.5,
        "background_mixture_fraction": 0.05,
        "renewal_sensitivity": 1.0,
    }
}
CH008 = {
    "parameters": {
        "prior_exposure": 0.5,
        "memory_half_life_days": 100.0,
        "frailty_neighborhood_mix": 0.0,
        "minimum_log_frailty": 0.0,
        "frailty_weight": 1.0,
        "renewal_weight": 1.0,
        "background_mixture_fraction": 0.25,
    }
}


class Grid:
    areas_km2 = np.array([10.0, 20.0])
    transition = identity(2, format="csr")
    longitude_edges = np.array([0.0, 1.0, 2.0])
    latitude_edges = np.array([0.0, 1.0])


class RollingConnection:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, query, parameters):
        class Result:
            def __init__(self, one=None, rows=None):
                self.one = one
                self.rows = rows or []

            def fetchone(self):
                return self.one

            def fetchall(self):
                return self.rows

        if "SELECT snapshot_id" in query:
            return Result(one=(12,))
        return Result(rows=self.rows)


class ProspectiveForecastTest(unittest.TestCase):
    def test_daily_advance_accepts_fixed_cutoff(self):
        from unittest.mock import patch

        with patch(
            "sys.argv",
            ["advance", "--cutoff", "2026-09-01T00:05:00Z", "--region", "region"],
        ):
            args = parse_advance_args()
        self.assertEqual(args.cutoff.isoformat(), "2026-09-01T00:05:00+00:00")
        self.assertEqual(args.regions, ["region"])

    def test_deadline_contract_targets_the_next_utc_day(self):
        boundary = datetime(2026, 8, 31, tzinfo=timezone.utc)
        target_start, target_end = enforce_publication_deadline(
            datetime(2026, 8, 31, 0, 15, tzinfo=timezone.utc),
            boundary,
            deadline_minutes=15,
            minimum_lead_time_minutes=1425,
        )
        self.assertEqual(target_start.isoformat(), "2026-09-01T00:00:00+00:00")
        self.assertEqual(target_end.isoformat(), "2026-09-02T00:00:00+00:00")
        with self.assertRaisesRegex(ValueError, "deadline"):
            enforce_publication_deadline(
                datetime(2026, 8, 31, 0, 15, 1, tzinfo=timezone.utc),
                boundary,
                deadline_minutes=15,
                minimum_lead_time_minutes=1425,
            )

    def test_run_identity_is_target_stable(self):
        target = datetime(2026, 9, 1, tzinfo=timezone.utc)
        first = forecast_run_id("protocol", "region", target)
        second = forecast_run_id("protocol", "region", target)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_regional_artifacts_are_deterministic_and_mass_preserving(self):
        state = CH008State(
            np.array([2.0, 0.1]),
            np.array([1.0, 2.0]),
            np.array([4.0, 1.0]),
        )
        buffer = io.BytesIO()
        np.savez(
            buffer,
            ch008_age=state.age,
            ch008_exposure=state.exposure,
            ch008_roots=state.roots,
        )
        buffer.seek(0)
        with np.load(buffer, allow_pickle=False) as source:
            pair = build_regional_artifacts(
                source,
                grid=Grid(),
                etas_model={"parameters": {"log10_mu": -2.0}},
                parent_model=PARENT,
                ch008_model=CH008,
            )
        self.assertAlmostEqual(
            float(np.sum(pair.baseline_arrays["direct_background_mass"])),
            float(np.sum(pair.challenger_arrays["direct_background_mass"])),
        )
        first = deterministic_npz_bytes(pair.challenger_arrays)
        second = deterministic_npz_bytes(pair.challenger_arrays)
        self.assertEqual(first, second)

    def test_daily_catalog_appends_only_the_completed_window(self):
        previous = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
        source = {
            "event_ids": np.array(["old"]),
            "origin_time_ns": np.array([int(previous.timestamp() * 1e9)], dtype=np.int64),
            "latitudes": np.array([1.0]),
            "longitudes": np.array([2.0]),
            "depths_km": np.array([3.0]),
            "magnitudes": np.array([4.0]),
        }
        event_time = datetime(2026, 8, 30, 18, tzinfo=timezone.utc)
        connection = RollingConnection(
            [("new", event_time, 5.0, 6.0, 7.0, 4.5)]
        )
        catalog, snapshot_id = append_completed_day(
            connection,
            source,
            "region",
            datetime(2026, 8, 30, tzinfo=timezone.utc),
            datetime(2026, 8, 31, tzinfo=timezone.utc),
            datetime(2026, 8, 31, 0, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(snapshot_id, 12)
        self.assertEqual(catalog.event_ids.tolist(), ["old", "new"])
        self.assertEqual(catalog.magnitudes.tolist(), [4.0, 4.5])


if __name__ == "__main__":
    unittest.main()
