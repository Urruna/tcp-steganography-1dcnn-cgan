from __future__ import annotations

import unittest

from examples.demo_secret_transfer import run_demo


class EndToEndTests(unittest.TestCase):
    def test_end_to_end_demo(self) -> None:
        summary = run_demo(
            secret_size=32,
            block_gap_ms=10,
            ports=(19401, 19402, 19403),
        )
        self.assertTrue(summary["passed"], summary)
        self.assertEqual(summary["bit_error_count"], 0)
        self.assertEqual(summary["crc_failure_count"], 0)
        self.assertEqual(summary["frame_error_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
