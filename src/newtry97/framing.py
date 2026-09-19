"""newtry97 v0.2 帧格式与解码状态机。

帧格式（按 PDF 的建议扩展为正式协议）：

    | Preamble(32 bit) | Version(4 bit)+Reserved(4 bit)
      | Frame ID(16 bit) | Payload Length(16 bit)
      | Payload | CRC-16(16 bit) |

每个隐蔽比特仍由一行 cover record 承载；解码端不再假设帧从第 1 行开始，
而是在累积 bit 流里用滑动窗口搜索 Preamble，并在 CRC 失败后继续重同步。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

PREAMBLE = 0x6E9797A1  # 32 bit 同步字
VERSION = 1
PREAMBLE_BITS = 32
FRAME_HEAD_BITS = PREAMBLE_BITS + 8 + 16 + 16  # preamble/version/frame_id/length
CRC_BITS = 16
MAX_PAYLOAD = 512
MAX_BUFFER_BITS = 8192  # 足够容纳 512 B payload 帧与一段正常流量


def crc16(data: bytes) -> int:
    """CRC-16/XMODEM，便于在 Python 脚本间移植。"""
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


@dataclass
class DecodeEvent:
    """一次完整的帧解析结果。

    status: ``ok`` / ``crc_bad``
    """

    status: str
    frame_id: int
    payload: bytes
    frame_bits: int


def build_frame(
    payload: bytes | str,
    frame_id: int = 0,
    version: int = VERSION,
) -> bytes:
    """组装 v0.2 二进制帧。

    布局：| Preamble(4B) | Version+Reserved(1B) | Frame ID(2B)
          | Payload Length(2B) | Payload | CRC16(2B) |
    CRC 覆盖 Version/Frame ID/Length/Payload 组成的 body。
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    if not 0 <= len(payload) <= MAX_PAYLOAD:
        raise ValueError(f"payload length must be 0..{MAX_PAYLOAD}")
    if not 0 <= version <= 0x0F:
        raise ValueError("version must fit in 4 bits")
    if not 0 <= frame_id <= 0xFFFF:
        raise ValueError("frame_id must fit in 16 bits")

    # 高 4 bit 为 Version，低 4 bit 为 Reserved（保留给后续扩展）。
    header = struct.pack("!B", (version & 0x0F) << 4)
    body = header + struct.pack("!HH", frame_id & 0xFFFF, len(payload))
    body += payload
    crc = struct.pack("!H", crc16(body))
    return struct.pack("!I", PREAMBLE) + body + crc


def bytes_to_bits(data: bytes) -> list[int]:
    return [(byte >> shift) & 1 for byte in data for shift in range(7, -1, -1)]


def bits_to_bytes(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for bit in bits[i : i + 8]:
            v = (v << 1) | bit
        out.append(v)
    return bytes(out)


def _int_from_bits(bits, start: int, count: int) -> int:
    value = 0
    for bit in bits[start : start + count]:
        value = (value << 1) | bit
    return value


def _preamble_at(bits, start: int) -> bool:
    return _int_from_bits(bits, start, PREAMBLE_BITS) == PREAMBLE


def _parse_frame_at(bits, start: int) -> DecodeEvent | None:
    """尝试解析从 ``start`` 开始的完整帧。

    Returns:
        - DecodeEvent(status=ok/crc_bad)：已得到定界结论；
        - None：比特还不够，需要继续等待。
    """
    need_head = start + FRAME_HEAD_BITS
    if len(bits) < need_head:
        return None
    length = _int_from_bits(bits, start + PREAMBLE_BITS + 8 + 16, 16)
    end = need_head + length * 8 + CRC_BITS
    if len(bits) < end:
        return None

    # CRC 覆盖 Preamble 之后的全部字段：Version/Frame ID/Length/Payload。
    body = bits_to_bytes(bits[start + PREAMBLE_BITS : end - CRC_BITS])
    crc_recv = _int_from_bits(bits, end - CRC_BITS, CRC_BITS)
    version = body[0] >> 4
    frame_id = int.from_bytes(body[1:3], "big")
    payload = body[5:]

    status = "ok" if crc_recv == crc16(body) else "crc_bad"
    return DecodeEvent(
        status=status,
        frame_id=frame_id,
        payload=payload,
        frame_bits=end - start,
    )


def decode_frame(bits: list[int]) -> tuple[bool, bytes, str]:
    """无状态便捷入口：把一段 bit 流交给 FrameDecoder 后取最后一个结果。

    返回值兼容 v0.1 的 ``(ok, payload, status)`` 接口，status 取值：
    waiting / searching / crc_bad / ok。
    """
    decoder = FrameDecoder()
    events: list[DecodeEvent] = []
    for bit in bits:
        events.extend(decoder.push(bit))
    if not events:
        if len(bits) < FRAME_HEAD_BITS + CRC_BITS:
            return False, b"", "waiting"
        return False, b"", "searching"
    last = events[-1]
    if last.status == "ok":
        return True, last.payload, "ok"
    return False, b"", "crc_bad"


class FrameDecoder:
    """滑窗同步解码状态机。

    用法：每一行 cover record 恢复出 1 bit 后调用 ``push(bit)``，
    返回本次新增的解析事件。解码器会在累积 bit 流中搜索 Preamble；
    CRC 失败的事件照常返回，但不会删除 bit，因此可以继续向后重同步。
    """

    def __init__(self) -> None:
        self._bits: list[int] = []
        self._scan_start = 0

    def push(self, bit: int) -> list[DecodeEvent]:
        self._bits.append(1 if bit else 0)
        self._trim()

        events: list[DecodeEvent] = []
        while True:
            idx = self._find_preamble()
            if idx is None:
                break
            event = _parse_frame_at(self._bits, idx)
            if event is None:
                # 找到候选帧头但数据还没到齐，停在原处等更多 bit。
                self._scan_start = idx
                break

            self._scan_start = idx + 1
            if event.status == "ok":
                events.append(event)
                # 有效帧整体移出缓冲；之前与之后的普通 bit 也可以一并丢弃。
                del self._bits[: idx + event.frame_bits]
                self._scan_start = 0
                # 一次 push 理论上最多完成一帧，但保留循环以支持批量喂入。
            else:
                # CRC 失败：记录误码事件，但不破坏后续重同步。
                events.append(event)
        return events

    def _find_preamble(self) -> int | None:
        limit = len(self._bits) - PREAMBLE_BITS
        i = self._scan_start
        while i <= limit:
            if _preamble_at(self._bits, i):
                return i
            i += 1
        self._scan_start = max(0, len(self._bits) - (PREAMBLE_BITS - 1))
        return None

    def _trim(self) -> None:
        overflow = len(self._bits) - MAX_BUFFER_BITS
        if overflow <= 0:
            return
        del self._bits[:overflow]
        self._scan_start = max(0, self._scan_start - overflow)
