"""Proxy-A（发送端代理）：正常 TCP 转发 + 分块长度调制。

调制方式（第一版，最容易落地）：
- cover business 为“逐行上传文本、Server 逐行 Echo”；
- 秘密帧的每个 bit 占一行 cover record；
- bit=0：Proxy-A 把这一行作为 1 个应用层 write 原样转发；
- bit=1：Proxy-A 把这一行拆成 2 个 write，中间加一个短间隔；
- Proxy-B 在自己收到的 recv 事件数上恢复 bit（1 次=0，2 次=1）。

不改动任何业务字节：Server 收到的内容与 Client 发送的内容完全一致。
"""

from __future__ import annotations

import argparse
import os
import socket
import socketserver
import threading
import time

from event_log import SessionEventLog
from framing import build_frame, bytes_to_bits


def _set_nodelay(sock: socket.socket) -> None:
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass


def serve(
    listen_host: str,
    listen_port: int,
    upstream_host: str,
    upstream_port: int,
    message: bytes = b"",
    split_gap: float = 0.08,
    log_dir: str | None = None,
    experiment_id: str = "newtry97",
    session_id: str | None = None,
    frame_id: int = 0,
    leading_normal: int = 0,
) -> None:
    frame_bits = bytes_to_bits(build_frame(message, frame_id=frame_id)) if message else []
    total_bits = len(frame_bits)

    class ReusableServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            client = self.request
            _set_nodelay(client)
            try:
                up = socket.create_connection((upstream_host, upstream_port), timeout=10)
            except OSError as exc:
                print(f"[proxy_a] upstream connect failed: {exc}", flush=True)
                return
            _set_nodelay(up)

            self._logger = None
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                self._logger = SessionEventLog(
                    os.path.join(log_dir, "proxy_a_events.csv"),
                    proxy_name="proxy_a",
                    experiment_id=experiment_id,
                    session_id=session_id,
                )

            rev = threading.Thread(target=self._relay_reverse, args=(up, client), daemon=True)
            rev.start()
            try:
                self._forward(client, up, frame_bits)
            finally:
                try:
                    up.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                rev.join(timeout=5)
                try:
                    up.close()
                except OSError:
                    pass
                try:
                    client.close()
                except OSError:
                    pass

        def _relay_reverse(self, up: socket.socket, client: socket.socket) -> None:
            try:
                while True:
                    data = up.recv(65536)
                    if not data:
                        break
                    if self._logger is not None:
                        self._logger.log("reverse", len(data))
                    client.sendall(data)
            except OSError:
                pass

        def _send_upstream(
            self,
            up: socket.socket,
            chunk: bytes,
            encoded_bit: int | None,
            frame_id: int | None,
        ) -> None:
            if self._logger is not None:
                self._logger.log(
                    "forward",
                    len(chunk),
                    frame_id=frame_id,
                    encoded_bit=encoded_bit,
                )
            up.sendall(chunk)

        def _forward(
            self,
            client: socket.socket,
            up: socket.socket,
            frame_bits: list[int],
        ) -> None:
            bit_index = 0
            total_bits = len(frame_bits)
            line_index = 0
            try:
                f = client.makefile("rb")
                while True:
                    line = f.readline()
                    if not line:
                        break
                    if leading_normal > 0 and line_index < leading_normal:
                        self._send_upstream(up, line, None, None)
                    elif bit_index < total_bits:
                        bit = frame_bits[bit_index]
                        bit_index += 1
                        if bit == 0:
                            self._send_upstream(up, line, bit, frame_id)
                        else:
                            mid = len(line) // 2
                            if mid <= 0 or mid >= len(line):
                                self._send_upstream(up, line, bit, frame_id)
                            else:
                                self._send_upstream(up, line[:mid], bit, frame_id)
                                time.sleep(split_gap)
                                self._send_upstream(up, line[mid:], bit, frame_id)
                    else:
                        self._send_upstream(up, line, None, None)
                    line_index += 1
                f.close()
            except OSError as exc:
                print(f"[proxy_a] forward ended: {exc}", flush=True)

    with ReusableServer((listen_host, listen_port), Handler) as srv:
        print(
            f"[proxy_a] listening {listen_host}:{listen_port} -> "
            f"{upstream_host}:{upstream_port}, covert_bits={total_bits}",
            flush=True,
        )
        srv.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Proxy-A sender")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=9001)
    parser.add_argument("--upstream-host", default="127.0.0.1")
    parser.add_argument("--upstream-port", type=int, default=9002)
    parser.add_argument("--message", default="Hello from A to B (newtry97)")
    parser.add_argument("--gap", type=float, default=0.08, help="bit=1 两次 write 的间隔秒")
    parser.add_argument("--log-dir", default=None, help="写入 proxy_a_events.csv 的目录")
    parser.add_argument("--experiment-id", default="newtry97")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--frame-id", type=int, default=0)
    parser.add_argument(
        "--leading-normal",
        type=int,
        default=0,
        help="在秘密帧前先透传多少行正常业务，用于验证 Proxy-B 的滑窗搜索",
    )
    args = parser.parse_args()
    serve(
        args.listen_host,
        args.listen_port,
        args.upstream_host,
        args.upstream_port,
        message=args.message.encode("utf-8"),
        split_gap=args.gap,
        log_dir=args.log_dir,
        experiment_id=args.experiment_id,
        session_id=args.session_id,
        frame_id=args.frame_id,
        leading_normal=args.leading_normal,
    )


if __name__ == "__main__":
    main()
