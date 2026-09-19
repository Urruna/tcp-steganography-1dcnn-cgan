"""newtry97 加密层：AES-256-GCM + 固定长度填充。

设计目标：
1. 保证 Decrypt(Encrypt(M, K), K) == M；
2. 密文长度只增加固定开销，不产生不可控扩张；
3. 支持固定长度模式，便于后续帧设计与容量计算；
4. 只负责“内容不可读”，不负责“流量不可检测”。

格式：

    | Header(1B) | Flags(1B) | Nonce(12B) | Ciphertext | GCM Tag(16B) |

固定开销 = 1 + 1 + 12 + 16 = 30 字节。
"""

from __future__ import annotations

import hashlib
import os
import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = 1
ALGORITHM_AES_256_GCM = 1
HEADER = (VERSION << 4) | ALGORITHM_AES_256_GCM

FLAG_PADDED = 0x01
NONCE_SIZE = 12
TAG_SIZE = 16
HEADER_SIZE = 2
OVERHEAD = HEADER_SIZE + NONCE_SIZE + TAG_SIZE
KEY_SIZE = 32

DEFAULT_KDF_SALT = b"newtry97-crypto-v1"
DEFAULT_KDF_ITERATIONS = 200_000


class CryptoError(Exception):
    """加解密格式错误、密钥错误或认证失败。"""


def keygen() -> bytes:
    """生成 32 字节随机密钥。"""
    return os.urandom(KEY_SIZE)


def derive_key(
    passphrase: str | bytes,
    salt: bytes = DEFAULT_KDF_SALT,
    iterations: int = DEFAULT_KDF_ITERATIONS,
) -> bytes:
    """从口令派生 32 字节密钥。

    生产环境中 salt 应随会话随机生成并安全传递；本实验为保持密文长度固定，
    默认使用固定 salt，便于复现实验。
    """
    if isinstance(passphrase, str):
        passphrase = passphrase.encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", passphrase, salt, iterations, dklen=KEY_SIZE)


def ciphertext_overhead() -> int:
    """返回固定开销字节数（30）。"""
    return OVERHEAD


def _check_key(key: bytes) -> bytes:
    key = bytes(key)
    if len(key) != KEY_SIZE:
        raise CryptoError(f"key must be {KEY_SIZE} bytes, got {len(key)}")
    return key


def encrypt(
    plaintext: bytes | str,
    key: bytes,
    aad: bytes = b"",
    pad_to: int | None = None,
) -> bytes:
    """加密并返回自包含密文包。

    pad_to 不为空时使用固定长度模式：
    - 明文前加 4 字节长度，再补零到 pad_to 字节；
    - 密文长度恒为 pad_to + 30 字节，适合固定帧容量实验。
    """
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    key = _check_key(key)

    flags = 0
    body = plaintext
    if pad_to is not None:
        if pad_to < len(plaintext) + 4:
            raise CryptoError("pad_to must be >= len(plaintext) + 4")
        body = struct.pack("!I", len(plaintext)) + plaintext
        body = body.ljust(pad_to, b"\x00")
        flags |= FLAG_PADDED

    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, body, aad)
    return bytes([HEADER, flags]) + nonce + ciphertext


def decrypt(blob: bytes, key: bytes, aad: bytes = b"") -> bytes:
    """解密并校验认证标签；密钥错误或内容被篡改都会失败。"""
    key = _check_key(key)
    if len(blob) < OVERHEAD:
        raise CryptoError("ciphertext too short")
    if blob[0] != HEADER:
        raise CryptoError(f"unsupported header: {blob[0]:#x}")
    flags = blob[1]
    if flags & ~FLAG_PADDED:
        raise CryptoError(f"unsupported flags: {flags:#x}")

    nonce = blob[HEADER_SIZE : HEADER_SIZE + NONCE_SIZE]
    ciphertext = blob[HEADER_SIZE + NONCE_SIZE :]
    try:
        body = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise CryptoError("authentication failed") from exc

    if flags & FLAG_PADDED:
        if len(body) < 4:
            raise CryptoError("padded plaintext too short")
        length = struct.unpack("!I", body[:4])[0]
        if length > len(body) - 4:
            raise CryptoError("padded length field out of range")
        body = body[4 : 4 + length]
    return body


def pad_plaintext_size(plaintext_size: int, frame_payload_size: int) -> int:
    """给定明文长度，返回固定长度模式应使用的 pad_to 值。"""
    if frame_payload_size < plaintext_size + 4:
        raise CryptoError("frame payload too small for 4-byte length prefix")
    return frame_payload_size
