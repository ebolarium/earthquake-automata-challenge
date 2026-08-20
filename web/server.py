"""Dependency-free HTTP server for the independent ETAS web page."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATIC = ROOT / "web" / "static"
DEFAULT_SNAPSHOT = ROOT / "artifacts" / "web-v1" / "latest-forecast.json"


class SnapshotStore:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._mtime_ns = None
        self._payload = None
        self._etag = None

    def read(self):
        stat = self.path.stat()
        if self._mtime_ns != stat.st_mtime_ns:
            payload = self.path.read_bytes()
            json.loads(payload)
            self._payload = payload
            self._etag = hashlib.sha256(payload).hexdigest()
            self._mtime_ns = stat.st_mtime_ns
        return self._payload, self._etag


def handler_factory(static_dir: Path, snapshot_path: Path):
    static_root = static_dir.resolve()
    store = SnapshotStore(snapshot_path)

    class ETASRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static_root), **kwargs)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/forecast":
                self._serve_snapshot(store)
                return
            if path == "/api/health":
                self._serve_health(store)
                return
            if path == "/":
                self.path = "/index.html"
            super().do_GET()

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            super().end_headers()

        def _serve_snapshot(self, snapshot_store: SnapshotStore):
            try:
                payload, etag = snapshot_store.read()
            except (FileNotFoundError, json.JSONDecodeError):
                self._json_error(HTTPStatus.SERVICE_UNAVAILABLE, "snapshot_unavailable")
                return
            if self.headers.get("If-None-Match") == f'"{etag}"':
                self.send_response(HTTPStatus.NOT_MODIFIED)
                self.send_header("ETag", f'"{etag}"')
                self.end_headers()
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("ETag", f'"{etag}"')
            self.end_headers()
            self.wfile.write(payload)

        def _serve_health(self, snapshot_store: SnapshotStore):
            try:
                payload, etag = snapshot_store.read()
                snapshot = json.loads(payload)
                body = {
                    "status": "ok",
                    "snapshot_id": snapshot.get("snapshot_id"),
                    "issue_time": snapshot["forecast"]["issue_time"],
                    "etag": etag,
                }
                status = HTTPStatus.OK
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                body = {"status": "degraded", "reason": "snapshot_unavailable"}
                status = HTTPStatus.SERVICE_UNAVAILABLE
            encoded = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def _json_error(self, status: HTTPStatus, reason: str):
            payload = json.dumps({"status": "error", "reason": reason}).encode(
                "utf-8"
            )
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):
            print(f"{self.address_string()} - {format % args}", flush=True)

    return ETASRequestHandler


def create_server(host: str, port: int, static_dir: Path, snapshot_path: Path):
    if not static_dir.is_dir():
        raise ValueError(f"static directory does not exist: {static_dir}")
    return ThreadingHTTPServer(
        (host, port), handler_factory(static_dir, snapshot_path)
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "8080"))
    )
    parser.add_argument(
        "--static",
        type=Path,
        default=Path(os.environ.get("STATIC_DIR", DEFAULT_STATIC)),
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path(os.environ.get("SNAPSHOT_PATH", DEFAULT_SNAPSHOT)),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    server = create_server(args.host, args.port, args.static, args.snapshot)
    print(f"ETAS web listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
