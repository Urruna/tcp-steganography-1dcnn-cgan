"""结构化 CSV 事件日志（newtry97 版）。

字段与 `baseline_lenmix_v1/*.csv` 对齐，并在末尾追加隐蔽通道需要的
`frame_id / encoded_bit / recovered_bit / crc_status` 四列：

    timestamp,proxy_name,experiment_id,session_id,direction,
    event_index,byte_length,inter_event_gap_ms,frame_id,
    encoded_bit,recovered_bit,crc_status

行语义：一行 = 代理上的一次应用层事件。
- proxy_a forward  ：Proxy-A 对 Proxy-B 的一次 sendall()；
- proxy_a reverse  ：Proxy-A 从 Proxy-B 读到并回给 Client 的字节；
- proxy_b forward  ：Proxy-B 从 Proxy-A 收到的一次 recv()；
- proxy_b reverse  ：Proxy-B 从 Server 读到并回给 Proxy-A 的字节。

`inter_event_gap_ms` 按同一方向相邻事件计算；会话内第一个事件以连接建立为基准，
与 baseline CSV 的行为保持一致。
"""

from __future__ import annotations

import csv
import os
import time
import uuid

CSV_HEADER = [
    "timestamp",
    "proxy_name",
    "experiment_id",
    "session_id",
    "direction",
    "event_index",
    "byte_length",
    "inter_event_gap_ms",
    "frame_id",
    "encoded_bit",
    "recovered_bit",
    "crc_status",
]


def ensure_header(path: str) -> None:
    """文件不存在或为空时写入表头。

    用 ``open(..., "x")`` 原子创建，避免多个连接/进程同时初始化同一个
    CSV 时重复写表头。
    """
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    try:
        with open(path, "x", newline="", encoding="utf-8") as fh:
            fh.write(",".join(CSV_HEADER) + "\n")
    except FileExistsError:
        # 另一个线程/进程刚刚创建了文件；等它把表头写完。
        for _ in range(200):
            if os.path.getsize(path) > 0:
                return
            time.sleep(0.01)
        # 极端兜底：文件存在但仍是空的，才补写表头。
        with open(path, "a", newline="", encoding="utf-8") as fh:
            fh.write(",".join(CSV_HEADER) + "\n")


class SessionEventLog:
    """单个会话的 CSV 日志器。

    每行即时落盘，因此多个并发连接/进程可以安全地写同一个日志文件；
    需要按会话切分数据时用 `session_id` 过滤即可。
    """

    def __init__(
        self,
        path: str,
        proxy_name: str,
        experiment_id: str = "newtry97",
        session_id: str | None = None,
    ) -> None:
        self.path = os.path.abspath(path)
        self.proxy_name = proxy_name
        self.experiment_id = experiment_id
        self.session_id = session_id or str(uuid.uuid4())
        self._session_start = time.time()
        self._event_index = {"forward": 0, "reverse": 0}
        self._last_ts: dict[str, float | None] = {"forward": None, "reverse": None}
        ensure_header(self.path)

    def log(
        self,
        direction: str,
        byte_length: int,
        ts: float | None = None,
        frame_id: int | None = None,
        encoded_bit: int | None = None,
        recovered_bit: int | None = None,
        crc_status: str = "",
    ) -> None:
        now = time.time() if ts is None else ts
        self._event_index[direction] += 1
        last = self._last_ts[direction]
        if last is None:
            gap_ms = (now - self._session_start) * 1000.0
        else:
            gap_ms = (now - last) * 1000.0
        self._last_ts[direction] = now

        def field(v: object) -> str:
            return "" if v is None else str(v)

        row = [
            f"{now:.6f}",
            self.proxy_name,
            self.experiment_id,
            self.session_id,
            direction,
            self._event_index[direction],
            byte_length,
            f"{gap_ms:.3f}",
            field(frame_id),
            field(encoded_bit),
            field(recovered_bit),
            crc_status,
        ]
        with open(self.path, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(row)
