# 数据集格式

## 原始 session 目录

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
└── recovered_secret.txt      # 仅 stego session
```

## `metadata.json`

主要字段：

```text
session_id
label         0=Normal，1=Stego
mode          normal / stego
timestamp
config
success
metrics
error_reason
```

## `sender.jsonl`

每次应用层写入对应一条 JSON 记录：

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

每次观测到的应用层读取对应一条 JSON 记录：

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

Normal session 中，`recovered_bit`、`frame_id`、`crc_status` 均为 null。

## 处理后文件

| 文件 | 类型 | 形状 / 含义 |
| --- | --- | --- |
| `processed/X.npy` | float32 | `[1398, 4, 128]`（该文件在发布包中） |
| `processed/y.npy` | int64 | `[1398]`（该文件在发布包中） |
| `processed/windows.npz` | npz | 含 `X` 与 `y` |
| `processed/index.jsonl` | JSONL | session_id、window_id、label |
| `processed/build_summary.json` | JSON | 窗口汇总 |
| `processed/stats.json` | JSON | 数据集统计 |
| `processed/data_quality_report.json` | JSON | 质量审计（约 199 MB，不入库） |
| `processed/baseline_analysis.json` | JSON | 基线指标 |

特征顺序：

```text
0 direction
1 length
2 inter_arrival_time
3 cumulative_bytes
```

## 划分文件

```text
splits/train.npz / train_index.jsonl
splits/val.npz   / val_index.jsonl
splits/test.npz  / test_index.jsonl
splits/split_manifest.json
```

不要随机重划分窗口，请使用仓库提供的 session 级划分。
