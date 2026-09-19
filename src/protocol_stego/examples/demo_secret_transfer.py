"""Minimal end-to-end demo:

Client → Proxy-A → Proxy-B → Server, with AES + framing + length modulation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import socket
import threading
import time
from pathlib import Path

import yaml

from core.config import load_config
from core.crypto_adapter import keygen
from core.framing import FrameProtocol
from core.modulation import ModulationConfig
from proxy import receiver_stego, sender_stego
from proxy.sender_stego import prepare_secret


class DemoError(Exception):
    """Raised when the end-to-end demo cannot complete."""


def _make_secret(size: int) -> bytes:
    if size <= 0:
        raise DemoError("secret_size must be positive")
    prefix = b"authorized-experiment-secret|"
    repeats = (size + len(prefix) - 1) // len(prefix)
    return (prefix * repeats)[:size]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _wait_event(event: threading.Event, name: str, timeout: float = 5.0) -> None:
    if not event.wait(timeout):
        raise DemoError(f"{name} did not become ready within {timeout}s")


def _sink_server(
    host: str,
    port: int,
    ready: threading.Event,
    result: dict[str, object],
) -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(1)
    ready.set()
    conn, _ = listener.accept()
    digest = hashlib.sha256()
    total = 0
    with conn:
        while True:
            data = conn.recv(65536)
            if not data:
                break
            digest.update(data)
            total += len(data)
    listener.close()
    result.update(bytes_received=total, sha256=digest.hexdigest())


def _client_sender(
    host: str,
    port: int,
    cover: bytes,
    result: dict[str, object],
) -> None:
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.settimeout(30)
        sock.sendall(cover)
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        try:
            while sock.recv(65536):
                pass
        except OSError:
            pass
    result.update(sent_bytes=len(cover), sha256=_sha256(cover))


def run_demo(
    *,
    secret_size: int = 64,
    block_gap_ms: int = 10,
    host: str = "127.0.0.1",
    ports: tuple[int, int, int] = (19301, 19302, 19303),
    work_dir: str | Path | None = None,
) -> dict[str, object]:
    root = Path(work_dir) if work_dir else Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    out_dir = root / "out"
    log_dir = root / "logs"
    for directory in (data_dir, out_dir, log_dir):
        directory.mkdir(parents=True, exist_ok=True)

    config = load_config(root / "config.yaml")
    config["stego"]["block_gap_ms"] = block_gap_ms  # type: ignore[index]
    config_path = out_dir / "demo_config.yaml"
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    secret = _make_secret(secret_size)
    secret_path = data_dir / "secret.txt"
    secret_path.write_bytes(secret)
    key_path = out_dir / "demo_key.bin"
    key = keygen()
    key_path.write_bytes(key)

    protocol = FrameProtocol.from_config(config)
    modulation = ModulationConfig.from_config(config)
    prepared = prepare_secret(secret_path, key, protocol, modulation)
    rng = random.Random(int(config["demo"]["cover_seed"]))  # type: ignore[index]
    # Proxy-A performs its own AES-GCM encryption (random nonce), so its
    # actual bit plan can differ from the demo-side estimate.  Send a margin
    # of cover bytes; Proxy-A only consumes what it needs.
    cover = rng.randbytes(prepared.required_cover_bytes + 400 * len(prepared.bits) + 4096)

    port_a, port_b, port_server = ports
    server_ready = threading.Event()
    receiver_ready = threading.Event()
    sender_ready = threading.Event()
    server_result: dict[str, object] = {}
    receiver_result: dict[str, object] = {}
    sender_result: dict[str, object] = {}
    client_result: dict[str, object] = {}

    server_thread = threading.Thread(
        target=_sink_server,
        args=(host, port_server, server_ready, server_result),
        daemon=True,
    )
    receiver_thread = threading.Thread(
        target=receiver_stego.serve_once,
        kwargs={
            "listen_host": host,
            "listen_port": port_b,
            "server_host": host,
            "server_port": port_server,
            "key_path": str(key_path),
            "config_path": str(config_path),
            "log_dir": str(log_dir),
            "out_dir": str(out_dir),
            "session_id": "demo-e2e",
            "ready_event": receiver_ready,
        },
        daemon=True,
    )
    sender_thread = threading.Thread(
        target=sender_stego.serve_once,
        kwargs={
            "listen_host": host,
            "listen_port": port_a,
            "upstream_host": host,
            "upstream_port": port_b,
            "secret_path": str(secret_path),
            "key_path": str(key_path),
            "config_path": str(config_path),
            "log_dir": str(log_dir),
            "out_dir": str(out_dir),
            "session_id": "demo-e2e",
            "ready_event": sender_ready,
        },
        daemon=True,
    )

    server_thread.start()
    _wait_event(server_ready, "server")
    receiver_thread.start()
    _wait_event(receiver_ready, "receiver")
    sender_thread.start()
    _wait_event(sender_ready, "sender")

    started = time.monotonic()
    client_thread = threading.Thread(
        target=_client_sender,
        args=(host, port_a, cover, client_result),
        daemon=True,
    )
    client_thread.start()
    client_thread.join(timeout=60)
    receiver_thread.join(timeout=60)
    sender_thread.join(timeout=60)
    server_thread.join(timeout=60)
    total_duration_ms = (time.monotonic() - started) * 1000.0

    if any(thread.is_alive() for thread in (client_thread, receiver_thread, sender_thread, server_thread)):
        raise DemoError("one or more demo threads did not finish")

    receiver_file = out_dir / "receiver_result.json"
    sender_file = out_dir / "sender_result.json"
    if not receiver_file.exists() or not sender_file.exists():
        raise DemoError("result JSON files were not produced")
    receiver_result = json.loads(receiver_file.read_text(encoding="utf-8"))
    sender_result = json.loads(sender_file.read_text(encoding="utf-8"))

    recovered_path = out_dir / "recovered_secret.txt"
    recovered_secret = recovered_path.read_bytes() if recovered_path.exists() else b""
    recovered_bits = list(receiver_result.get("recovered_bits", []))
    sent_bits = list(sender_result.get("sender_bits", prepared.bits))
    used_cover_bytes = int(sender_result.get("cover_bytes", 0))
    cover_prefix = cover[:used_cover_bytes]
    bit_errors = abs(len(sent_bits) - len(recovered_bits)) + sum(
        1 for left, right in zip(sent_bits, recovered_bits) if left != right
    )
    ber = bit_errors / len(sent_bits) if sent_bits else 0.0
    frame_count = int(sender_result.get("frame_count", len(prepared.frames)))
    received_frames = list(receiver_result.get("frames", []))
    crc_failures = int(receiver_result.get("crc_failures", 0))
    frame_errors = max(0, frame_count - len(received_frames))
    fer = frame_errors / frame_count if frame_count else 0.0

    plaintext_match = recovered_secret == secret
    cover_match = (
        int(server_result.get("bytes_received", 0)) == used_cover_bytes
        and server_result.get("sha256") == _sha256(cover_prefix)
    )
    passed = (
        plaintext_match
        and bit_errors == 0
        and crc_failures == 0
        and frame_errors == 0
        and cover_match
        and not receiver_result.get("error_reason")
    )

    summary: dict[str, object] = {
        "passed": passed,
        "secret_size": len(secret),
        "recovered_size": len(recovered_secret),
        "plaintext_match": plaintext_match,
        "cover_match": cover_match,
        "total_bits": len(sent_bits),
        "bit_error_count": bit_errors,
        "ber": ber,
        "frame_count": frame_count,
        "received_frame_count": len(received_frames),
        "frame_error_count": frame_errors,
        "frame_error_rate": fer,
        "crc_failure_count": crc_failures,
        "ciphertext_bytes": len(prepared.ciphertext),
        "cover_bytes": used_cover_bytes,
        "duration_ms": total_duration_ms,
        "throughput_secret_Bps": len(secret) / (total_duration_ms / 1000.0)
        if total_duration_ms > 0
        else None,
        "sender_duration_ms": sender_result.get("duration_ms"),
        "receiver_error_reason": receiver_result.get("error_reason"),
        "decoder_errors": receiver_result.get("decoder_errors", []),
    }
    (out_dir / "server_result.json").write_text(
        json.dumps(server_result, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "client_result.json").write_text(
        json.dumps(client_result, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "experiment_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"PASS={passed}")
    for key in (
        "total_bits",
        "bit_error_count",
        "ber",
        "frame_count",
        "received_frame_count",
        "crc_failure_count",
        "frame_error_rate",
        "secret_size",
        "recovered_size",
        "duration_ms",
        "throughput_secret_Bps",
    ):
        print(f"{key}={summary[key]}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="end-to-end secret transfer demo")
    parser.add_argument("--secret-size", type=int, default=64)
    parser.add_argument("--block-gap-ms", type=int, default=10)
    parser.add_argument("--work-dir", default=None)
    args = parser.parse_args()
    summary = run_demo(
        secret_size=args.secret_size,
        block_gap_ms=args.block_gap_ms,
        work_dir=args.work_dir,
    )
    raise SystemExit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
