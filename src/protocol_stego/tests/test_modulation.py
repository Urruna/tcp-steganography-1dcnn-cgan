from __future__ import annotations

import unittest

from core.config import load_config
from core.modulation import (
    ModulationConfig,
    ModulationError,
    bit_to_target_length,
    length_to_bit,
)


class ModulationTests(unittest.TestCase):
    def test_test4_bits_to_lengths_to_bits(self) -> None:
        cfg = ModulationConfig.from_config(load_config())
        bits = [1, 0, 1, 0, 1]
        lengths = [bit_to_target_length(bit, cfg) for bit in bits]
        self.assertEqual(lengths, [1200, 800, 1200, 800, 1200])
        self.assertEqual([length_to_bit(length, cfg) for length in lengths], bits)

    def test_tolerance_ranges(self) -> None:
        cfg = ModulationConfig.from_config(load_config())
        self.assertEqual(length_to_bit(720, cfg), 0)
        self.assertEqual(length_to_bit(880, cfg), 0)
        self.assertEqual(length_to_bit(1120, cfg), 1)
        self.assertEqual(length_to_bit(1280, cfg), 1)
        with self.assertRaises(ModulationError):
            length_to_bit(1000, cfg)

    def test_overlapping_ranges_are_rejected(self) -> None:
        cfg = ModulationConfig(low_length=800, high_length=900, tolerance=80)
        with self.assertRaises(ModulationError):
            cfg.validate()


if __name__ == "__main__":
    unittest.main()
