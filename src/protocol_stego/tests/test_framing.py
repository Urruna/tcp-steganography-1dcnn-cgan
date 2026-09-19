from __future__ import annotations

import unittest

from core.config import load_config
from core.framing import (
    CRCMismatchError,
    FrameProtocol,
    IncompleteFrameError,
    InvalidPayloadLengthError,
    PreambleNotFoundError,
    UnsupportedVersionError,
    decode_frame,
    encode_frame,
)


class FramingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = FrameProtocol.from_config(load_config())

    def test_test2_hello_roundtrip(self) -> None:
        frame_bytes = encode_frame(b"HELLO", frame_id=7, protocol=self.protocol)
        frame = decode_frame(frame_bytes, protocol=self.protocol)
        self.assertEqual(frame.payload, b"HELLO")
        self.assertEqual(frame.frame_id, 7)
        self.assertEqual(frame.version, 1)

    def test_test5_crc_failure(self) -> None:
        frame_bytes = bytearray(encode_frame(b"HELLO", frame_id=0, protocol=self.protocol))
        frame_bytes[-1] ^= 0x01
        with self.assertRaises(CRCMismatchError):
            decode_frame(bytes(frame_bytes), protocol=self.protocol)

    def test_preamble_error(self) -> None:
        with self.assertRaises(PreambleNotFoundError):
            decode_frame(b"no frame here", protocol=self.protocol)

    def test_version_error(self) -> None:
        frame_bytes = bytearray(encode_frame(b"HELLO", frame_id=0, protocol=self.protocol))
        frame_bytes[4] = 0x20
        with self.assertRaises(UnsupportedVersionError):
            decode_frame(bytes(frame_bytes), protocol=self.protocol)

    def test_invalid_payload_length(self) -> None:
        frame_bytes = bytearray(encode_frame(b"HELLO", frame_id=0, protocol=self.protocol))
        frame_bytes[7:9] = (self.protocol.max_payload_size + 1).to_bytes(2, "big")
        with self.assertRaises(InvalidPayloadLengthError):
            decode_frame(bytes(frame_bytes), protocol=self.protocol)

    def test_incomplete_frame(self) -> None:
        frame_bytes = encode_frame(b"HELLO", frame_id=0, protocol=self.protocol)
        with self.assertRaises(IncompleteFrameError):
            decode_frame(frame_bytes[:-1], protocol=self.protocol)


if __name__ == "__main__":
    unittest.main()
