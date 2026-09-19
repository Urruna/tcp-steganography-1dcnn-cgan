import asyncio
import os


TARGET_HOST = os.getenv("TARGET_HOST", "proxy_a")
TARGET_PORT = int(os.getenv("TARGET_PORT", "9001"))
TEST_MESSAGE = os.getenv("TEST_MESSAGE", "hello network")


async def main() -> None:
    reader, writer = await asyncio.open_connection(
        TARGET_HOST,
        TARGET_PORT,
    )

    payload = TEST_MESSAGE.encode("utf-8")

    print(f"[client] sending: {TEST_MESSAGE}")
    writer.write(payload)
    await writer.drain()

    response = await reader.read(len(payload))
    text = response.decode("utf-8")

    print(f"[client] received: {text}")

    if response == payload:
        print("[client] PASS: returned payload matches sent payload")
    else:
        print("[client] FAIL: returned payload does not match")

    writer.close()
    await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
