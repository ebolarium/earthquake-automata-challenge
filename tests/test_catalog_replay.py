import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.likelihood import CatalogEvent, likelihood_components
from etas_challenge.parameters import ETASParameters
from etas_challenge.replay import CatalogReplay, ReplayCatalog


class CatalogReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_path = ROOT / "tests" / "fixtures" / "native-alignment-001.json"
        cls.fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        transformed = cls.fixture["parameters"].copy()
        transformed.pop("log10_iota")
        cls.parameters = ETASParameters.from_transformed(**transformed)
        cls.events = [
            CatalogEvent(
                event_id=event["id"],
                time=event["time"],
                latitude=event["latitude"],
                longitude=event["longitude"],
                magnitude=event["magnitude"],
            )
            for event in cls.fixture["events"]
        ]

    def test_vectorized_replay_matches_scalar_native_likelihood(self):
        catalog = ReplayCatalog(
            times=[event.time for event in self.events],
            latitudes=[event.latitude for event in self.events],
            longitudes=[event.longitude for event in self.events],
            magnitudes=[event.magnitude for event in self.events],
        )
        target_indexes = np.array(
            [
                index
                for index, event in enumerate(self.fixture["events"])
                if event["role"] == "target"
            ]
        )
        replay = CatalogReplay(
            catalog=catalog,
            target_indexes=target_indexes,
            window_start=self.fixture["window_start"],
            area=self.fixture["area"],
            m_ref=self.fixture["m_ref"],
            parameters=self.parameters,
            earth_radius=self.fixture["earth_radius"],
        )

        interval_start = self.fixture["window_start"]
        for position, target_index in enumerate(target_indexes):
            target = self.events[target_index]
            scalar = likelihood_components(
                target=target,
                interval_start=interval_start,
                history=self.events[:target_index],
                area=self.fixture["area"],
                m_ref=self.fixture["m_ref"],
                parameters=self.parameters,
                earth_radius=self.fixture["earth_radius"],
            )
            vectorized = replay.evaluate_target(position)
            self.assertAlmostEqual(
                vectorized.point_intensity, scalar.point_intensity, delta=1e-14
            )
            self.assertAlmostEqual(
                vectorized.temporal_intensity,
                scalar.temporal_intensity,
                delta=1e-14,
            )
            self.assertAlmostEqual(
                vectorized.corrected_compensator,
                scalar.compensator,
                delta=1e-13,
            )
            if position == 0:
                expected_background = (
                    self.parameters.mu
                    * self.fixture["area"]
                    * (target.time - interval_start)
                )
                self.assertAlmostEqual(
                    vectorized.strict_reference_compensator,
                    expected_background,
                    delta=1e-15,
                )
            else:
                self.assertEqual(
                    vectorized.strict_reference_compensator,
                    vectorized.corrected_compensator,
                )
            interval_start = target.time

    def test_catalog_rejects_non_increasing_times(self):
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            ReplayCatalog(
                times=[1.0, 1.0],
                latitudes=[34.0, 34.1],
                longitudes=[-118.0, -118.1],
                magnitudes=[3.0, 3.1],
            )

    def test_catalog_preserves_nanosecond_event_order(self):
        catalog = ReplayCatalog(
            times=np.array(
                [
                    "2019-07-06T13:45:19.050000265",
                    "2019-07-06T13:45:19.050000324",
                ],
                dtype="datetime64[ns]",
            ),
            latitudes=[35.0, 35.0],
            longitudes=[-117.0, -117.0],
            magnitudes=[3.0, 3.1],
        )
        self.assertEqual(catalog.times.dtype, np.dtype("datetime64[ns]"))
        self.assertEqual(
            catalog.times[1] - catalog.times[0], np.timedelta64(59, "ns")
        )


if __name__ == "__main__":
    unittest.main()
