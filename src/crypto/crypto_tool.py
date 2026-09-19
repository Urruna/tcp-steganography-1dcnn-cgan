"""加密层命令行工具与自检。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from crypto import (
    CryptoError,
    ciphertext_overhead,
    decrypt,
    derive_key,
    encrypt,
    keygen,
)


def _read_key(path: str) -> bytes:
    return Path(path).read_bytes()


def cmd_keygen(args: argparse.Namespace) -> int:
    key = keygen()
    if args.hex:
        print(key.hex())
        return 0
    path = Path(args.out or "secret.key")
    path.write_bytes(key)
    path.chmod(0o600)
    print(f"[keygen] wrote {path} ({len(key)} bytes)")
    return 0


def cmd_derive_key(args: argparse.Namespace) -> int:
    key = derive_key(args.passphrase)
    path = Path(args.out or "secret.key")
    path.write_bytes(key)
    path.chmod(0o600)
    print(f"[derive-key] wrote {path} ({len(key)} bytes)")
    return 0


def cmd_encrypt(args: argparse.Namespace) -> int:
    key = _read_key(args.key_file)
    plaintext = Path(args.input).read_bytes()
    blob = encrypt(
        plaintext,
        key,
        aad=args.aad.encode("utf-8"),
        pad_to=args.pad_to,
    )
    out = Path(args.output)
    out.write_bytes(blob)
    print(
        f"[encrypt] {args.input} -> {out} "
        f"plaintext={len(plaintext)} ciphertext={len(blob)} "
        f"overhead={len(blob) - len(plaintext)}"
    )
    return 0


def cmd_decrypt(args: argparse.Namespace) -> int:
    key = _read_key(args.key_file)
    plaintext = decrypt(
        Path(args.input).read_bytes(),
        key,
        aad=args.aad.encode("utf-8"),
    )
    out = Path(args.output)
    out.write_bytes(plaintext)
    print(f"[decrypt] {args.input} -> {out} plaintext={len(plaintext)}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    key = keygen()
    key_path = Path(args.key_file) if args.key_file else out_dir / "demo.key"
    key_path.write_bytes(key)
    key_path.chmod(0o600)

    samples = {
        "hello.txt": b"HELLO",
        "secret28.txt": b"Hello from A to B (newtry97)",
        "empty.bin": b"",
    }
    for name, plaintext in samples.items():
        normal = encrypt(plaintext, key)
        padded = encrypt(plaintext, key, pad_to=64)
        (out_dir / f"{name}.enc").write_bytes(normal)
        (out_dir / f"{name}.padded.enc").write_bytes(padded)
        assert decrypt(normal, key) == plaintext
        assert decrypt(padded, key) == plaintext
        print(
            f"[demo] {name}: plaintext={len(plaintext)} "
            f"normal={len(normal)} padded={len(padded)}"
        )
    print(f"[demo] key={key_path} out_dir={out_dir}")
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    import random

    rng = random.Random(args.seed)
    key = keygen()
    rounds = 0
    padded_ok = False
    tamper_detected = False
    wrong_key_detected = False

    for _ in range(args.iterations):
        size = rng.randrange(0, args.max_size + 1)
        plaintext = rng.randbytes(size)
        blob = encrypt(plaintext, key)
        if decrypt(blob, key) != plaintext:
            raise SystemExit("roundtrip failed")
        if len(blob) != len(plaintext) + ciphertext_overhead():
            raise SystemExit("overhead check failed")
        rounds += 1

    plaintext = rng.randbytes(100)
    padded = encrypt(plaintext, key, pad_to=512)
    padded_ok = len(padded) == 512 + ciphertext_overhead() and decrypt(padded, key) == plaintext

    tampered = bytearray(encrypt(plaintext, key))
    tampered[-1] ^= 0x01
    try:
        decrypt(bytes(tampered), key)
    except CryptoError:
        tamper_detected = True

    try:
        decrypt(encrypt(plaintext, key), keygen())
    except CryptoError:
        wrong_key_detected = True

    report = {
        "rounds": rounds,
        "overhead_bytes": ciphertext_overhead(),
        "padded_ok": padded_ok,
        "tamper_detected": tamper_detected,
        "wrong_key_detected": wrong_key_detected,
        "passed": padded_ok and tamper_detected and wrong_key_detected,
    }
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="newtry97 crypto tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("keygen", help="generate a random 32-byte key")
    p.add_argument("--out", default=None)
    p.add_argument("--hex", action="store_true")
    p.set_defaults(func=cmd_keygen)

    p = sub.add_parser("derive-key", help="derive a key from passphrase")
    p.add_argument("--passphrase", required=True)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_derive_key)

    p = sub.add_parser("encrypt", help="encrypt a file")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--key-file", required=True)
    p.add_argument("--aad", default="")
    p.add_argument("--pad-to", type=int, default=None)
    p.set_defaults(func=cmd_encrypt)

    p = sub.add_parser("decrypt", help="decrypt a file")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--key-file", required=True)
    p.add_argument("--aad", default="")
    p.set_defaults(func=cmd_decrypt)

    p = sub.add_parser("demo", help="write small sample ciphertexts")
    p.add_argument("--key-file", default=None)
    p.add_argument("--out-dir", default="out")
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("selftest", help="run roundtrip/auth tests")
    p.add_argument("--iterations", type=int, default=200)
    p.add_argument("--max-size", type=int, default=4096)
    p.add_argument("--seed", type=int, default=917)
    p.add_argument("--report", default=None)
    p.set_defaults(func=cmd_selftest)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = args.func(args)
    except CryptoError as exc:
        print(f"[crypto] error: {exc}", file=sys.stderr)
        code = 2
    sys.exit(code)


if __name__ == "__main__":
    main()
