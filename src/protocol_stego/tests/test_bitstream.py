from __future__ import annotations

import unittest

from core.bitstream import BitstreamError, bits_to_bytes, bytes_to_bits


class BitstreamTests(unittest.TestCase):
    def test_test1_bits_to_bytes_to_bits(self) -> None:
        bits = [1, 0, 1, 0, 1, 0, 1, 0]
        self.assertEqual(bits_to_bytes(bits), b"\xaa")
        self.assertEqual(bytes_to_bits(bits_to_bytes(bits)), bits)

    def test_bytes_roundtrip(self) -> None:
        data = bytes(range(256))
        self.assertEqual(bits_to_bytes(bytes_to_bits(data)), data)

    def test_empty(self) -> None:
        self.assertEqual(bytes_to_bits(b""), [])
        self.assertEqual(bits_to_bytes([]), b"")

    def test_non_multiple_of_8_is_explicit(self) -> None:
        with self.assertRaises(BitstreamError):
            bits_to_bytes([1, 0, 1])
        self.assertEqual(bits_to_bytes([1, 0, 1], pad=True), b"\xa0")


if __name__ == "__main__":
    unittest.main()
