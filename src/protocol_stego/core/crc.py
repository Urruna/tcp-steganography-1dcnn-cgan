"""CRC-16/XMODEM implementation used by the frame protocol."""

from __future__ import annotations


def crc16_xmodem(data: bytes) -> int:
    """Return CRC-16/XMODEM of data."""
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def crc16_bytes_be(data: bytes) -> bytes:
    """Return CRC-16/XMODEM as 2 big-endian bytes."""
    return crc16_xmodem(data).to_bytes(2, "big")
