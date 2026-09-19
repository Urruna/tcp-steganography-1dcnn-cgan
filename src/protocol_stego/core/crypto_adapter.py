"""Adapter for the existing AES-256-GCM module in ../crypto/crypto.py."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType


def _crypto_path() -> Path:
    configured = os.getenv("CRYPTO_MODULE")
    if configured:
        return Path(configured).resolve()
    return (Path(__file__).resolve().parents[2] / "crypto" / "crypto.py").resolve()


def _load_crypto() -> ModuleType:
    path = _crypto_path()
    if not path.exists():
        raise RuntimeError(f"AES module not found: {path}")
    spec = importlib.util.spec_from_file_location("newtry97_aes_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load AES module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def keygen() -> bytes:
    return _load_crypto().keygen()


def derive_key(passphrase: str | bytes) -> bytes:
    return _load_crypto().derive_key(passphrase)


def load_key(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def encrypt_secret(data: bytes, key: bytes, pad_to: int | None = None) -> bytes:
    return _load_crypto().encrypt(data, key, pad_to=pad_to)


def decrypt_secret(blob: bytes, key: bytes) -> bytes:
    return _load_crypto().decrypt(blob, key)


def ciphertext_overhead() -> int:
    return int(_load_crypto().ciphertext_overhead())
