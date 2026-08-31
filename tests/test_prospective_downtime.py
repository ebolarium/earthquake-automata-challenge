from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from etas_challenge.prospective_downtime import evaluate_invalidation
from etas_challenge.prospective_downtime import invalidation_threshold
from etas_challenge.prospective_downtime import publication_missed_dates
from etas_challenge.prospective_downtime import run_with_retries
from etas_challenge.prospective_downtime import validate_downtime_policy


class Clock:
    def __init__(self, value):
        self.value = value

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += timedelta(seconds=seconds)


class ProspectiveDowntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.policy = validate_downtime_policy(
            root / "configs/challenge/ch008-downtime-policy.json"
        )

    def test_retry_that_would_cross_deadline_is_not_attempted(self):
        start = datetime(2026, 9, 1, 0, 5, tzinfo=timezone.utc)
        clock = Clock(start)
        calls = []

        def fail():
            calls.append(clock.now())
            raise OSError("temporary outage")

        result = run_with_retries(
            fail,
            max_attempts=3,
            backoff_seconds=[60, 300],
            deadline=start + timedelta(minutes=3),
            now=clock.now,
            sleep=clock.sleep,
        )
        self.assertFalse(result.succeeded)
        self.assertTrue(result.deadline_blocked)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(len(calls), 2)

    def test_agreed_threshold_drift_is_rejected(self):
        changed = json.loads(json.dumps(self.policy))
        changed["region_invalidation"]["threshold_pct"] = 0.10
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as stream:
            json.dump(changed, stream)
            path = Path(stream.name)
        self.addCleanup(path.unlink)
        with self.assertRaisesRegex(ValueError, "invalidation contract changed"):
            validate_downtime_policy(path)

    def test_deferred_scoring_does_not_enter_missed_day_counter(self):
        records = [
            {"issue_date": date(2026, 9, 1), "publication_status": "missed"},
            {
                "issue_date": date(2026, 9, 2),
                "publication_status": "published",
                "scoring_status": "deferred",
            },
        ]
        result = evaluate_invalidation(publication_missed_dates(records), self.policy)
        self.assertEqual(result.missed_days, 1)
        self.assertFalse(result.invalid)

    def test_nineteenth_missed_day_invalidates_region(self):
        start = date(2026, 9, 1)
        missed = [start + timedelta(days=index * 2) for index in range(19)]
        self.assertEqual(invalidation_threshold(self.policy), 19)
        self.assertFalse(evaluate_invalidation(missed[:18], self.policy).invalid)
        result = evaluate_invalidation(missed, self.policy)
        self.assertTrue(result.invalid)
        self.assertEqual(result.reason, "missed_region_days_reached_19")

    def test_seven_consecutive_missed_days_invalidates_region(self):
        start = date(2026, 9, 1)
        missed = [start + timedelta(days=index) for index in range(7)]
        result = evaluate_invalidation(missed, self.policy)
        self.assertTrue(result.invalid)
        self.assertEqual(result.reason, "consecutive_missed_days_reached_7")


if __name__ == "__main__":
    unittest.main()
