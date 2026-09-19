"""Secret data frame encoding/decoding.

The wire format reuses the field layout and constants of the existing
``newtry97`` v0.2 protocol:

    | Preamble(4B) | Version(1B) | Frame ID(2B) |
    | Payload Length(2B) | Payload | CRC-16(2B) |
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .config import load_config
from .crc import crc16_xmodem

PREAMBLE = 0x6E9797A1
VERSION = 1
FRAME_OVERHEAD = 4 + 1 + 2 + 2 + 2


class FramingError(Exception):
    """Base class for frame errors."""


class PreambleNotFoundError(FramingError):
    """No preamble was found in the supplied bytes."""


class UnsupportedVersionError(FramingError):
    """Version/reserved byte is not supported."""


class InvalidPayloadLengthError(FramingError):
    """Payload length is outside the configured legal range."""


class IncompleteFrameError(FramingError):
    """The supplied bytes do not contain a complete frame."""


class CRCMismatchError(FramingError):
    """CRC verification failed."""


@dataclass(frozen=True)
class FrameProtocol:
    version: int = VERSION
    preamble: int = PREAMBLE
    max_payload_size: int = 512
    frame_id_max: int = 0xFFFF

    @classmethod
    def from_config(cls, config: dict[str, object] | None = None) -> "FrameProtocol":
        cfg = config or load_config()
        protocol = cfg["protocol"]
        assert isinstance(protocol, dict)
        return cls(
            version=int(protocol["version"]),
            preamble=int(protocol["preamble"]),
            max_payload_size=int(protocol["max_payload_size"]),
            frame_id_max=int(protocol["frame_id_max"]),
        )

    def validate(self) -> None:
        if not 0 <= self.version <= 0x0F:
            raise FramingError("version must fit in 4 bits")
        if not 0 <= self.preamble <= 0xFFFFFFFF:
            raise FramingError("preamble must fit in 32 bits")
        if not 0 < self.max_payload_size <= 65535:
            raise FramingError("max_payload_size must be in 1..65535")
        if not 0 <= self.frame_id_max <= 0xFFFF:
            raise FramingError("frame_id_max must fit in 16 bits")

    def preamble_bytes(self) -> bytes:
        return struct.pack("!I", self.preamble)


@dataclass(frozen=True)
class Frame:
    version: int
    frame_id: int
    payload: bytes
    crc: int

    @property
    def payload_length(self) -> int:
        return len(self.payload)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "frame_id": self.frame_id,
            "payload_length": self.payload_length,
            "crc": self.crc,
        }


def _protocol(protocol: FrameProtocol | None) -> FrameProtocol:
    result = protocol or FrameProtocol.from_config()
    result.validate()
    return result


def encode_frame(
    payload: bytes,
    frame_id: int,
    protocol: FrameProtocol | None = None,
) -> bytes:
    """Encode payload into one frame."""
    proto = _protocol(protocol)
    if len(payload) > proto.max_payload_size:
        raise InvalidPayloadLengthError(
            f"payload {len(payload)} > max {proto.max_payload_size}"
        )
    if not 0 <= frame_id <= proto.frame_id_max:
        raise FramingError(f"frame_id {frame_id} out of range")
    version_byte = bytes([(proto.version & 0x0F) << 4])
    body = version_byte + struct.pack("!HH", frame_id, len(payload)) + payload
    crc = crc16_xmodem(body)
    return proto.preamble_bytes() + body + struct.pack("!H", crc)


def _decode_at(data: bytes, start: int, proto: FrameProtocol) -> Frame:
    if len(data) < start + FRAME_OVERHEAD:
        raise IncompleteFrameError("not enough bytes for frame header")
    version_byte = data[start + 4]
    version = version_byte >> 4
    reserved = version_byte & 0x0F
    if version != proto.version or reserved != 0:
        raise UnsupportedVersionError(
            f"version/reserved={version}/{reserved}, expected {proto.version}/0"
        )
    frame_id, length = struct.unpack("!HH", data[start + 5 : start + 9])
    if length > proto.max_payload_size:
        raise InvalidPayloadLengthError(
            f"payload length {length} > max {proto.max_payload_size}"
        )
    total = FRAME_OVERHEAD + length
    if len(data) < start + total:
        raise IncompleteFrameError(
            f"need {total} bytes, got {len(data) - start}"
        )
    payload = data[start + 9 : start + 9 + length]
    body = data[start + 4 : start + 9 + length]
    crc_recv = struct.unpack("!H", data[start + 9 + length : start + total])[0]
    crc_calc = crc16_xmodem(body)
    if crc_recv != crc_calc:
        raise CRCMismatchError(
            f"CRC mismatch: received {crc_recv:#06x}, calculated {crc_calc:#06x}"
        )
    return Frame(version=version, frame_id=frame_id, payload=payload, crc=crc_recv)


def decode_frame(data: bytes, protocol: FrameProtocol | None = None) -> Frame:
    """Find and decode one frame from bytes.

    Raises specific FramingError subclasses for every failure mode.
    """
    proto = _protocol(protocol)
    preamble = proto.preamble_bytes()
    start = data.find(preamble)
    if start < 0:
        raise PreambleNotFoundError("preamble not found")
    return _decode_at(data, start, proto)


class FrameStreamDecoder:
    """Byte-stream frame decoder with resynchronisation after bad frames."""

    def __init__(self, protocol: FrameProtocol | None = None) -> None:
        self.protocol = _protocol(protocol)
        self._buffer = bytearray()
        self.errors: list[dict[str, object]] = []

    def feed(self, data: bytes) -> list[Frame]:
        self._buffer.extend(data)
        frames: list[Frame] = []
        preamble = self.protocol.preamble_bytes()

        while True:
            start = self._buffer.find(preamble)
            if start < 0:
                # Keep a possible partial preamble suffix.
                keep = len(preamble) - 1
                if len(self._buffer) > keep:
                    del self._buffer[:-keep]
                break
            if start > 0:
                del self._buffer[:start]
            if len(self._buffer) < FRAME_OVERHEAD:
                break
            length = struct.unpack("!H", self._buffer[7:9])[0]
            if length > self.protocol.max_payload_size:
                self.errors.append(
                    {
                        "error_reason": "invalid_payload_length",
                        "payload_length": length,
                        "max_payload_size": self.protocol.max_payload_size,
                    }
                )
                del self._buffer[0]
                continue
            total = FRAME_OVERHEAD + length
            if len(self._buffer) < total:
                break
            try:
                frame = _decode_at(bytes(self._buffer), 0, self.protocol)
            except FramingError as exc:
                self.errors.append(
                    {
                        "error_reason": type(exc).__name__,
                        "detail": str(exc),
                    }
                )
                del self._buffer[0]
                continue
            frames.append(frame)
            del self._buffer[:total]
        return frames


def split_payload(payload: bytes, max_payload_size: int) -> list[bytes]:
    """Split ciphertext into frame payloads.

    Convention for the first version: all frames except the final one carry
    exactly ``max_payload_size`` bytes.  If the payload length is an exact
    multiple of ``max_payload_size``, an empty terminating frame is appended
    so the receiver can detect the end of the frame sequence.
    """
    if max_payload_size <= 0:
        raise FramingError("max_payload_size must be positive")
    if not payload:
        return [b""]
    chunks = [
        payload[index : index + max_payload_size]
        for index in range(0, len(payload), max_payload_size)
    ]
    if len(chunks[-1]) == max_payload_size:
        chunks.append(b"")
    return chunks


def frames_complete(frames: list[Frame], max_payload_size: int) -> bool:
    """Return True once the terminating (short) frame has been seen."""
    return bool(frames) and frames[-1].payload_length < max_payload_size
