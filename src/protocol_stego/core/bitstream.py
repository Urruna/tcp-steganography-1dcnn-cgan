"""Byte/bit conversion helpers with explicit error behaviour."""

from __future__ import annotations


class BitstreamError(ValueError):
    """Raised when a bit sequence cannot be represented as bytes."""


def bytes_to_bits(data: bytes) -> list[int]:
    """Convert bytes to a big-endian bit list.

    ``b"A"`` -> ``[0, 1, 0, 0, 0, 0, 0, 1]``.
    Empty input returns an empty list.
    """
    return [(byte >> shift) & 1 for byte in data for shift in range(7, -1, -1)]


def bits_to_bytes(bits: list[int], *, pad: bool = False) -> bytes:
    """Convert a bit list back to bytes.

    By default the bit length must be a multiple of 8; otherwise
    ``BitstreamError`` is raised.  With ``pad=True`` the final byte is
    zero-padded on the right (least significant bits).
    """
    if not bits:
        return b""
    if any(bit not in (0, 1) for bit in bits):
        raise BitstreamError("bitstream may only contain 0/1")
    if len(bits) % 8 and not pad:
        raise BitstreamError(
            f"bit length must be a multiple of 8, got {len(bits)}"
        )
    padded = list(bits)
    if len(padded) % 8:
        padded.extend([0] * (8 - len(padded) % 8))
    out = bytearray()
    for index in range(0, len(padded), 8):
        value = 0
        for bit in padded[index : index + 8]:
            value = (value << 1) | bit
        out.append(value)
    return bytes(out)


def bits_to_int(bits: list[int]) -> int:
    """Interpret bits as a big-endian unsigned integer."""
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def int_to_bits(value: int, width: int) -> list[int]:
    """Convert an unsigned integer to a fixed-width big-endian bit list."""
    if width < 0:
        raise BitstreamError("width must be >= 0")
    if value < 0 or value >= (1 << width):
        raise BitstreamError(f"value {value} does not fit in {width} bits")
    return [(value >> shift) & 1 for shift in range(width - 1, -1, -1)]
