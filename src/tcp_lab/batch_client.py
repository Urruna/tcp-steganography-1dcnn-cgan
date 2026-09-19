import asyncio
import csv
import os
import random
import time
from pathlib import Path


TARGET_HOST = os.getenv("TARGET_HOST", "127.0.0.1")
TARGET_PORT = int(os.getenv("TARGET_PORT", "9001"))

EXPERIMENT_ID = os.getenv("EXPERIMENT_ID", "baseline")
RUN_ID = os.getenv("RUN_ID", "run_00")
EVENT_COUNT = int(os.getenv("EVENT_COUNT", "256"))

# choices：从 MESSAGE_SIZES 中随机选一个长度
# uniform：从 MIN_SIZE 到 MAX_SIZE 中随机选一个长度
SIZE_MODE = os.getenv("SIZE_MODE", "choices")
MESSAGE_SIZES = [
    int(item) for item in os.getenv(
        "MESSAGE_SIZES", "64,128,256,512,1024"
    ).split(",")
]
MIN_SIZE = int(os.getenv("MIN_SIZE", "64"))
MAX_SIZE = int(os.getenv("MAX_SIZE", "1024"))

# fixed：固定间隔
# uniform：在 MIN_INTERVAL_MS 与 MAX_INTERVAL_MS 间随机
INTERVAL_MODE = os.getenv("INTERVAL_MODE", "fixed")
INTERVAL_MS = float(os.getenv("INTERVAL_MS", "20"))
MIN_INTERVAL_MS = float(os.getenv("MIN_INTERVAL_MS", "5"))
MAX_INTERVAL_MS = float(os.getenv("MAX_INTERVAL_MS", "80"))

SEED = int(os.getenv("SEED", "2026"))
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
CLIENT_LOG = LOG_DIR / "client_events.csv"


def prepare_client_log():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not CLIENT_LOG.exists():
        with CLIENT_LOG.open("w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow([
                "timestamp", "experiment_id", "run_id",
                "event_index", "expected_byte_length",
                "interval_ms", "status"
            ])


def write_client_log(index, size, interval_ms, status):
    with CLIENT_LOG.open("a", newline="", encoding="utf-8") as file:
        csv.writer(file).writerow([
            f"{time.time():.6f}", EXPERIMENT_ID, RUN_ID,
            index, size, f"{interval_ms:.3f}", status
        ])


def choose_size(rng):
    if SIZE_MODE == "uniform":
        return rng.randint(MIN_SIZE, MAX_SIZE)
    return rng.choice(MESSAGE_SIZES)


def choose_interval(rng):
    if INTERVAL_MODE == "uniform":
        return rng.uniform(MIN_INTERVAL_MS, MAX_INTERVAL_MS)
    return INTERVAL_MS


async def main():
    prepare_client_log()
    rng = random.Random(SEED)

    reader, writer = await asyncio.open_connection(TARGET_HOST, TARGET_PORT)
    print(f"[client] {RUN_ID}: connected; events={EVENT_COUNT}")

    try:
        for index in range(EVENT_COUNT):
            size = choose_size(rng)
            interval_ms = choose_interval(rng)
            payload = bytes([65 + index % 26]) * size

            writer.write(payload)
            await writer.drain()

            response = await reader.readexactly(size)
            status = "passed" if response == payload else "failed"
            write_client_log(index, size, interval_ms, status)

            if response != payload:
                raise RuntimeError(f"event {index}: echo mismatch")

            await asyncio.sleep(interval_ms / 1000)

        print(f"[client] {RUN_ID}: PASS")

    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
