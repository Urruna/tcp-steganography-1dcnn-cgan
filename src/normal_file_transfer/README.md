# normal_file_transfer

Docker file-transfer chain used to generate normal traffic.

```text
client → proxy_a → proxy_b → server
```

The server serves:

- `report_small.txt` 64 KiB
- `report_medium.txt` 256 KiB
- `report_large.bin` 1 MiB

The client performs 8 downloads and verifies SHA-256.

Generated data copies are archived in:

```text
datasets/normal_v1/
```

`normal_proxy.py` is the threaded proxy used by the current compose file.
`proxy.py` is an earlier asyncio version kept for historical reference.
