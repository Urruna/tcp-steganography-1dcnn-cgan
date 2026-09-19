import asyncio


async def handle_client(reader: asyncio.StreamReader,
                        writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    print(f"[server] client connected: {peer}")

    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break

            print(f"[server] received {len(data)} bytes")
            writer.write(data)
            await writer.drain()

    except ConnectionError as exc:
        print(f"[server] connection error: {exc}")

    finally:
        writer.close()
        await writer.wait_closed()
        print(f"[server] client disconnected: {peer}")


async def main() -> None:
    server = await asyncio.start_server(handle_client, "0.0.0.0", 9003)
    print("[server] listening on 0.0.0.0:9003")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
