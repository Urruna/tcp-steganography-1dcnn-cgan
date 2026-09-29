# 数据字典

## Protocol-Stego 处理后数据

### X.npy

- 含义：定长事件窗口
- 类型：float32
- 形状：`[N, 4, 128]`
- 特征顺序：
  - 通道 0：`direction`
  - 通道 1：`length`
  - 通道 2：`inter_arrival_time`
  - 通道 3：`cumulative_bytes`

### y.npy

- 含义：窗口标签
- 类型：int64
- 形状：`[N]`
- 取值：`0 = Normal`，`1 = Stego`

## 字段说明

| 字段 | 含义 | 类型 | 单位 | 来源 | CNN 是否使用 | 仅 Stego | 原始 / 处理后 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `session_id` | 一次完整实验 session 的唯一标识 | string | - | metadata.json / JSONL | 否（仅用于追踪） | 否 | raw + index |
| `label` | `0=Normal`，`1=Stego` | int | - | metadata.json | 是（作为目标 y） | 否 | raw + processed index |
| `mode` | `normal` 或 `stego` | string | - | metadata.json | 否 | 否 | raw |
| `timestamp` | 事件时间 | float | 秒 | sender/receiver JSONL | 间接（用于间隔） | 否 | raw |
| `direction` | `forward` = client→server，`reverse` = server→client | string/int | - | JSONL；处理后为 +1/-1 | 是，通道 0 | 否 | raw + processed |
| `length` | 观测到的应用层事件长度 | int | 字节 | receiver.jsonl 的 `observed_length` | 是，通道 1 | 否 | raw + processed |
| `inter_arrival_time` | 距同一 session 内上一事件的时间 | float | 秒 | 由 timestamp 计算 | 是，通道 2 | 否 | processed |
| `cumulative_bytes` | 到该事件为止当前方向的累积字节数 | int | 字节 | 计算得到 | 是，通道 3 | 否 | processed |
| `target_length` | Proxy-A 计划的应用层写入长度 | int | 字节 | sender.jsonl | 否 | 是 | raw |
| `actual_write_length` | Proxy-A 实际 `sendall()` 的长度 | int | 字节 | sender.jsonl | 分析 / 审计用 | 是 | raw |
| `observed_length` | Proxy-B 实际 `recv()` 读到的长度 | int | 字节 | receiver.jsonl | 是（成为 `length`） | Normal 中也有原始值 | raw |
| `bit` | 调制前要编码的比特 | int | 0/1 | sender.jsonl | 否 | 是 | raw |
| `frame_id` | 协议帧编号 | int | - | sender/receiver | 否 | 是 | raw |
| `crc_status` | 帧 CRC 状态 | string | - | receiver.jsonl | 否 | 是 | raw |

## 重要区分

`actual_write_length` 与 `observed_length` 是分开保存的。

```text
Proxy-A 的 sendall 长度  不一定等于
Proxy-B 的 recv 长度
```

TCP 可能分段、合并或缓冲。处理后的特征 `length` 使用的是
`observed_length`，不是 `actual_write_length`。

## 历史 Normal 数据字段

历史数据是 CSV，不是上面的 JSONL 结构。字段为：

```text
timestamp, proxy_name, session_id, direction, event_index,
byte_length, inter_event_gap_ms
```

`baseline_lenmix_v1` 还额外包含：

```text
experiment_id
```
