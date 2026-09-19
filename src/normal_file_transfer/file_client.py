"""正常文件下载客户端：经由 Proxy-A → Proxy-B 下载文件并记录客户端事件。"""

from __future__ import annotations

import csv
import hashlib
import os
import socket
import sys
import time
import uuid
from pathlib import Path

TARGET_HOST = os.getenv("TARGET_HOST", "proxy_a")
TARGET_PORT = int(os.getenv("TARGET_PORT", "9001"))
FILE_PATHS = [
    p.strip()
    for p in os.getenv(
        "FILE_PATHS",
        "/report_small.txt,/report_medium.txt,/report_large.bin",
    ).split(",")
    if p.strip()
]
SESSIONS = int(os.getenv("SESSIONS", "8"))
INTER_SESSION_DELAY = float(os.getenv("INTER_SESSION_DELAY", "0.5"))
EXPERIMENT_ID = os.getenv("EXPERIMENT_ID", "normal_v1")
LOG_FILE = Path(os.getenv("LOG_FILE", "/app/logs/client_events.csv"))
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/app/downloads"))


def ensure_log() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(
                [
                    "timestamp",
                    "experiment_id",
                    "session_index",
                    "client_session_id",
                    "target",
                    "path",
                    "status",
                    "request_bytes",
                    "response_bytes",
                    "duration_ms",
                    "sha256",
                    "expected_sha256",
                    "result",
                ]
            )


def log_event(
    session_index: int,
    client_session_id: str,
    path: str,
    status: str,
    request_bytes: int,
    response_bytes: int,
    duration_ms: float,
    sha256: str,
    expected_sha256: str,
    result: str,
) -> None:
    with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
        csv.writer(file).writerow(
            [
                f"{time.time():.6f}",
                EXPERIMENT_ID,
                session_index,
                client_session_id,
                f"{TARGET_HOST}:{TARGET_PORT}",
                path,
                status,
                request_bytes,
                response_bytes,
                f"{duration_ms:.3f}",
                sha256,
                expected_sha256,
                result,
            ]
        )


def wait_for_proxy(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((TARGET_HOST, TARGET_PORT), timeout=0.5):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"proxy {TARGET_HOST}:{TARGET_PORT} not ready")


def download_once(path: str) -> tuple[str, int, int, str, str]:
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: file_server\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")
    with socket.create_connection((TARGET_HOST, TARGET_PORT), timeout=10) as sock:
        sock.settimeout(30)
        sock.sendall(request)
        f = sock.makefile("rb")
        status_line = f.readline().decode("latin-1").strip()
        headers: dict[str, str] = {}
        while True:
            line = f.readline()
            if line in (b"\r\n", b"\n", b""):
                break
            key, _, value = line.decode("latin-1").partition(":")
            headers[key.strip().lower()] = value.strip()
        expected = headers.get("x-file-sha256", "")
        length = int(headers.get("content-length", "0"))
        digest = hashlib.sha256()
        received = 0
        remaining = length
        while remaining > 0:
            chunk = f.read(min(64 * 1024, remaining))
            if not chunk:
                break
            digest.update(chunk)
            received += len(chunk)
            remaining -= len(chunk)
        sock_status = status_line.split(" ")[1] if " " in status_line else "000"
        sha256 = digest.hexdigest()
        result = "ok"
        if received != length:
            result = "length_mismatch"
        elif expected and sha256 != expected:
            result = "sha256_mismatch"
        return sock_status, len(request), received, sha256, expected if result == "ok" else result


def main() -> None:
    ensure_log()
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    wait_for_proxy()
    failures = 0
    for index in range(SESSIONS):
        path = FILE_PATHS[index % len(FILE_PATHS)]
        session_id = str(uuid.uuid4())
        start = time.monotonic()
        try:
            status, request_bytes, response_bytes, sha256, expected = download_once(path)
            result = "ok" if expected == sha256 else expected
        except (OSError, ValueError) as exc:
            status = "000"
            request_bytes = 0
            response_bytes = 0
            sha256 = ""
            expected = ""
            result = f"error:{exc}"
        duration_ms = (time.monotonic() - start) * 1000.0
        if result != "ok":
            failures += 1
        log_event(
            index,
            session_id,
            path,
            status,
            request_bytes,
            response_bytes,
            duration_ms,
            sha256,
            expected,
            result,
        )
        print(
            f"[file_client] session={index} path={path} status={status} "
            f"bytes={response_bytes} duration_ms={duration_ms:.1f} result={result}",
            flush=True,
        )
        time.sleep(INTER_SESSION_DELAY)
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
