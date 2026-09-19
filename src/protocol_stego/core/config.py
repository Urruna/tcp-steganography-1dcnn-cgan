"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"

DEFAULT_CONFIG: dict[str, object] = {
    "protocol": {
        "version": 1,
        "preamble": 0x6E9797A1,
        "max_payload_size": 512,
        "frame_id_max": 65535,
        "crc": "crc16-xmodem",
    },
    "stego": {
        "low_length": 800,
        "high_length": 1200,
        "tolerance": 80,
        "block_gap_ms": 5,
        "recv_buffer": 4096,
    },
    "logging": {"enabled": True, "dir": "logs"},
    "demo": {"secret_size": 64, "cover_seed": 917},
}


def _merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = value
    return result


def load_config(path: str | Path | None = None) -> dict[str, object]:
    """Load YAML config and merge it onto defaults."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data: dict = {}
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = _merge(DEFAULT_CONFIG, data)
    validate_config(config)
    return config


def validate_config(config: dict[str, object]) -> None:
    protocol = config["protocol"]
    stego = config["stego"]
    assert isinstance(protocol, dict)
    assert isinstance(stego, dict)

    max_payload = int(protocol["max_payload_size"])
    if not 0 < max_payload <= 65535:
        raise ValueError("protocol.max_payload_size must be in 1..65535")
    version = int(protocol["version"])
    if not 0 <= version <= 0x0F:
        raise ValueError("protocol.version must fit in 4 bits")

    low = int(stego["low_length"])
    high = int(stego["high_length"])
    tolerance = int(stego["tolerance"])
    if low <= 0 or high <= 0 or tolerance < 0:
        raise ValueError("stego lengths must be positive and tolerance >= 0")
    if low + tolerance >= high - tolerance:
        raise ValueError("stego low/high ranges overlap; adjust tolerance")
    if int(stego["block_gap_ms"]) < 0:
        raise ValueError("stego.block_gap_ms must be >= 0")
