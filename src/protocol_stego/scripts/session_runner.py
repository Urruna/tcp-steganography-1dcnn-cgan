"""Run one normal or stego session and write raw session data."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import socket
import threading
import time
from pathlib import Path

import yaml

from core.config import load_config
from core.crypto_adapter import ciphertext_overhead, derive_key
from core.framing import FrameProtocol
from core.modulation import ModulationConfig
from proxy import receiver_stego, sender_stego
from proxy.sender_stego import prepare_secret


def deterministic_bytes(tag: str, size: int) -> bytes:
    """Deterministic pseudo-random bytes for reproducible experiments."""
    out = bytearray()
    counter = 0
    while len(out) < size:
        out.extend(hashlib.sha256(f"{tag}:{counter}".encode()).digest())
        counter += 1
    return bytes(out[:size])


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _free_ports(count: int) -> list[int]:
    ports: list[int] = []
    while len(ports) < count:
        port = _free_port()
        if port not in ports:
            ports.append(port)
    return ports


def _wait_event(event: threading.Event, name: str, timeout: float = 10.0) -> None:
    if not event.wait(timeout):
        raise TimeoutError(f"{name} not ready within {timeout}s")


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


def _client_send(
    host: str,
    port: int,
    payload: bytes,
    chunk_size: int,
    delay_seconds: float,
    result: dict[str, object],
) -> None:
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.settimeout(60)
        for index in range(0, len(payload), chunk_size):
            sock.sendall(payload[index : index + chunk_size])
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        try:
            while sock.recv(65536):
                pass
        except OSError:
            pass
    result.update(sent_bytes=len(payload), sha256=_sha256(payload))


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_session(
    *,
    session_id: str,
    mode: str,
    config: dict[str, object],
    raw_root: str | Path,
) -> dict[str, object]:
    """Execute one session and return its metadata."""
    if mode not in ("normal", "stego"):
        raise ValueError("mode must be normal or stego")
    label = 0 if mode == "normal" else 1
    raw_dir = Path(raw_root) / mode / session_id
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    work_dir = raw_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    project_root = Path(__file__).resolve().parents[1]
    base_config = load_config(project_root / "config.yaml")
    protocol = FrameProtocol.from_config(base_config)
    modulation = ModulationConfig.from_config(base_config)
    block_gap_ms = int(config.get("block_gap_ms", 10))
    secret_size = int(config.get("secret_size", 64))
    normal_chunk_size = int(config.get("normal_chunk_size", 1024))
    random_seed = int(config.get("random_seed", 42))

    port_a, port_b, port_server = _free_ports(3)
    session_config = dict(config)
    session_config.update(
        {
            "session_id": session_id,
            "mode": mode,
            "label": label,
            "project_config_path": "config.yaml",
            "ports": {"proxy_a": port_a, "proxy_b": port_b, "server": port_server},
        }
    )
    effective_config = dict(base_config)
    effective_config["stego"] = dict(base_config["stego"])  # type: ignore[arg-type]
    effective_config["stego"]["block_gap_ms"] = block_gap_ms  # type: ignore[index]
    effective_config_path = raw_dir / "proxy_config.yaml"
    effective_config_path.write_text(
        yaml.safe_dump(effective_config, sort_keys=False),
        encoding="utf-8",
    )

    server_result: dict[str, object] = {}
    client_result: dict[str, object] = {}
    metrics: dict[str, object] = {}
    error_text: str | None = None
    secret: bytes | None = None

    try:
        if mode == "stego":
            secret = deterministic_bytes(
                f"secret:{random_seed}:{session_id}",
                secret_size,
            )
            secret_path = work_dir / "secret.txt"
            secret_path.write_bytes(secret)
            passphrase = f"{random_seed}:{session_id}:newtry97"
            key = derive_key(passphrase)
            key_path = work_dir / "session.key"
            key_path.write_bytes(key)
            prepared = prepare_secret(secret_path, key, protocol, modulation)
            cover = deterministic_bytes(
                f"cover:{random_seed}:{session_id}",
                prepared.required_cover_bytes + 400 * len(prepared.bits) + 4096,
            )
            expected_duration_ms = len(prepared.bits) * block_gap_ms
            client_chunk_size = 4096
            client_delay_s = 0.0
            session_config["key_derivation"] = (
                "PBKDF2-HMAC-SHA256(default salt newtry97-crypto-v1, 200000 iterations)"
            )
            session_config["key_passphrase_pattern"] = "<random_seed>:<session_id>:newtry97"
            session_config["secret_sha256"] = _sha256(secret)
        else:
            ciphertext_bytes = secret_size + ciphertext_overhead()
            frame_bytes = ciphertext_bytes + 11
            total_bits = frame_bytes * 8
            average_length = (modulation.low_length + modulation.high_length) // 2
            cover_size = total_bits * average_length
            cover = deterministic_bytes(
                f"cover:{random_seed}:{session_id}",
                cover_size,
            )
            expected_duration_ms = total_bits * block_gap_ms
            client_chunk_size = normal_chunk_size
            chunks = max(1, math.ceil(len(cover) / client_chunk_size))
            client_delay_s = (expected_duration_ms / chunks) / 1000.0
            session_config["expected_equivalent_bits"] = total_bits
            session_config["cover_sha256"] = _sha256(cover)

        session_config["expected_duration_ms"] = expected_duration_ms
        (raw_dir / "session_config.json").write_text(
            json.dumps(session_config, indent=2) + "\n",
            encoding="utf-8",
        )

        server_ready = threading.Event()
        receiver_ready = threading.Event()
        sender_ready = threading.Event()
        receiver_result: dict[str, object] = {}
        sender_result: dict[str, object] = {}
        server_thread = threading.Thread(
            target=_sink_server,
            args=("127.0.0.1", port_server, server_ready, server_result),
            daemon=True,
        )
        receiver_thread = threading.Thread(
            target=receiver_stego.serve_once,
            kwargs={
                "listen_host": "127.0.0.1",
                "listen_port": port_b,
                "server_host": "127.0.0.1",
                "server_port": port_server,
                "key_path": str(work_dir / "session.key") if mode == "stego" else None,
                "normal_mode": mode == "normal",
                "config_path": str(effective_config_path),
                "log_dir": str(raw_dir),
                "out_dir": str(raw_dir),
                "session_id": session_id,
                "ready_event": receiver_ready,
            },
            daemon=True,
        )
        sender_thread = threading.Thread(
            target=sender_stego.serve_once,
            kwargs={
                "listen_host": "127.0.0.1",
                "listen_port": port_a,
                "upstream_host": "127.0.0.1",
                "upstream_port": port_b,
                "secret_path": str(work_dir / "secret.txt") if mode == "stego" else None,
                "key_path": str(work_dir / "session.key") if mode == "stego" else None,
                "config_path": str(effective_config_path),
                "log_dir": str(raw_dir),
                "out_dir": str(raw_dir),
                "session_id": session_id,
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
            target=_client_send,
            args=(
                "127.0.0.1",
                port_a,
                cover,
                client_chunk_size,
                client_delay_s,
                client_result,
            ),
            daemon=True,
        )
        client_thread.start()
        client_thread.join(timeout=300)
        receiver_thread.join(timeout=300)
        sender_thread.join(timeout=300)
        server_thread.join(timeout=300)
        total_duration_ms = (time.monotonic() - started) * 1000.0
        if any(
            thread.is_alive()
            for thread in (client_thread, receiver_thread, sender_thread, server_thread)
        ):
            raise TimeoutError("session thread did not finish")

        sender_result = _load_json(raw_dir / "sender_result.json")
        receiver_result = _load_json(raw_dir / "receiver_result.json")

        if mode == "stego":
            sent_bits = list(sender_result.get("sender_bits", []))
            recovered_bits = list(receiver_result.get("recovered_bits", []))
            bit_errors = abs(len(sent_bits) - len(recovered_bits)) + sum(
                1 for left, right in zip(sent_bits, recovered_bits) if left != right
            )
            ber = bit_errors / len(sent_bits) if sent_bits else 0.0
            frame_count = int(sender_result.get("frame_count", 0))
            received_frames = len(receiver_result.get("frames", []))
            frame_errors = max(0, frame_count - received_frames)
            fer = frame_errors / frame_count if frame_count else 0.0
            crc_failures = int(receiver_result.get("crc_failures", 0))
            used_cover_bytes = int(sender_result.get("cover_bytes", 0))
            recovered_path = raw_dir / "recovered_secret.txt"
            recovered_secret = (
                recovered_path.read_bytes() if recovered_path.exists() else b""
            )
            plaintext_match = recovered_secret == secret
            cover_match = (
                int(server_result.get("bytes_received", 0)) == used_cover_bytes
                and server_result.get("sha256") == _sha256(cover[:used_cover_bytes])
            )
            success = (
                plaintext_match
                and bit_errors == 0
                and crc_failures == 0
                and frame_errors == 0
                and cover_match
                and not receiver_result.get("error_reason")
            )
            metrics = {
                "total_bits": len(sent_bits),
                "bit_error_count": bit_errors,
                "ber": ber,
                "frame_count": frame_count,
                "received_frame_count": received_frames,
                "frame_error_count": frame_errors,
                "frame_error_rate": fer,
                "crc_failure_count": crc_failures,
                "plaintext_match": plaintext_match,
                "cover_match": cover_match,
                "cover_bytes": used_cover_bytes,
                "ciphertext_bytes": int(sender_result.get("ciphertext_bytes", 0)),
                "duration_ms": total_duration_ms,
                "throughput_secret_Bps": len(secret)
                / (total_duration_ms / 1000.0)
                if total_duration_ms > 0
                else None,
            }
        else:
            cover_match = (
                int(server_result.get("bytes_received", 0)) == len(cover)
                and server_result.get("sha256") == _sha256(cover)
            )
            relay_ok = bool(receiver_result.get("success"))
            success = cover_match and relay_ok
            metrics = {
                "total_bits": None,
                "bit_error_count": None,
                "ber": None,
                "frame_count": None,
                "received_frame_count": None,
                "frame_error_count": None,
                "frame_error_rate": None,
                "crc_failure_count": None,
                "plaintext_match": None,
                "cover_match": cover_match,
                "cover_bytes": len(cover),
                "ciphertext_bytes": None,
                "duration_ms": total_duration_ms,
                "throughput_secret_Bps": None,
            }
    except Exception as exc:  # keep metadata even for failed sessions
        error_text = f"{type(exc).__name__}: {exc}"
        success = False

    if not metrics:
        metrics = {"error_reason": error_text}
    (raw_dir / "server_result.json").write_text(
        json.dumps(server_result, indent=2) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "client_result.json").write_text(
        json.dumps(client_result, indent=2) + "\n",
        encoding="utf-8",
    )

    metadata: dict[str, object] = {
        "session_id": session_id,
        "label": label,
        "mode": mode,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "timestamp_epoch": time.time(),
        "config": session_config,
        "success": success,
        "metrics": metrics,
        "error_reason": error_text,
        "files": {
            "sender_jsonl": "sender.jsonl",
            "receiver_jsonl": "receiver.jsonl",
            "errors_jsonl": "errors.jsonl",
            "sender_result": "sender_result.json",
            "receiver_result": "receiver_result.json",
        },
    }
    (raw_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.rmtree(work_dir, ignore_errors=True)
    return metadata
