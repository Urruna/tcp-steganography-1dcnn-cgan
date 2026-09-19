"""容器化客户端入口：自动计算 cover 行数并等待 Proxy-A 就绪。"""

from __future__ import annotations

import os
import socket
import sys
import time

import covert_client
from framing import build_frame


def _wait_port(host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"port {host}:{port} did not become ready")


def main() -> None:
    host = os.environ.get("TARGET_HOST", "proxy_a")
    port = int(os.environ.get("TARGET_PORT", "9001"))
    message = os.environ.get("SECRET_MESSAGE", "Hello from A to B (newtry97)")
    frame_id = int(os.environ.get("FRAME_ID", "917"))
    leading_normal = int(os.environ.get("LEADING_NORMAL", "16"))
    trailing_normal = int(os.environ.get("TRAILING_NORMAL", "16"))

    frame_bits = len(build_frame(message, frame_id=frame_id)) * 8
    num_lines = leading_normal + frame_bits + trailing_normal
    _wait_port(host, port)

    ok, total = covert_client.run(host, port, num_lines)
    print(
        f"[container_client] frame_bits={frame_bits} lines={num_lines} "
        f"echo={ok}/{total}",
        flush=True,
    )
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
