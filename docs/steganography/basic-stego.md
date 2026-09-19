# Basic Steganography

## Current Baseline Strategy

```text
bit 0 → target 800 B application-layer write
bit 1 → target 1200 B application-layer write
```

Configuration: `src/protocol_stego/config.yaml`

```yaml
stego:
  low_length: 800
  high_length: 1200
  tolerance: 80
  block_gap_ms: 5
```

Allowed ranges:

```text
LOW:  720–880 B
HIGH: 1120–1280 B
```

## Data Flow

```text
secret data
 → AES-256-GCM
 → ciphertext
 → Frame encode
 → bitstream
 → bit
 → choose target write length
 → Proxy-A sendall()
```

## Proxy-A

`src/protocol_stego/proxy/sender_stego.py`

For each bit:

1. `bit_to_target_length()`;
2. read exactly target bytes from the cover stream;
3. `upstream.sendall(block)`;
4. log `target_length`, `actual_write_length`, `bit`, `frame_id`.

## Proxy-B

`src/protocol_stego/proxy/receiver_stego.py`

1. `_read_modulated_block()` accumulates recv bytes;
2. `length_to_bit()` recovers bit;
3. bitstream → bytes;
4. frame decode + CRC;
5. reassembly;
6. AES-GCM decrypt.

## Logs

JSONL:

```text
sender.jsonl
receiver.jsonl
errors.jsonl
```

## Actual Validation

From 23 Stego sessions:

| Item | Value |
| --- | ---: |
| target 800 / 1200 | 5654 / 4834 |
| bit 0 / 1 | 5654 / 4834 |
| observed 800 / 1200 | 5654 / 4834 |
| actual == target | 1.0 |
| actual == observed | 1.0 |
| BER | 0.0 |
| frame error rate | 0.0 |
| CRC failure rate | 0.0 |

## Important Boundary

The code controls **application-layer write length**.

It does not directly control TCP packet length; TCP segmentation or
coalescing may change what the receiver observes.

## Limitations

- block-boundary assumption;
- no FEC;
- no retransmission;
- fixed 800/1200 lengths are easy to detect;
- current Normal data is mostly 1024 B, so the task is comparatively easy.
