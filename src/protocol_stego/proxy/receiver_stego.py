"""Proxy-B: recover bits from block lengths, decode frames and decrypt."""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
import uuid
from pathlib import Path

from core.bitstream import bits_to_int
from core.config import load_config
from core.crypto_adapter import decrypt_secret
from core.framing import (
    FrameProtocol,
    FrameStreamDecoder,
    frames_complete,
)
from core.modulation import ModulationConfig, length_to_bit
from core.reassembly import reassemble_frames
from proxy.jsonl_log import JsonlLogger


class ReceiverError(Exception):
    """Raised when Proxy-B cannot recover a secret payload."""


def _normal_relay(
    source: socket.socket,
    destination: socket.socket,
    *,
    direction: str,
    logger: JsonlLogger,
    error_logger: JsonlLogger,
    counters: dict[str, int],
) -> None:
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            counters[f"bytes_{direction}"] = counters.get(f"bytes_{direction}", 0) + len(data)
            counters[f"events_{direction}"] = counters.get(f"events_{direction}", 0) + 1
            logger.log(
                "read",
                direction=direction,
                observed_length=len(data),
                recovered_bit=None,
                frame_id=None,
                crc_status=None,
                error_reason=None,
            )
            destination.sendall(data)
    except OSError as exc:
        error_logger.log(
            "relay_error",
            direction=direction,
            error_reason=type(exc).__name__,
            detail=str(exc),
        )
        counters["errors"] = counters.get("errors", 0) + 1


def _serve_normal_session(
    from_a: socket.socket,
    to_server: socket.socket,
    *,
    session: str,
    peer: object,
    logger: JsonlLogger,
    error_logger: JsonlLogger,
) -> dict[str, object]:
    counters: dict[str, int] = {}
    result: dict[str, object] = {
        "session_id": session,
        "peer": str(peer),
        "mode": "normal",
        "success": False,
    }
    reverse = threading.Thread(
        target=_normal_relay,
        kwargs={
            "source": to_server,
            "destination": from_a,
            "direction": "reverse",
            "logger": logger,
            "error_logger": error_logger,
            "counters": counters,
        },
        daemon=True,
    )
    reverse.start()
    _normal_relay(
        source=from_a,
        destination=to_server,
        direction="forward",
        logger=logger,
        error_logger=error_logger,
        counters=counters,
    )
    try:
        to_server.shutdown(socket.SHUT_WR)
    except OSError:
        pass
    reverse.join(timeout=5)
    result.update(counters)
    result["forward_events"] = counters.get("events_forward", 0)
    result["reverse_events"] = counters.get("events_reverse", 0)
    result["success"] = counters.get("errors", 0) == 0
    return result


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


def _read_modulated_block(
    sock: socket.socket,
    *,
    recv_buffer: int,
    low_min: int,
    low_max: int,
    high_min: int,
    high_max: int,
    grace_seconds: float = 0.002,
) -> bytes | None:
    """Read one application-layer block.

    TCP may split a target write into multiple recv() events, so we
    accumulate until the buffer falls into a legal LOW/HIGH range.  When the
    buffer is in the LOW range we wait a short grace period: if more bytes
    arrive, the write was actually a HIGH block that got segmented.
    """
    buffer = bytearray()
    while True:
        length = len(buffer)
        if length > high_max:
            return bytes(buffer)
        if high_min <= length <= high_max:
            return bytes(buffer)
        if low_min <= length <= low_max:
            sock.settimeout(grace_seconds)
            try:
                more = sock.recv(recv_buffer)
            except socket.timeout:
                return bytes(buffer)
            if not more:
                return bytes(buffer)
            buffer.extend(more)
            continue
        sock.settimeout(10.0)
        try:
            chunk = sock.recv(recv_buffer)
        except socket.timeout:
            return bytes(buffer) if buffer else None
        if not chunk:
            return bytes(buffer) if buffer else None
        buffer.extend(chunk)


def serve_once(
    *,
    listen_host: str,
    listen_port: int,
    server_host: str,
    server_port: int,
    key_path: str | None = None,
    normal_mode: bool = False,
    config_path: str | None = None,
    log_dir: str = "logs",
    out_dir: str = "out",
    session_id: str | None = None,
    ready_event: "threading.Event | None" = None,
) -> dict[str, object]:
    config = load_config(config_path)
    protocol = FrameProtocol.from_config(config)
    modulation = ModulationConfig.from_config(config)
    recv_buffer = int(config["stego"]["recv_buffer"])  # type: ignore[index]
    session = session_id or str(uuid.uuid4())
    log_root = Path(log_dir)
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    logger = JsonlLogger(log_root / "receiver.jsonl", session, flush_every=32)
    error_logger = JsonlLogger(log_root / "errors.jsonl", session)
    key = Path(key_path).read_bytes() if key_path else None
    if not normal_mode and key is None:
        raise ReceiverError("key_path is required in stego mode")

    listener = _listen(listen_host, listen_port)
    if ready_event is not None:
        ready_event.set()
    logger.log(
        "listen",
        listen=f"{listen_host}:{listen_port}",
        server=f"{server_host}:{server_port}",
    )
    try:
        from_a, peer = listener.accept()
    finally:
        listener.close()
    _set_nodelay(from_a)
    to_server = socket.create_connection((server_host, server_port), timeout=10)
    _set_nodelay(to_server)

    if normal_mode:
        result = _serve_normal_session(
            from_a,
            to_server,
            session=session,
            peer=peer,
            logger=logger,
            error_logger=error_logger,
        )
        (out_root / "receiver_result.json").write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.close()
        error_logger.close()
        try:
            to_server.close()
            from_a.close()
        except OSError:
            pass
        return result

    decoder = FrameStreamDecoder(protocol)
    frames: list = []
    recovered_bits: list[int] = []
    observed_lengths: list[int] = []
    bit_buffer: list[int] = []
    byte_count = 0
    start = time.monotonic()
    result: dict[str, object] | None = None
    error_reason: str | None = None

    try:
        while True:
            chunk = _read_modulated_block(
                from_a,
                recv_buffer=recv_buffer,
                low_min=max(1, modulation.low_range[0]),
                low_max=modulation.low_range[1],
                high_min=modulation.high_range[0],
                high_max=modulation.high_range[1],
            )
            if chunk is None:
                break
            if not chunk:
                break
            observed = len(chunk)
            observed_lengths.append(observed)
            try:
                bit = length_to_bit(observed, modulation)
            except Exception as exc:  # ModulationError
                error_reason = "length_out_of_range"
                error_logger.log(
                    "length_error",
                    observed_length=observed,
                    error_reason=error_reason,
                    detail=str(exc),
                )
                logger.log(
                    "read",
                    direction="forward",
                    observed_length=observed,
                    recovered_bit=None,
                    error_reason=error_reason,
                )
                to_server.sendall(chunk)
                continue

            recovered_bits.append(bit)
            logger.log(
                "read",
                direction="forward",
                observed_length=observed,
                recovered_bit=bit,
                error_reason=None,
            )
            to_server.sendall(chunk)
            bit_buffer.append(bit)
            if len(bit_buffer) == 8:
                value = bits_to_int(bit_buffer)
                bit_buffer = []
                byte_count += 1
                new_frames = decoder.feed(bytes([value]))
                for frame in new_frames:
                    frames.append(frame)
                    logger.log(
                        "frame_decoded",
                        frame_id=frame.frame_id,
                        payload_length=frame.payload_length,
                        crc_status="pass",
                    )
                if frames_complete(frames, protocol.max_payload_size):
                    break

        if not frames:
            raise ReceiverError("no complete frame recovered")
        reassembled = reassemble_frames(frames, strict=True)
        plaintext = decrypt_secret(reassembled.ciphertext, key)
        recovered_path = out_root / "recovered_secret.txt"
        recovered_path.write_bytes(plaintext)
        duration_ms = (time.monotonic() - start) * 1000.0
        result = {
            "session_id": session,
            "peer": str(peer),
            "recovered_bits": recovered_bits,
            "observed_lengths": observed_lengths,
            "frame_ids": [frame.frame_id for frame in frames],
            "frames": [frame.to_dict() for frame in frames],
            "crc_failures": len(decoder.errors),
            "decoder_errors": decoder.errors,
            "reassembly_errors": reassembled.errors,
            "ciphertext_bytes": len(reassembled.ciphertext),
            "plaintext_bytes": len(plaintext),
            "byte_count": byte_count,
            "duration_ms": duration_ms,
            "recovered_file": str(recovered_path),
        }
        logger.log(
            "receiver_done",
            plaintext_bytes=len(plaintext),
            ciphertext_bytes=len(reassembled.ciphertext),
            frame_count=len(frames),
            crc_failures=len(decoder.errors),
            duration_ms=duration_ms,
        )
    except Exception as exc:
        error_reason = type(exc).__name__
        error_logger.log(
            "receiver_error",
            error_reason=error_reason,
            detail=str(exc),
        )
        result = {
            "session_id": session,
            "peer": str(peer),
            "recovered_bits": recovered_bits,
            "observed_lengths": observed_lengths,
            "frames": [frame.to_dict() for frame in frames],
            "crc_failures": len(decoder.errors),
            "decoder_errors": decoder.errors,
            "error_reason": error_reason,
            "detail": str(exc),
        }
    finally:
        for sock in (to_server, from_a):
            try:
                sock.close()
            except OSError:
                pass

    (out_root / "receiver_result.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.close()
    error_logger.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Proxy-B stego receiver")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=9102)
    parser.add_argument("--server-host", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=9103)
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--config", default=None)
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args()
    while True:
        result = serve_once(
            listen_host=args.listen_host,
            listen_port=args.listen_port,
            server_host=args.server_host,
            server_port=args.server_port,
            key_path=args.key_file,
            config_path=args.config,
            log_dir=args.log_dir,
            out_dir=args.out_dir,
            session_id=args.session_id,
        )
        print(json.dumps(result, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
