from datetime import datetime, timezone
import hashlib
import io
import unittest

import numpy as np

from etas_challenge.prospective_map import _forecast_cells, load_latest_forecast_map


def archive(**arrays):
    target = io.BytesIO()
    np.savez_compressed(target, **arrays)
    return target.getvalue()


class Body:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload


class Storage:
    bucket = "test"


class Client:
    def __init__(self, payloads):
        self.payloads = payloads

    def get_object(self, *, Bucket, Key):
        return {"Body": Body(self.payloads[Key])}


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


class ProspectiveMapTest(unittest.TestCase):
    def test_projects_regular_grid_and_log_ratio(self):
        baseline = archive(
            longitude_edges=np.array([-76.0, -75.5, -75.0]),
            latitude_edges=np.array([-20.0, -19.5]),
            direct_background_mass=np.array([1.0, 2.0]),
        )
        challenger = archive(
            longitude_edges=np.array([-76.0, -75.5, -75.0]),
            latitude_edges=np.array([-20.0, -19.5]),
            direct_background_mass=np.array([2.0, 1.0]),
        )
        result = _forecast_cells(baseline, challenger)
        self.assertEqual(result["origins"], [[-76.0, -20.0], [-75.5, -20.0]])
        self.assertAlmostEqual(result["layers"]["log_ratio"][0], np.log(2.0))
        self.assertAlmostEqual(result["layers"]["log_ratio"][1], -np.log(2.0))
        self.assertEqual(result["summary"]["etas_total"], 3.0)
        self.assertEqual(result["summary"]["ch008_total"], 3.0)

    def test_reads_only_configured_models_and_verifies_objects(self):
        baseline = archive(
            origin_units=np.array([[-1254, 401], [-1253, 401]]),
            coordinate_units_per_degree=np.array(10),
            daily_rates=np.array([0.1, 0.2]),
        )
        challenger = archive(
            origin_units=np.array([[-1254, 401], [-1253, 401]]),
            coordinate_units_per_degree=np.array(10),
            daily_rates=np.array([0.12, 0.18]),
        )
        now = datetime(2026, 9, 3, tzinfo=timezone.utc)
        config = {"regions": [{
            "region_id": "california-relm",
            "name": "California RELM",
            "baseline_model_id": "etas",
            "challenger_model_id": "ch008",
        }]}
        rows = [
            ("etas", "baseline", hashlib.sha256(baseline).hexdigest(), len(baseline)),
            ("ch008", "challenger", hashlib.sha256(challenger).hexdigest(), len(challenger)),
        ]
        connection = Connection([
            [(config,)], [("run", now, now, now, now)], rows,
        ])
        result = load_latest_forecast_map(
            connection,
            Client({"baseline": baseline, "challenger": challenger}),
            Storage(),
            "protocol",
            "california-relm",
        )
        self.assertEqual(result["region_id"], "california-relm")
        self.assertEqual(result["origins"][0], [-125.4, 40.1])
        self.assertEqual(result["summary"]["cells"], 2)

    def test_rejects_object_checksum_mismatch(self):
        payload = archive(
            latent_keys=np.array([[330, -90]]),
            direct_background_mass=np.array([1.0]),
        )
        now = datetime(2026, 9, 3, tzinfo=timezone.utc)
        config = {"regions": [{
            "region_id": "new-zealand-csep", "name": "New Zealand",
            "baseline_model_id": "etas", "challenger_model_id": "ch008",
        }]}
        rows = [
            ("etas", "baseline", "0" * 64, len(payload)),
            ("ch008", "challenger", hashlib.sha256(payload).hexdigest(), len(payload)),
        ]
        connection = Connection([[(config,)], [("run", now, now, now, now)], rows])
        with self.assertRaisesRegex(RuntimeError, "checksum"):
            load_latest_forecast_map(
                connection, Client({"baseline": payload, "challenger": payload}),
                Storage(), "protocol", "new-zealand-csep",
            )


if __name__ == "__main__":
    unittest.main()
