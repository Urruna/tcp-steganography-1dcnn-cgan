"""正常业务客户端：向 Proxy-A 发送多行“报表文本”，逐行校验 Echo。

客户端不感知隐蔽数据。cover record 的节奏是“发一行 -> 等一行 Echo”，
这正是 Proxy-A/B 能稳定切分 record 的前提。
"""

from __future__ import annotations

import argparse
import socket


def recv_line(f) -> bytes:
    return f.readline()


def run(
    target_host: str,
    target_port: int,
    num_lines: int,
    record_len: int = 384,
) -> tuple[int, int]:
    sock = socket.create_connection((target_host, target_port), timeout=10)
    sock.settimeout(10)
    f = sock.makefile("rb")
    ok = 0
    for i in range(num_lines):
        prefix = f"cover-record-{i:05d}|".encode()
        body = b"x" * max(0, record_len - len(prefix) - 1)
        line = prefix + body + b"\n"
        sock.sendall(line)
        echo = recv_line(f)
        if echo != line:
            print(f"[client] line {i}: MISMATCH", flush=True)
        else:
            ok += 1
    sock.close()
    return ok, num_lines


def main() -> None:
    parser = argparse.ArgumentParser(description="normal cover client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--lines", type=int, default=256)
    parser.add_argument("--len", type=int, default=384, dest="record_len")
    args = parser.parse_args()
    ok, total = run(args.host, args.port, args.lines, args.record_len)
    print(f"[client] echo ok {ok}/{total}", flush=True)


if __name__ == "__main__":
    main()
