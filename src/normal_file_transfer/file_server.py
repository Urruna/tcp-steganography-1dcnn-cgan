"""正常 HTTP 文件服务：为 Normal 数据集提供文件下载业务。"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FILES_DIR = Path(os.getenv("FILES_DIR", "/app/files")).resolve()
LOG_DIR = Path(os.getenv("LOG_DIR", "/app/logs"))
LOG_FILE = LOG_DIR / "server_events.csv"
EXPERIMENT_ID = os.getenv("EXPERIMENT_ID", "normal_v1")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "9003"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", str(64 * 1024)))


def ensure_log() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(
                [
                    "timestamp",
                    "experiment_id",
                    "connection_id",
                    "client",
                    "method",
                    "path",
                    "status",
                    "bytes_sent",
                    "duration_ms",
                ]
            )


def _manifest() -> dict[str, object]:
    path = FILES_DIR / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FileHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "NormalFileServer/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[file_server] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        connection_id = str(uuid.uuid4())
        start = time.monotonic()
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if path == "/":
            path = "/report_small.txt"
        rel = path.lstrip("/")
        target = (FILES_DIR / rel).resolve()
        if not str(target).startswith(str(FILES_DIR)) or not target.is_file():
            self.send_error(404, "file not found")
            self._log(connection_id, "GET", path, 404, 0, start)
            return

        size = target.stat().st_size
        sha256 = _sha256(target)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.send_header("X-File-SHA256", sha256)
        self.send_header("Connection", "close")
        self.end_headers()

        sent = 0
        try:
            with target.open("rb") as file:
                while True:
                    chunk = file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    sent += len(chunk)
        except (BrokenPipeError, ConnectionError):
            pass
        self._log(connection_id, "GET", path, 200, sent, start)

    def _log(
        self,
        connection_id: str,
        method: str,
        path: str,
        status: int,
        sent: int,
        start: float,
    ) -> None:
        duration_ms = (time.monotonic() - start) * 1000.0
        with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(
                [
                    f"{time.time():.6f}",
                    EXPERIMENT_ID,
                    connection_id,
                    self.client_address[0],
                    method,
                    path,
                    status,
                    sent,
                    f"{duration_ms:.3f}",
                ]
            )


def main() -> None:
    ensure_log()
    manifest = _manifest()
    print(f"[file_server] serving {FILES_DIR}, manifest={bool(manifest)}", flush=True)
    server = ThreadingHTTPServer((HOST, PORT), FileHandler)
    print(f"[file_server] listening {HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
