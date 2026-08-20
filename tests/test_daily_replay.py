import json
import math
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
COMMITTED_MANIFEST = ROOT / "data" / "manifests" / "daily-replay-v1.json"

from etas_challenge.daily_replay import (
    DailyCatalog,
    DailyETASReplay,
    validate_daily_replay_manifest,
)
from etas_challenge.kernels import (
    productivity,
    spatial_integral_disk,
    temporal_integral,
)
from etas_challenge.likelihood import CatalogEvent, point_intensity
from etas_challenge.parameters import ETASParameters


PARAMETERS = ETASParameters(
    mu=1e-5,
    k0=2e-3,
    a=1.1,
    c=0.01,
    omega=0.0,
    tau=100.0,
    d=0.2,
    gamma=0.8,
    rho=0.6,
)
AREA = 1_000.0
M_REF = 2.5


class DailyReplayTests(unittest.TestCase):
    def test_committed_daily_replay_manifest_is_valid(self):
        manifest = json.loads(COMMITTED_MANIFEST.read_text(encoding="utf-8"))
        validate_daily_replay_manifest(manifest)
        self.assertEqual(manifest["results"]["replay_days"], 7_170)
        self.assertEqual(manifest["results"]["target_events"], 24_498)

    def test_daily_boundaries_ties_and_compensators(self):
        catalog = self._catalog()
        replay = self._replay(catalog)
        score = replay.evaluate_day(1.0)

        self.assertEqual(score.history_event_count, 1)
        self.assertEqual(score.target_event_count, 3)

        source_weight = (
            productivity(3.0, M_REF, PARAMETERS)
            * spatial_integral_disk(math.inf, 3.0, M_REF, PARAMETERS)
        )
        expected_frozen_integrated = (
            PARAMETERS.mu * AREA
            + source_weight * temporal_integral(0.5, 1.5, PARAMETERS)
        )
        self.assertAlmostEqual(
            score.frozen_integrated_rate, expected_frozen_integrated, places=13
        )

        events = self._events(catalog)
        frozen_intensities = [
            point_intensity(target, events[:1], M_REF, PARAMETERS)
            for target in events[1:4]
        ]
        self.assertAlmostEqual(
            score.frozen_log_intensity_sum,
            sum(math.log(value) for value in frozen_intensities),
            places=13,
        )

        sequential_histories = [events[:1], events[:2], events[:2]]
        sequential_intensities = [
            point_intensity(target, history, M_REF, PARAMETERS)
            for target, history in zip(events[1:4], sequential_histories)
        ]
        self.assertAlmostEqual(
            score.sequential_log_intensity_sum,
            sum(math.log(value) for value in sequential_intensities),
            places=13,
        )
        self.assertGreater(
            score.sequential_integrated_rate, score.frozen_integrated_rate
        )
        self.assertGreater(sequential_intensities[1], frozen_intensities[1])
        self.assertEqual(sequential_intensities[1], sequential_intensities[2])

    def test_events_at_or_after_window_end_cannot_change_score(self):
        original = self._catalog()
        mutated = DailyCatalog(
            times=original.times,
            latitudes=np.array([34.0, 34.0, 34.0, 34.0, -80.0, 80.0]),
            longitudes=np.array([-118.0, -118.0, -118.0, -118.0, 170.0, -170.0]),
            magnitudes=np.array([3.0, 3.2, 2.8, 2.8, 9.0, 9.0]),
        )
        original_score = asdict(self._replay(original).evaluate_day(1.0))
        mutated_score = asdict(self._replay(mutated).evaluate_day(1.0))
        self.assertEqual(original_score, mutated_score)

    def test_datetime_issue_boundary_is_exclusive(self):
        catalog = DailyCatalog(
            times=np.array(
                [
                    "2020-01-01T23:59:59.999999999",
                    "2020-01-02T00:00:00.000000000",
                    "2020-01-03T00:00:00.000000000",
                ],
                dtype="datetime64[ns]",
            ),
            latitudes=[34.0, 34.0, 34.0],
            longitudes=[-118.0, -118.0, -118.0],
            magnitudes=[3.0, 3.0, 3.0],
        )
        score = self._replay(catalog).evaluate_day(
            np.datetime64("2020-01-02T00:00:00", "ns")
        )
        self.assertEqual(score.history_event_count, 1)
        self.assertEqual(score.target_event_count, 1)

    def test_catalog_rejects_decreasing_time(self):
        with self.assertRaisesRegex(ValueError, "non-decreasing"):
            DailyCatalog(
                times=[2.0, 1.0],
                latitudes=[34.0, 34.0],
                longitudes=[-118.0, -118.0],
                magnitudes=[3.0, 3.0],
            )

    @staticmethod
    def _catalog():
        return DailyCatalog(
            times=np.array([0.5, 1.0, 1.25, 1.25, 2.0, 2.5]),
            latitudes=np.full(6, 34.0),
            longitudes=np.full(6, -118.0),
            magnitudes=np.array([3.0, 3.2, 2.8, 2.8, 3.5, 4.0]),
        )

    @staticmethod
    def _replay(catalog):
        return DailyETASReplay(
            catalog=catalog,
            area=AREA,
            m_ref=M_REF,
            parameters=PARAMETERS,
            poisson_mu=2e-5,
        )

    @staticmethod
    def _events(catalog):
        return [
            CatalogEvent(
                event_id=str(index),
                time=float(catalog.times[index]),
                latitude=float(catalog.latitudes[index]),
                longitude=float(catalog.longitudes[index]),
                magnitude=float(catalog.magnitudes[index]),
            )
            for index in range(len(catalog.times))
        ]


if __name__ == "__main__":
    unittest.main()
