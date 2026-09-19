"""Proxy-B（接收端代理）：从转发事件中恢复隐蔽比特，同时透明转发业务。

观察对象不是网络抓包里的 IP 分片，而是 Proxy-A -> Proxy-B 这一条 TCP
连接上的应用层 recv 事件：一个完整 cover record 被 1 次 recv 收到记为 0，
被 2 次 recv 收到记为 1。恢复出的比特流按 framing.py 解析并做 CRC 校验。
"""

from __future__ import annotations

import argparse
import os
import socket
import socketserver
import threading
import time

from event_log import SessionEventLog
from framing import FrameDecoder


def _set_nodelay(sock: socket.socket) -> None:
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass


def serve(
    listen_host: str,
    listen_port: int,
    server_host: str,
    server_port: int,
    recovered_file: str | None = None,
    log_dir: str | None = None,
    experiment_id: str = "newtry97",
    session_id: str | None = None,
) -> None:
    class ReusableServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            from_a = self.request
            _set_nodelay(from_a)
            try:
                to_server = socket.create_connection((server_host, server_port), timeout=10)
            except OSError as exc:
                print(f"[proxy_b] server connect failed: {exc}", flush=True)
                return
            _set_nodelay(to_server)

            self._logger = None
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                self._logger = SessionEventLog(
                    os.path.join(log_dir, "proxy_b_events.csv"),
                    proxy_name="proxy_b",
                    experiment_id=experiment_id,
                    session_id=session_id,
                )

            rev = threading.Thread(
                target=self._relay_reverse,
                args=(to_server, from_a),
                daemon=True,
            )
            rev.start()
            try:
                self._decode_forward(from_a, to_server)
            finally:
                try:
                    to_server.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                rev.join(timeout=5)
                try:
                    to_server.close()
                except OSError:
                    pass
                try:
                    from_a.close()
                except OSError:
                    pass

        def _relay_reverse(self, src: socket.socket, dst: socket.socket) -> None:
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    if self._logger is not None:
                        self._logger.log("reverse", len(data))
                    dst.sendall(data)
            except OSError:
                pass

        def _flush_record_log(
            self,
            segment_events: list[tuple[float, int]],
            recovered_bit: int | None,
            crc_status: str,
            frame_id: int | None = None,
        ) -> None:
            if self._logger is None:
                return
            for ts, byte_len in segment_events:
                self._logger.log(
                    "forward",
                    byte_len,
                    ts=ts,
                    frame_id=frame_id,
                    recovered_bit=recovered_bit,
                    crc_status=crc_status,
                )

        def _decode_forward(self, from_a: socket.socket, to_server: socket.socket) -> None:
            pending = b""
            segments_in_record = 0
            segment_events: list[tuple[float, int]] = []
            decoder = FrameDecoder()
            wrote_recovered = False
            try:
                while True:
                    data = from_a.recv(65536)
                    if not data:
                        break
                    recv_ts = time.time()
                    segments_in_record += 1
                    segment_events.append((recv_ts, len(data)))
                    pending += data

                    # 本实验的 cover business 是“发一行 -> 等一行 Echo”，
                    # 因此同一时刻上游只会有一个 record 在途。
                    while b"\n" in pending:
                        idx = pending.index(b"\n") + 1
                        line = pending[:idx]
                        pending = pending[idx:]

                        recovered_bit: int | None = None
                        crc_status = ""
                        frame_id: int | None = None
                        recovered_bit = 0 if segments_in_record == 1 else 1
                        events = decoder.push(recovered_bit)
                        crc_status = "searching"
                        for event in events:
                            if event.status == "ok":
                                frame_id = event.frame_id
                                crc_status = "ok"
                                text = event.payload.decode("utf-8", "replace")
                                print(
                                    f"[proxy_b] RECOVERED {event.frame_bits} bits | "
                                    f"frame_id={event.frame_id} | "
                                    f"payload={text!r} | crc=ok",
                                    flush=True,
                                )
                                if recovered_file:
                                    try:
                                        os.makedirs(
                                            os.path.dirname(recovered_file) or ".",
                                            exist_ok=True,
                                        )
                                        mode = "a" if wrote_recovered else "w"
                                        with open(
                                            recovered_file,
                                            mode,
                                            encoding="utf-8",
                                        ) as fh:
                                            fh.write(text + "\n")
                                        wrote_recovered = True
                                    except OSError as wexc:
                                        print(
                                            f"[proxy_b] recovered-file write failed: {wexc}",
                                            flush=True,
                                        )
                            else:
                                crc_status = "crc_bad"
                                print(
                                    f"[proxy_b] crc_bad | frame_id={event.frame_id} "
                                    f"after {event.frame_bits} bits",
                                    flush=True,
                                )

                        # 一个 record 结束后把组成它的 recv 事件补写成日志行。
                        self._flush_record_log(
                            segment_events,
                            recovered_bit=recovered_bit,
                            crc_status=crc_status,
                            frame_id=frame_id,
                        )
                        segment_events = []

                        # 完成一个 record 后才把整行交给 Server，字节保持不变。
                        to_server.sendall(line)
                        segments_in_record = 0

                if pending:
                    to_server.sendall(pending)
            except OSError as exc:
                print(f"[proxy_b] forward ended: {exc}", flush=True)

    with ReusableServer((listen_host, listen_port), Handler) as srv:
        print(
            f"[proxy_b] listening {listen_host}:{listen_port} -> "
            f"{server_host}:{server_port}",
            flush=True,
        )
        srv.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Proxy-B receiver")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=9002)
    parser.add_argument("--server-host", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=9003)
    parser.add_argument("--recovered-file", default=None)
    parser.add_argument("--log-dir", default=None, help="写入 proxy_b_events.csv 的目录")
    parser.add_argument("--experiment-id", default="newtry97")
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args()
    serve(
        args.listen_host,
        args.listen_port,
        args.server_host,
        args.server_port,
        recovered_file=args.recovered_file,
        log_dir=args.log_dir,
        experiment_id=args.experiment_id,
        session_id=args.session_id,
    )


if __name__ == "__main__":
    main()
