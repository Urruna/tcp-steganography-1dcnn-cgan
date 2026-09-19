"""正常业务服务端：行式 TCP Echo。

它完全不知道隐蔽数据的存在：收到一行文本就原样回一行。
"""

from __future__ import annotations

import argparse
import socketserver


class EchoHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            f = self.request.makefile("rb")
            while True:
                line = f.readline()
                if not line:
                    break
                self.request.sendall(line)
            f.close()
        except OSError:
            pass
        finally:
            try:
                self.request.close()
            except OSError:
                pass


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(listen_host: str, listen_port: int) -> None:
    with ReusableTCPServer((listen_host, listen_port), EchoHandler) as srv:
        print(f"[echo_server] listening {listen_host}:{listen_port}", flush=True)
        srv.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="line echo server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9003)
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
