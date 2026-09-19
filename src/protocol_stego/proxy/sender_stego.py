"""Proxy-A: normal cover forwarding + block-length stego modulation."""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from core.bitstream import bytes_to_bits
from core.config import load_config
from core.crypto_adapter import encrypt_secret
from core.framing import FrameProtocol, encode_frame, split_payload
from core.modulation import ModulationConfig, bit_to_target_length
from proxy.jsonl_log import JsonlLogger


class SenderError(Exception):
    """Raised when Proxy-A cannot complete a secret transmission."""


@dataclass(frozen=True)
class PreparedSecret:
    ciphertext: bytes
    frames: list[bytes]
    frame_bytes: bytes
    bits: list[int]
    bit_frame_ids: list[int]
    required_cover_bytes: int


def prepare_secret(
    secret_path: str | Path,
    key: bytes,
    protocol: FrameProtocol,
    modulation: ModulationConfig,
    *,
    pad_to: int | None = None,
) -> PreparedSecret:
    plaintext = Path(secret_path).read_bytes()
    ciphertext = encrypt_secret(plaintext, key, pad_to=pad_to)
    payloads = split_payload(ciphertext, protocol.max_payload_size)
    frames = [
        encode_frame(payload, frame_id=index, protocol=protocol)
        for index, payload in enumerate(payloads)
    ]
    frame_bytes = b"".join(frames)
    bits = bytes_to_bits(frame_bytes)
    bit_frame_ids: list[int] = []
    for frame_id, frame in enumerate(frames):
        bit_frame_ids.extend([frame_id] * (len(frame) * 8))
    required = sum(bit_to_target_length(bit, modulation) for bit in bits)
    return PreparedSecret(
        ciphertext=ciphertext,
        frames=frames,
        frame_bytes=frame_bytes,
        bits=bits,
        bit_frame_ids=bit_frame_ids,
        required_cover_bytes=required,
    )


def _set_nodelay(sock: socket.socket) -> None:
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass


def _listen(host: str, port: int) -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(1)
    return listener


def _read_exactly(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(65536, size - len(data)))
        if not chunk:
            raise SenderError(
                f"cover stream ended early: need {size}, got {len(data)}"
            )
        data.extend(chunk)
    return bytes(data)


def _transmit_secret(
    client: socket.socket,
    upstream: socket.socket,
    prepared: PreparedSecret,
    modulation: ModulationConfig,
    gap_seconds: float,
    logger: JsonlLogger,
    error_logger: JsonlLogger,
) -> dict[str, object]:
    start = time.monotonic()
    target_lengths: list[int] = []
    actual_lengths: list[int] = []
    try:
        for index, bit in enumerate(prepared.bits):
            target = bit_to_target_length(bit, modulation)
            block = _read_exactly(client, target)
            upstream.sendall(block)
            actual = len(block)
            target_lengths.append(target)
            actual_lengths.append(actual)
            logger.log(
                "write",
                frame_id=prepared.bit_frame_ids[index],
                bit=bit,
                target_length=target,
                actual_write_length=actual,
                direction="forward",
                error=None,
            )
            if gap_seconds > 0:
                time.sleep(gap_seconds)
        try:
            upstream.shutdown(socket.SHUT_WR)
        except OSError:
            pass
    except (OSError, SenderError) as exc:
        error_logger.log(
            "sender_error",
            error_reason=type(exc).__name__,
            detail=str(exc),
        )
        raise
    duration_ms = (time.monotonic() - start) * 1000.0
    cover_bytes = sum(actual_lengths)
    return {
        "session_id": logger.session_id,
        "sent_bits": len(prepared.bits),
        "sender_bits": prepared.bits,
        "ciphertext_bytes": len(prepared.ciphertext),
        "frame_count": len(prepared.frames),
        "frame_bytes": len(prepared.frame_bytes),
        "cover_bytes": cover_bytes,
        "target_lengths": target_lengths,
        "actual_write_lengths": actual_lengths,
        "duration_ms": duration_ms,
        "cover_throughput_Bps": cover_bytes / (duration_ms / 1000.0)
        if duration_ms > 0
        else None,
    }


def _relay_normal(
    client: socket.socket,
    upstream: socket.socket,
    logger: JsonlLogger,
) -> dict[str, object]:
    counters = {"forward": 0, "reverse": 0}

    def relay(source: socket.socket, destination: socket.socket, direction: str) -> None:
        try:
            while True:
                data = source.recv(4096)
                if not data:
                    break
                counters[direction] += len(data)
                logger.log(
                    "relay",
                    direction=direction,
                    actual_write_length=len(data),
                    error=None,
                )
                destination.sendall(data)
        except OSError as exc:
            logger.log("relay_error", direction=direction, error=str(exc))

    thread = threading.Thread(target=relay, args=(upstream, client, "reverse"), daemon=True)
    thread.start()
    relay(client, upstream, "forward")
    try:
        upstream.shutdown(socket.SHUT_WR)
    except OSError:
        pass
    thread.join(timeout=5)
    return {"session_id": logger.session_id, "mode": "normal", **counters}


def serve_once(
    *,
    listen_host: str,
    listen_port: int,
    upstream_host: str,
    upstream_port: int,
    secret_path: str | None,
    key_path: str | None,
    config_path: str | None = None,
    log_dir: str = "logs",
    out_dir: str = "out",
    session_id: str | None = None,
    ready_event: threading.Event | None = None,
) -> dict[str, object]:
    config = load_config(config_path)
    protocol = FrameProtocol.from_config(config)
    modulation = ModulationConfig.from_config(config)
    session = session_id or str(uuid.uuid4())
    log_root = Path(log_dir)
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    logger = JsonlLogger(log_root / "sender.jsonl", session, flush_every=32)
    error_logger = JsonlLogger(log_root / "errors.jsonl", session)
    gap_seconds = int(config["stego"]["block_gap_ms"]) / 1000.0  # type: ignore[index]

    prepared = None
    if secret_path:
        if not key_path:
            raise SenderError("--key-file is required in secret mode")
        key = Path(key_path).read_bytes()
        prepared = prepare_secret(secret_path, key, protocol, modulation)

    listener = _listen(listen_host, listen_port)
    if ready_event is not None:
        ready_event.set()
    logger.log(
        "listen",
        listen=f"{listen_host}:{listen_port}",
        upstream=f"{upstream_host}:{upstream_port}",
    )
    try:
        client, peer = listener.accept()
    finally:
        listener.close()
    _set_nodelay(client)
    upstream = socket.create_connection((upstream_host, upstream_port), timeout=10)
    _set_nodelay(upstream)
    result: dict[str, object]
    try:
        if prepared is None:
            result = _relay_normal(client, upstream, logger)
        else:
            result = _transmit_secret(
                client,
                upstream,
                prepared,
                modulation,
                gap_seconds,
                logger,
                error_logger,
            )
    finally:
        for sock in (upstream, client):
            try:
                sock.close()
            except OSError:
                pass

    result["peer"] = str(peer)
    (out_root / "sender_result.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.log("sender_done", **{k: v for k, v in result.items() if k != "target_lengths" and k != "actual_write_lengths"})
    logger.close()
    error_logger.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Proxy-A stego sender")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=9101)
    parser.add_argument("--upstream-host", default="127.0.0.1")
    parser.add_argument("--upstream-port", type=int, default=9102)
    parser.add_argument("--secret", default=None, help="secret file; omit for normal relay")
    parser.add_argument("--key-file", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args()
    while True:
        result = serve_once(
            listen_host=args.listen_host,
            listen_port=args.listen_port,
            upstream_host=args.upstream_host,
            upstream_port=args.upstream_port,
            secret_path=args.secret,
            key_path=args.key_file,
            config_path=args.config,
            log_dir=args.log_dir,
            out_dir=args.out_dir,
            session_id=args.session_id,
        )
        print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
