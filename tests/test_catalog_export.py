import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
COMMITTED_MANIFEST = ROOT / "data" / "manifests" / "local-california-catalog-v1.json"

from etas_challenge.catalog_export import (
    export_catalog,
    point_intersects_polygon,
    sha256_file,
    validate_export_manifest,
)


POLYGON = np.array([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0], [0.0, 0.0]])


class CatalogExportTests(unittest.TestCase):
    def test_committed_export_manifest_is_valid(self):
        manifest = json.loads(COMMITTED_MANIFEST.read_text(encoding="utf-8"))
        validate_export_manifest(manifest)
        self.assertEqual(manifest["selection"]["included_rows"], 80_140)

    def test_polygon_includes_boundary_and_excludes_outer_bbox(self):
        self.assertTrue(point_intersects_polygon(0.5, 0.5, POLYGON))
        self.assertTrue(point_intersects_polygon(1.0, 1.0, POLYGON))
        self.assertFalse(point_intersects_polygon(1.5, 1.5, POLYGON))

    def test_export_is_filtered_provenance_aware_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.db"
            shape = root / "shape.npy"
            np.save(shape, POLYGON)
            self._create_source(source)
            source_hash = sha256_file(source)

            manifests = []
            outputs = []
            for suffix in ("a", "b"):
                output = root / f"catalog-{suffix}.sqlite"
                manifest_path = root / f"manifest-{suffix}.json"
                manifest = export_catalog(
                    source_path=source,
                    region_path=shape,
                    output_path=output,
                    manifest_path=manifest_path,
                    snapshot_id="test-snapshot-v1",
                    expected_source_sha256=source_hash,
                    output_label="test catalog",
                )
                manifests.append(manifest)
                outputs.append(output)
                self.assertEqual(
                    manifest,
                    json.loads(manifest_path.read_text(encoding="utf-8")),
                )

            self.assertEqual(sha256_file(outputs[0]), sha256_file(outputs[1]))
            self.assertEqual(sha256_file(source), source_hash)
            self.assertEqual(manifests[0]["selection"]["included_rows"], 3)
            self.assertEqual(
                manifests[0]["selection"]["bounding_box_outside_polygon"], 1
            )

            destination = sqlite3.connect(
                f"{outputs[0].resolve().as_uri()}?mode=ro", uri=True
            )
            rows = destination.execute(
                """
                SELECT event_id, source_catalog, source_event_id,
                       origin_time_utc, event_type
                FROM catalog_events ORDER BY origin_time_utc
                """
            ).fetchall()
            integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
            destination.close()
            self.assertEqual(integrity, "ok")
            self.assertEqual(
                rows,
                [
                    (
                        "usgs-fdsn:source-a",
                        "usgs-fdsn",
                        "source-a",
                        "2020-01-01T00:00:00.100Z",
                        "earthquake",
                    ),
                    (
                        "usgs-legacy:legacy-usgs-b",
                        "usgs-legacy",
                        "legacy-usgs-b",
                        "2020-01-02T00:00:00.200Z",
                        "earthquake",
                    ),
                    (
                        "legacy-earthquake-db:6",
                        "legacy-earthquake-db",
                        "6",
                        "2020-01-06T00:00:00.600Z",
                        "earthquake",
                    ),
                ],
            )

    def test_manifest_rejects_committed_source(self):
        manifest = {
            "schema_version": 1,
            "status": "exported",
            "source": {"sha256": "a" * 64, "committed": True},
            "region": {"shape_sha256": "b" * 64},
            "selection": {"included_rows": 1},
            "normalization": {},
            "output": {"sha256": "c" * 64, "rows": 1},
        }
        with self.assertRaisesRegex(ValueError, "never be committed"):
            validate_export_manifest(manifest)

    @staticmethod
    def _create_source(path: Path):
        connection = sqlite3.connect(path)
        connection.execute(
            """
            CREATE TABLE earthquakes (
                event_id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                depth REAL,
                mag REAL,
                usgs_event_id TEXT,
                event_type TEXT,
                usgs_status TEXT,
                usgs_updated_at TEXT,
                is_catalog_earthquake INTEGER NOT NULL,
                excluded_reason TEXT,
                source_catalog TEXT,
                source_event_id TEXT,
                source_url TEXT,
                source_retrieved_at TEXT,
                source_payload_hash TEXT
            )
            """
        )
        rows = [
            (1, "2020-01-01", "00:00:00.100", 0.5, 0.5, 5.0, 3.0, None, None, None, None, 1, None, "usgs-fdsn", "source-a", None, None, "a" * 64),
            (2, "2020-01-02", "00:00:00.200", 1.0, 1.0, 6.0, 3.1, "legacy-usgs-b", None, None, None, 1, None, None, None, None, None, None),
            (3, "2020-01-03", "00:00:00.300", 1.5, 1.5, 7.0, 3.2, None, None, None, None, 1, None, None, None, None, None, None),
            (4, "2020-01-04", "00:00:00.400", 0.3, 0.3, 0.0, 1.0, None, "explosion", None, None, 0, "not earthquake", None, None, None, None, None),
            (5, "2020-01-05", "00:00:00.500", 0.4, 0.4, 8.0, None, None, None, None, None, 1, None, None, None, None, None, None),
            (6, "2020-01-06", "00:00:00.600", 0.25, 0.25, 9.0, 2.5, None, None, None, None, 1, None, None, None, None, None, None),
        ]
        connection.executemany(
            "INSERT INTO earthquakes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        connection.commit()
        connection.close()


if __name__ == "__main__":
    unittest.main()
