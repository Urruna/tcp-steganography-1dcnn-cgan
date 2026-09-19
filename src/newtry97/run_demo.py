"""一条命令跑通：Client -> Proxy-A -> Proxy-B -> Server 的隐蔽传输。

运行：
    python run_demo.py

成功标志：
    [client] echo ok N/N
    [proxy_b] RECOVERED ... payload='Hello from A to B (newtry97)' crc=ok
"""

from __future__ import annotations

import multiprocessing as mp
import os
import socket
import time
import uuid

import covert_client
import echo_server
from event_log import ensure_header
import receiver_proxy
import sender_proxy
from framing import build_frame

HOST = "127.0.0.1"
PORT_A = 9001
PORT_B = 9002
PORT_SERVER = 9003
MESSAGE = b"Hello from A to B (newtry97)"
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LEADING_NORMAL = 16  # 帧前普通行，验证 Proxy-B 不从第 1 行开始解码
TRAILING_NORMAL = 16  # 帧后普通行


def wait_port(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError(f"port {port} did not open")


def main() -> None:
    num_bits = len(build_frame(MESSAGE)) * 8
    num_lines = LEADING_NORMAL + num_bits + TRAILING_NORMAL
    os.makedirs(LOG_DIR, exist_ok=True)
    ensure_header(os.path.join(LOG_DIR, "proxy_a_events.csv"))
    ensure_header(os.path.join(LOG_DIR, "proxy_b_events.csv"))
    session_id = str(uuid.uuid4())
    recovered_file = os.path.join(LOG_DIR, "recovered.txt")

    procs = [
        mp.Process(
            target=echo_server.serve,
            args=(HOST, PORT_SERVER),
            name="echo-server",
        ),
        mp.Process(
            target=receiver_proxy.serve,
            args=(
                HOST,
                PORT_B,
                HOST,
                PORT_SERVER,
                recovered_file,
                LOG_DIR,
                "newtry97",
                session_id,
            ),
            name="proxy-b",
        ),
        mp.Process(
            target=sender_proxy.serve,
            kwargs={
                "listen_host": HOST,
                "listen_port": PORT_A,
                "upstream_host": HOST,
                "upstream_port": PORT_B,
                "message": MESSAGE,
                "split_gap": 0.08,
                "log_dir": LOG_DIR,
                "experiment_id": "newtry97",
                "session_id": session_id,
                "frame_id": 0,
                "leading_normal": LEADING_NORMAL,
            },
            name="proxy-a",
        ),
    ]

    for p in procs:
        p.start()
    try:
        for port in (PORT_SERVER, PORT_B, PORT_A):
            wait_port(port)
        ok, total = covert_client.run(HOST, PORT_A, num_lines)
        print(f"[demo] client echo {ok}/{total}", flush=True)
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.join(timeout=5)


if __name__ == "__main__":
    main()
