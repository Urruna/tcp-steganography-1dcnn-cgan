# Dataset Format

## Raw Session Directory

```text
<session>/
├── metadata.json
├── session_config.json
├── proxy_config.yaml
├── sender.jsonl
├── receiver.jsonl
├── errors.jsonl
├── sender_result.json
├── receiver_result.json
├── server_result.json
├── client_result.json
└── recovered_secret.txt      # stego sessions
```

## `metadata.json`

Important fields:

```text
session_id
label         0=Normal, 1=Stego
mode          normal / stego
timestamp
config
success
metrics
error_reason
```

## `sender.jsonl`

One JSON object per application-layer write:

```text
timestamp
session_id
event
frame_id
bit
target_length
actual_write_length
direction
error
```

## `receiver.jsonl`

One JSON object per observed application-layer read:

```text
timestamp
session_id
event
direction
observed_length
recovered_bit
frame_id
crc_status
error_reason
```

For Normal sessions, `recovered_bit`, `frame_id`, `crc_status` are null.

## Processed Files

| File | Type | Shape / Meaning |
| --- | --- | --- |
| `processed/X.npy` | float32 | `[138, 4, 128]` |
| `processed/y.npy` | int64 | `[138]` |
| `processed/windows.npz` | npz | `X` and `y` |
| `processed/index.jsonl` | JSONL | session_id, window_id, label |
| `processed/build_summary.json` | JSON | window summary |
| `processed/stats.json` | JSON | dataset statistics |
| `processed/data_quality_report.json` | JSON | quality audit |
| `processed/baseline_analysis.json` | JSON | baseline metrics |

Feature order:

```text
0 direction
1 length
2 inter_arrival_time
3 cumulative_bytes
```

## Split Files

```text
splits/train.npz / train_index.jsonl
splits/val.npz   / val_index.jsonl
splits/test.npz  / test_index.jsonl
splits/split_manifest.json
```

Do not re-split windows randomly. Use the provided session-level split.
