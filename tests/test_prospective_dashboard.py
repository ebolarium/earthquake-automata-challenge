from datetime import date, datetime, timedelta, timezone
import unittest

from etas_challenge.prospective_dashboard import _dry_run_progress, build_dashboard


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, responses):
        self.responses = iter(responses)

    def execute(self, query, parameters):
        return Result(next(self.responses))


class ProspectiveDashboardTest(unittest.TestCase):
    def test_projection_summarizes_regions_runs_and_scores(self):
        target = datetime(2026, 9, 1, tzinfo=timezone.utc)
        config = {
            "mode": "dry_run",
            "counts_toward_prospective_claim": False,
            "catalog_revision_contract": {"settled_score_delay_days": 7},
        }
        regions = [
            ("california-relm", "California RELM", "USGS", 2.5, None, None),
            ("new-zealand-csep", "New Zealand CSEP", "GeoNet", 4.0, 0.0, 40.0),
            ("chile-subduction", "Chile", "USGS", 4.5, 0.0, 100.0),
        ]
        runs = [
            (region[0], f"run-{index}", target, target, target, "published", target, f"state-{index}", 6)
            for index, region in enumerate(regions)
        ]
        catalogs = [
            (region[0], target, 10 + index, str(index) * 64)
            for index, region in enumerate(regions, start=1)
        ]
        scores = [
            ("california-relm", date(2026, 9, 1), "provisional", 2, 0.2, 0.1, target),
            ("new-zealand-csep", date(2026, 9, 1), "provisional", 0, 0.0, None, target),
        ]
        connection = Connection([
            [("draft", config, 14, 1)], regions, runs, catalogs, scores, [(0, None)], [],
        ])
        result = build_dashboard(connection, "protocol", now=target)
        self.assertEqual(result["pipeline_status"], "ok")
        self.assertTrue(result["forecast_current"])
        self.assertEqual(result["published_regions"], 3)
        self.assertEqual(result["provisional"]["events"], 2)
        self.assertAlmostEqual(result["provisional"]["mean_igpe"], 0.1)
        self.assertEqual(result["regions"][0]["latest_forecast"]["artifacts"], 6)
        self.assertEqual(result["provisional"]["days"], 1)
        self.assertEqual(result["dry_run"]["phase"], "awaiting_scores")

    def test_open_incident_marks_pipeline_attention(self):
        config = {
            "mode": "dry_run",
            "counts_toward_prospective_claim": False,
            "catalog_revision_contract": {"settled_score_delay_days": 7},
        }
        connection = Connection([
            [("draft", config, 14, 1)], [], [], [], [],
            [(1, datetime(2026, 9, 1, tzinfo=timezone.utc))], [],
        ])
        result = build_dashboard(connection, "protocol")
        self.assertEqual(result["pipeline_status"], "attention")
        self.assertEqual(result["open_incidents"], 1)

    def test_invalid_region_makes_pooled_claim_inconclusive(self):
        config = {
            "mode": "dry_run",
            "counts_toward_prospective_claim": False,
            "catalog_revision_contract": {"settled_score_delay_days": 7},
        }
        target = datetime(2026, 9, 1, tzinfo=timezone.utc)
        regions = [("california-relm", "California", "USGS", 2.5, None, None)]
        runs = [("california-relm", "run", target, target, target, "published", target, "state", 6)]
        operations = [("california-relm", False, 19, 3, target, "missed_region_days_reached_19")]
        connection = Connection([
            [("active", config, 365, 500)], regions, runs, [], [], [(0, None)], operations,
        ])
        result = build_dashboard(connection, "protocol", now=target)
        self.assertEqual(result["pipeline_status"], "attention")
        self.assertEqual(result["pooled_primary_claim_status"], "inconclusive")
        self.assertFalse(result["regions"][0]["operations"]["primary_eligible"])

    def test_forecast_is_stale_after_publication_deadline(self):
        config = {
            "mode": "dry_run",
            "counts_toward_prospective_claim": False,
            "catalog_revision_contract": {"settled_score_delay_days": 7},
        }
        target = datetime(2026, 9, 1, tzinfo=timezone.utc)
        generated = datetime(2026, 9, 2, 8, tzinfo=timezone.utc)
        regions = [("california-relm", "California", "USGS", 2.5, None, None)]
        runs = [("california-relm", "run", target, target, target + timedelta(days=1), "published", target, "state", 6)]
        connection = Connection([
            [("active", config, 365, 500)], regions, runs, [], [], [(0, None)], [],
        ])
        result = build_dashboard(connection, "protocol", now=generated)
        self.assertFalse(result["forecast_current"])
        self.assertEqual(result["pipeline_status"], "attention")

    def test_dry_run_progress_requires_every_region_and_final_settlement(self):
        regions = ["california", "new-zealand", "chile"]
        provisional = [
            {
                "region_id": region,
                "target_date": f"2026-09-{day:02d}",
                "revision": "provisional",
            }
            for day in range(1, 15)
            for region in regions
        ]
        incomplete_final = [
            {
                "region_id": region,
                "target_date": f"2026-09-{day:02d}",
                "revision": "final",
            }
            for day in range(1, 8)
            for region in regions
        ]
        settling = _dry_run_progress(provisional + incomplete_final, regions, 14)
        self.assertEqual(settling["phase"], "settling")
        self.assertEqual(settling["provisional_days"], 14)
        self.assertEqual(settling["final_days"], 7)

        remaining_final = [
            {
                "region_id": region,
                "target_date": f"2026-09-{day:02d}",
                "revision": "final",
            }
            for day in range(8, 15)
            for region in regions
        ]
        complete = _dry_run_progress(
            provisional + incomplete_final + remaining_final, regions, 14
        )
        self.assertEqual(complete["phase"], "complete")
        self.assertEqual(complete["final_days"], 14)


if __name__ == "__main__":
    unittest.main()
