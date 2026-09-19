from __future__ import annotations

import unittest

from core.config import load_config
from core.framing import (
    FrameProtocol,
    FrameStreamDecoder,
    decode_frame,
    encode_frame,
    frames_complete,
    split_payload,
)
from core.reassembly import ReassemblyError, reassemble_frames


class ReassemblyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = FrameProtocol.from_config(load_config())

    def test_test3_multi_frame_roundtrip(self) -> None:
        ciphertext = bytes(index % 256 for index in range(2000))
        payloads = split_payload(ciphertext, self.protocol.max_payload_size)
        frame_bytes = b"".join(
            encode_frame(payload, frame_id=index, protocol=self.protocol)
            for index, payload in enumerate(payloads)
        )
        decoder = FrameStreamDecoder(self.protocol)
        frames = []
        for offset in range(0, len(frame_bytes), 97):
            frames.extend(decoder.feed(frame_bytes[offset : offset + 97]))
        self.assertTrue(frames_complete(frames, self.protocol.max_payload_size))
        result = reassemble_frames(frames, strict=True)
        self.assertEqual(result.ciphertext, ciphertext)
        self.assertEqual(result.errors, [])

    def test_exact_multiple_uses_terminator(self) -> None:
        ciphertext = b"x" * (self.protocol.max_payload_size * 2)
        payloads = split_payload(ciphertext, self.protocol.max_payload_size)
        self.assertEqual(payloads[-1], b"")

    def test_duplicate_and_missing_frames(self) -> None:
        frame0 = encode_frame(b"a" * 10, frame_id=0, protocol=self.protocol)
        frame1 = encode_frame(b"b" * 10, frame_id=1, protocol=self.protocol)
        f0 = decode_frame(frame0, protocol=self.protocol)
        f1 = decode_frame(frame1, protocol=self.protocol)
        with self.assertRaises(ReassemblyError):
            reassemble_frames([f0, f0], strict=True)
        with self.assertRaises(ReassemblyError):
            reassemble_frames([f1], strict=True)


if __name__ == "__main__":
    unittest.main()
