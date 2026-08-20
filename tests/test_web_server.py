import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.server import create_server


class WebServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.static = root / "static"
        self.static.mkdir()
        (self.static / "index.html").write_text("<h1>ETAS</h1>", encoding="utf-8")
        self.snapshot = root / "snapshot.json"
        self.snapshot.write_text(
            json.dumps(
                {
                    "snapshot_id": "test-v1",
                    "forecast": {"issue_time": "2020-01-01T00:00:00Z"},
                }
            ),
            encoding="utf-8",
        )
        try:
            self.server = create_server("127.0.0.1", 0, self.static, self.snapshot)
        except PermissionError:
            self.temporary.cleanup()
            self.skipTest("local sockets are unavailable in this sandbox")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def test_serves_static_forecast_and_health(self):
        with urllib.request.urlopen(f"{self.base}/") as response:
            self.assertIn(b"ETAS", response.read())
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        with urllib.request.urlopen(f"{self.base}/api/forecast") as response:
            forecast = json.load(response)
            etag = response.headers["ETag"]
        self.assertEqual(forecast["snapshot_id"], "test-v1")
        request = urllib.request.Request(
            f"{self.base}/api/forecast", headers={"If-None-Match": etag}
        )
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request)
        self.assertEqual(raised.exception.code, 304)
        with urllib.request.urlopen(f"{self.base}/api/health") as response:
            health = json.load(response)
        self.assertEqual(health["status"], "ok")


if __name__ == "__main__":
    unittest.main()
