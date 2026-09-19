# DATA DICTIONARY

## Protocol-Stego Processed Data

### X.npy

- Meaning: fixed-length event windows
- Type: float32
- Shape: `[N, 4, 128]`
- Feature order:
  - channel 0: `direction`
  - channel 1: `length`
  - channel 2: `inter_arrival_time`
  - channel 3: `cumulative_bytes`

### y.npy

- Meaning: window label
- Type: int64
- Shape: `[N]`
- Values: `0 = Normal`, `1 = Stego`

## Fields

| Field | Meaning | Type | Unit | Source | Used by CNN | Stego only | Raw / Processed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `session_id` | Unique id of one complete experiment session | string | - | metadata.json / JSONL | No (tracking only) | No | raw + index |
| `label` | `0=Normal`, `1=Stego` | int | - | metadata.json | Yes (target y) | No | raw + processed index |
| `mode` | `normal` or `stego` | string | - | metadata.json | No | No | raw |
| `timestamp` | Event time | float | seconds | sender/receiver JSONL | Indirectly (gap) | No | raw |
| `direction` | `forward` = client→server, `reverse` = server→client | string/int | - | JSONL; +1/-1 in processed | Yes, channel 0 | No | raw + processed |
| `length` | Observed application-layer event length | int | bytes | receiver.jsonl `observed_length` | Yes, channel 1 | No | raw + processed |
| `inter_arrival_time` | Time since previous event in the same session | float | seconds | computed from timestamp | Yes, channel 2 | No | processed |
| `cumulative_bytes` | Cumulative bytes in the current direction up to this event | int | bytes | computed | Yes, channel 3 | No | processed |
| `target_length` | Proxy-A intended application-layer write length | int | bytes | sender.jsonl | No | Yes | raw |
| `actual_write_length` | Proxy-A actual `sendall()` length | int | bytes | sender.jsonl | Analysis / audit | Yes | raw |
| `observed_length` | Proxy-B actual `recv()` length | int | bytes | receiver.jsonl | Yes (becomes `length`) | Raw also exists in Normal | raw |
| `bit` | Encoded bit before modulation | int | 0/1 | sender.jsonl | No | Yes | raw |
| `frame_id` | Protocol frame id | int | - | sender/receiver | No | Yes | raw |
| `crc_status` | Frame CRC status | string | - | receiver.jsonl | No | Yes | raw |

## Important Distinction

`actual_write_length` and `observed_length` are stored separately.

```text
Proxy-A sendall length  !=  necessarily equal to
Proxy-B recv length
```

TCP may segment, coalesce, or buffer. The processed feature `length` uses
`observed_length`, not `actual_write_length`.

## Historical Normal Fields

Historical data is CSV, not the JSONL schema above. Fields are:

```text
timestamp, proxy_name, session_id, direction, event_index,
byte_length, inter_event_gap_ms
```

and for `baseline_lenmix_v1` additionally:

```text
experiment_id
```
