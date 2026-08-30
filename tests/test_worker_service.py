import json
from http import HTTPStatus
import threading
import unittest
import urllib.error
import urllib.request

from etas_challenge.worker_service import create_server


class WorkerServiceTest(unittest.TestCase):
    def start_server(self, result):
        try:
            server = create_server("127.0.0.1", 0, lambda: result)
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


if __name__ == "__main__":
    unittest.main()
