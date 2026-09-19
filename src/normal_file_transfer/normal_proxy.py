"""普通透明 TCP 代理（线程版）：只转发字节并记录应用层事件日志。"""

from __future__ import annotations

import csv
import os
import socket
import socketserver
import threading
import time
import uuid
from pathlib import Path

PROXY_NAME = os.getenv("PROXY_NAME", "proxy")
LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "9001"))
TARGET_HOST = os.getenv("TARGET_HOST", "localhost")
TARGET_PORT = int(os.getenv("TARGET_PORT", "9002"))
EXPERIMENT_ID = os.getenv("EXPERIMENT_ID", "normal_v1")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "4096"))
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / f"{PROXY_NAME}_events.csv"


def ensure_log_file() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(
                [
                    "timestamp",
                    "proxy_name",
                    "experiment_id",
                    "session_id",
                    "direction",
                    "event_index",
                    "byte_length",
                    "inter_event_gap_ms",
                ]
            )


def _set_nodelay(sock: socket.socket) -> None:
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        client = self.request
        _set_nodelay(client)
        session_id = str(uuid.uuid4())
        peer = self.client_address
        print(f"[{PROXY_NAME}] session {session_id} from {peer}", flush=True)
        try:
            upstream = socket.create_connection((TARGET_HOST, TARGET_PORT), timeout=10)
        except OSError as exc:
            print(f"[{PROXY_NAME}] upstream connect failed: {exc}", flush=True)
            client.close()
            return
        _set_nodelay(upstream)

        reverse = threading.Thread(
            target=self._relay,
            args=(upstream, client, session_id, "reverse"),
            daemon=True,
        )
        reverse.start()
        try:
            self._relay(client, upstream, session_id, "forward")
        finally:
            try:
                upstream.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            reverse.join(timeout=5)
            upstream.close()
            client.close()
            print(f"[{PROXY_NAME}] session closed: {session_id}", flush=True)

    def _relay(
        self,
        source: socket.socket,
        destination: socket.socket,
        session_id: str,
        direction: str,
    ) -> None:
        event_index = 0
        last_event_time = time.monotonic()
        try:
            while True:
                data = source.recv(CHUNK_SIZE)
                if not data:
                    break
                now = time.monotonic()
                gap_ms = (now - last_event_time) * 1000.0
                last_event_time = now
                event_index += 1
                write_log(
                    session_id,
                    direction,
                    event_index,
                    len(data),
                    gap_ms,
                )
                destination.sendall(data)
        except OSError as exc:
            print(
                f"[{PROXY_NAME}] relay error ({direction}): {exc}",
                flush=True,
            )


def write_log(
    session_id: str,
    direction: str,
    event_index: int,
    byte_length: int,
    inter_event_gap_ms: float,
) -> None:
    with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
        csv.writer(file).writerow(
            [
                f"{time.time():.6f}",
                PROXY_NAME,
                EXPERIMENT_ID,
                session_id,
                direction,
                event_index,
                byte_length,
                f"{inter_event_gap_ms:.3f}",
            ]
        )


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    ensure_log_file()
    with ReusableTCPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler) as server:
        print(
            f"[{PROXY_NAME}] listening on {LISTEN_HOST}:{LISTEN_PORT}, "
            f"target={TARGET_HOST}:{TARGET_PORT}",
            flush=True,
        )
        server.serve_forever()


if __name__ == "__main__":
    main()
