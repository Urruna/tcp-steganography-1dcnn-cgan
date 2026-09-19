"""普通透明 TCP 转发代理：只转发字节并记录应用层事件日志。"""

from __future__ import annotations

import asyncio
import csv
import os
import time
import uuid
from pathlib import Path

PROXY_NAME = os.getenv("PROXY_NAME", "proxy")
LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "9001"))
TARGET_HOST = os.getenv("TARGET_HOST", "localhost")
TARGET_PORT = int(os.getenv("TARGET_PORT", "9002"))
EXPERIMENT_ID = os.getenv("EXPERIMENT_ID", "normal_v1")
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / f"{PROXY_NAME}_events.csv"


def ensure_log_file() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(
                [
                    "timestamp",
                    "proxy_name",
                    "experiment_id",
                    "session_id",
                    "direction",
                    "event_index",
                    "byte_length",
                    "inter_event_gap_ms",
                ]
            )


def write_log(
    session_id: str,
    direction: str,
    event_index: int,
    byte_length: int,
    inter_event_gap_ms: float,
) -> None:
    with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
        csv.writer(file).writerow(
            [
                f"{time.time():.6f}",
                PROXY_NAME,
                EXPERIMENT_ID,
                session_id,
                direction,
                event_index,
                byte_length,
                f"{inter_event_gap_ms:.3f}",
            ]
        )


async def forward(
    source_reader: asyncio.StreamReader,
    destination_writer: asyncio.StreamWriter,
    session_id: str,
    direction: str,
) -> None:
    event_index = 0
    last_event_time = time.monotonic()
    try:
        while True:
            data = await source_reader.read(4096)
            if not data:
                break

            now = time.monotonic()
            gap_ms = (now - last_event_time) * 1000.0
            last_event_time = now
            event_index += 1
            write_log(
                session_id=session_id,
                direction=direction,
                event_index=event_index,
                byte_length=len(data),
                inter_event_gap_ms=gap_ms,
            )

            destination_writer.write(data)
            await destination_writer.drain()
    except (ConnectionError, OSError) as exc:
        print(f"[{PROXY_NAME}] forward error ({direction}): {exc}", flush=True)


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
) -> None:
    session_id = str(uuid.uuid4())
    peer = client_writer.get_extra_info("peername")
    print(f"[{PROXY_NAME}] session {session_id} from {peer}", flush=True)

    try:
        target_reader, target_writer = await asyncio.open_connection(
            TARGET_HOST,
            TARGET_PORT,
        )
        upstream = asyncio.create_task(
            forward(client_reader, target_writer, session_id, "forward")
        )
        downstream = asyncio.create_task(
            forward(target_reader, client_writer, session_id, "reverse")
        )
        await asyncio.gather(upstream, downstream)
    except (ConnectionError, OSError) as exc:
        print(f"[{PROXY_NAME}] connection error: {exc}", flush=True)
    finally:
        client_writer.close()
        try:
            await client_writer.wait_closed()
        except (ConnectionError, OSError):
            pass
        print(f"[{PROXY_NAME}] session closed: {session_id}", flush=True)


async def main() -> None:
    ensure_log_file()
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    print(
        f"[{PROXY_NAME}] listening on {LISTEN_HOST}:{LISTEN_PORT}, "
        f"target={TARGET_HOST}:{TARGET_PORT}",
        flush=True,
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
