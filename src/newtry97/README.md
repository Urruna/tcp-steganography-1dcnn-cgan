# newtry97

Independent v0.2 frame protocol and write-splitting steganography demo.

Frame format:

```text
Preamble(32 bit) | Version+Reserved(8 bit)
| Frame ID(16 bit) | Payload Length(16 bit)
| Payload | CRC-16(16 bit)
```

Stego strategy:

```text
bit 0 → one write
bit 1 → split into two writes
```

This is different from the 800/1200 length modulation in
`src/protocol_stego/`.

Run:

```bash
python3 run_demo.py
```

Container demo logs from the earlier container run are under
`logs/docker917/`.
