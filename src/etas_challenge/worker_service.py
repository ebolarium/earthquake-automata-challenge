"""Health service for the prospective scheduler container."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from urllib.parse import urlsplit

from etas_challenge.object_storage import ObjectStorageConfig
from etas_challenge.object_storage import storage_health


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


def handler_factory(checker):
    class WorkerRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if urlsplit(self.path).path != "/health":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
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
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            print(f"{self.address_string()} - {format % args}", flush=True)

    return WorkerRequestHandler


def create_server(host: str, port: int, checker):
    return ThreadingHTTPServer((host, port), handler_factory(checker))


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    database_url = os.environ.get("DATABASE_URL")
    require_storage = os.environ.get("REQUIRE_OBJECT_STORAGE", "0") == "1"
    server = create_server(
        host,
        port,
        lambda: combined_health(database_url, require_storage),
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
