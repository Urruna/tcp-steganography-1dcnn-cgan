from __future__ import annotations

import unittest

from core.crc import crc16_bytes_be, crc16_xmodem


class CRCTests(unittest.TestCase):
    def test_known_vector(self) -> None:
        self.assertEqual(crc16_xmodem(b"123456789"), 0x31C3)

    def test_bytes_be(self) -> None:
        self.assertEqual(crc16_bytes_be(b"123456789"), b"\x31\xc3")

    def test_empty(self) -> None:
        self.assertEqual(crc16_xmodem(b""), 0x0000)


if __name__ == "__main__":
    unittest.main()
