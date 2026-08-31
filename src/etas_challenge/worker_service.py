"""Health service for the prospective scheduler container."""

from __future__ import annotations

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from etas_challenge.object_storage import ObjectStorageConfig
from etas_challenge.object_storage import storage_health
from etas_challenge.prospective_dashboard import read_dashboard


DEFAULT_STATIC = Path(
    os.environ.get(
        "PROSPECTIVE_STATIC_DIR",
        Path.cwd() / "prospective_web" / "static",
    )
)
PROTOCOL_ID = "ch008-three-region-dry-run-v1"


def database_health(database_url: str | None) -> tuple[bool, str | None]:
    if not database_url:
        return False, "database_url_missing"
    try:
        import psycopg

        with psycopg.connect(database_url, connect_timeout=3) as connection:
            connection.execute("SELECT 1")
    except Exception:
        return False, "database_unavailable"
    return True, None


def combined_health(
    database_url: str | None,
    require_object_storage: bool,
) -> tuple[bool, str | None]:
    healthy, reason = database_health(database_url)
    if not healthy or not require_object_storage:
        return healthy, reason
    try:
        config = ObjectStorageConfig.from_environment()
    except ValueError:
        return False, "object_storage_config_invalid"
    return storage_health(config)


def handler_factory(checker, dashboard_reader=None, static_dir=None):
    static_root = Path(static_dir or DEFAULT_STATIC).resolve()

    class WorkerRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static_root), **kwargs)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/health":
                self._serve_health()
                return
            if path == "/api/dashboard":
                self._serve_dashboard()
                return
            if path == "/":
                self.path = "/index.html"
            elif path not in (
                "/index.html", "/about.html", "/styles.css", "/about.css", "/app.js"
            ):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            super().do_GET()

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
            )
            super().end_headers()

        def _serve_health(self):
            healthy, reason = checker()
            body = {
                "status": "ok" if healthy else "degraded",
                "service": "prospective-worker",
            }
            if reason:
                body["reason"] = reason
            commit = os.environ.get("SOURCE_COMMIT")
            if commit:
                body["source_commit"] = commit
            encoded = json.dumps(body).encode("utf-8")
            self.send_response(HTTPStatus.OK if healthy else HTTPStatus.SERVICE_UNAVAILABLE)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _serve_dashboard(self):
            if dashboard_reader is None:
                self._json_error(HTTPStatus.SERVICE_UNAVAILABLE, "dashboard_unavailable")
                return
            try:
                body = dashboard_reader()
            except Exception:
                self._json_error(HTTPStatus.SERVICE_UNAVAILABLE, "dashboard_unavailable")
                return
            encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _json_error(self, status, reason):
            encoded = json.dumps({"status": "error", "reason": reason}).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            print(f"{self.address_string()} - {format % args}", flush=True)

    return WorkerRequestHandler


def create_server(host: str, port: int, checker, dashboard_reader=None, static_dir=None):
    return ThreadingHTTPServer(
        (host, port), handler_factory(checker, dashboard_reader, static_dir)
    )


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    database_url = os.environ.get("DATABASE_URL")
    require_storage = os.environ.get("REQUIRE_OBJECT_STORAGE", "0") == "1"
    server = create_server(
        host,
        port,
        lambda: combined_health(database_url, require_storage),
        (
            None
            if not database_url
            else lambda: read_dashboard(database_url, PROTOCOL_ID)
        ),
    )
    print(f"Prospective worker listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
