import json
from http import HTTPStatus
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from etas_challenge.worker_service import create_server


class WorkerServiceTest(unittest.TestCase):
    def start_server(self, result, dashboard=None):
        static = Path(__file__).resolve().parents[1] / "prospective_web" / "static"
        try:
            server = create_server(
                "127.0.0.1", 0, lambda: result,
                None if dashboard is None else lambda: dashboard,
                static,
            )
        except PermissionError:
            self.skipTest("local sockets are unavailable in this sandbox")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: thread.join(timeout=2))
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}"

    def test_healthy_database(self):
        base = self.start_server((True, None))
        with urllib.request.urlopen(f"{base}/health") as response:
            payload = json.load(response)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "prospective-worker")

    def test_unavailable_database(self):
        base = self.start_server((False, "database_unavailable"))
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(f"{base}/health")
        self.assertEqual(raised.exception.code, HTTPStatus.SERVICE_UNAVAILABLE)

    def test_serves_dashboard_and_static_application(self):
        dashboard = {"schema_version": 1, "pipeline_status": "ok", "regions": []}
        base = self.start_server((True, None), dashboard)
        with urllib.request.urlopen(f"{base}/") as response:
            self.assertIn(b"CH-008 Prospective Test", response.read())
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        with urllib.request.urlopen(f"{base}/api/dashboard") as response:
            self.assertEqual(json.load(response), dashboard)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        with urllib.request.urlopen(f"{base}/about.html") as response:
            content = response.read()
            self.assertIn("CH-008 Yöntem ve Bilimsel Protokol".encode(), content)
            self.assertIn(b"hello@bboga.com", content)
        with urllib.request.urlopen(f"{base}/en/") as response:
            self.assertIn(b"CH-008 Prospective Test", response.read())
        with urllib.request.urlopen(f"{base}/en/about.html") as response:
            content = response.read()
            self.assertIn(b"CH-008 Method and Scientific Protocol", content)
            self.assertIn(b"hello@bboga.com", content)


if __name__ == "__main__":
    unittest.main()
