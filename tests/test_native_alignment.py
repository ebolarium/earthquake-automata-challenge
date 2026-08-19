import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
ALIGNMENT_TOLERANCE = 1e-12

from etas_challenge.likelihood import CatalogEvent, likelihood_components
from etas_challenge.parameters import ETASParameters


class NativeAlignmentTests(unittest.TestCase):
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

    def test_native_components_align_with_synthetic_reference_oracle(self):
        history = [
            event
            for event, payload in zip(self.events, self.fixture["events"])
            if payload["role"] == "history"
        ]
        targets = [
            event
            for event, payload in zip(self.events, self.fixture["events"])
            if payload["role"] == "target"
        ]
        interval_start = self.fixture["window_start"]

        for index, (target, expected) in enumerate(
            zip(targets, self.fixture["targets"])
        ):
            with self.subTest(target=target.event_id):
                actual = likelihood_components(
                    target=target,
                    interval_start=interval_start,
                    history=history,
                    area=self.fixture["area"],
                    m_ref=self.fixture["m_ref"],
                    parameters=self.parameters,
                    earth_radius=self.fixture["earth_radius"],
                )
                self.assertEqual(target.event_id, expected["id"])
                self.assertAlmostEqual(
                    actual.point_intensity,
                    expected["point_intensity"],
                    delta=ALIGNMENT_TOLERANCE,
                )
                self.assertAlmostEqual(
                    actual.temporal_intensity,
                    expected["temporal_intensity"],
                    delta=ALIGNMENT_TOLERANCE,
                )
                self.assertAlmostEqual(
                    actual.compensator,
                    expected["published_compensator"],
                    delta=ALIGNMENT_TOLERANCE,
                )
                self.assertAlmostEqual(
                    actual.sll,
                    expected["reference_sll"],
                    delta=ALIGNMENT_TOLERANCE,
                )

                if index == 0:
                    self.assertGreater(
                        abs(actual.compensator - expected["reference_compensator"]),
                        0.1,
                    )
                    self.assertNotAlmostEqual(
                        actual.ll, expected["reference_ll"], places=6
                    )
                else:
                    self.assertAlmostEqual(
                        actual.compensator,
                        expected["reference_compensator"],
                        delta=ALIGNMENT_TOLERANCE,
                    )
                    self.assertAlmostEqual(
                        actual.ll,
                        expected["reference_ll"],
                        delta=ALIGNMENT_TOLERANCE,
                    )
                    self.assertAlmostEqual(
                        actual.tll,
                        expected["reference_tll"],
                        delta=ALIGNMENT_TOLERANCE,
                    )

            history.append(target)
            interval_start = target.time

    def test_fixture_records_the_known_first_interval_behavior(self):
        behavior = self.fixture["known_reference_behavior"]
        self.assertTrue(behavior["first_interval_triggered_compensator_omitted"])


if __name__ == "__main__":
    unittest.main()
