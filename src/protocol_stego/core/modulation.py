"""Application-layer block-length modulation."""

from __future__ import annotations

from dataclasses import dataclass


class ModulationError(ValueError):
    """Raised when a bit/length cannot be mapped by the modulation layer."""


@dataclass(frozen=True)
class ModulationConfig:
    low_length: int = 800
    high_length: int = 1200
    tolerance: int = 80

    @classmethod
    def from_config(cls, config: dict[str, object]) -> "ModulationConfig":
        stego = config["stego"]
        assert isinstance(stego, dict)
        return cls(
            low_length=int(stego["low_length"]),
            high_length=int(stego["high_length"]),
            tolerance=int(stego["tolerance"]),
        )

    @property
    def low_range(self) -> tuple[int, int]:
        return (
            self.low_length - self.tolerance,
            self.low_length + self.tolerance,
        )

    @property
    def high_range(self) -> tuple[int, int]:
        return (
            self.high_length - self.tolerance,
            self.high_length + self.tolerance,
        )

    def validate(self) -> None:
        if self.tolerance < 0:
            raise ModulationError("tolerance must be >= 0")
        if self.low_range[1] >= self.high_range[0]:
            raise ModulationError("LOW/HIGH ranges must not overlap")


def bit_to_target_length(bit: int, config: ModulationConfig) -> int:
    """Map 0/1 to the target application-layer block length."""
    config.validate()
    if bit == 0:
        return config.low_length
    if bit == 1:
        return config.high_length
    raise ModulationError(f"bit must be 0 or 1, got {bit!r}")


def length_to_bit(length: int, config: ModulationConfig) -> int:
    """Recover 0/1 from an observed application-layer block length."""
    config.validate()
    low_min, low_max = config.low_range
    high_min, high_max = config.high_range
    if low_min <= length <= low_max:
        return 0
    if high_min <= length <= high_max:
        return 1
    raise ModulationError(
        f"length {length} outside LOW{config.low_range} / HIGH{config.high_range}"
    )


def is_valid_length(length: int, config: ModulationConfig) -> bool:
    try:
        length_to_bit(length, config)
    except ModulationError:
        return False
    return True
