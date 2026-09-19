# DATASET 数据集说明

## 1 数据采集架构

```text
Client
  → Proxy-A （normal: 正常中继 / stego: 800/1200 长度调制）
  → Proxy-B （normal: 正常中继 / stego: 长度恢复 + 解帧 + 重组 + 解密）
  → Server（只接收业务字节）
```

每次完整实验定义一个 **session**，输出到：

```text
dataset/raw/<mode>/<session_id>/
├── metadata.json
├── session_config.json
├── proxy_config.yaml
├── sender.jsonl
├── receiver.jsonl
├── errors.jsonl
├── sender_result.json
├── receiver_result.json
├── server_result.json
└── client_result.json
```

## 2 Normal / Stego 定义

| 类别 | label | 定义 |
| --- | ---: | --- |
| Normal | 0 | 只做正常 application-layer 转发，不做 800/1200 bit 调制 |
| Stego | 1 | 使用现有 800/1200 长度调制承载加密 secret |

Normal 不是“去掉 label 的 Stego”。两种模式使用相同的：

- Docker/进程拓扑；
- Client / Proxy-A / Proxy-B / Server 角色；
- cover 数据量级与 session 时长目标；
- 日志与数据结构。

区别只在 Proxy-A/B 是否执行 bit 调制与解码。

## 3 Session 数据格式

`metadata.json`：

```json
{
  "session_id": "stego_000001",
  "label": 1,
  "mode": "stego",
  "timestamp": "2026-09-19T...",
  "config": {},
  "success": true,
  "metrics": {}
}
```

`config` 记录该 session 实际使用的参数（含 ports、random_seed、
block_gap_ms、secret_size、window_size）。

`label` 只能是 0 或 1。

## 4 JSONL 数据格式

`sender.jsonl`（Proxy-A 侧）：

```json
{"timestamp": 178..., "session_id": "stego_000001", "event": "write",
 "frame_id": 0, "bit": 0, "target_length": 800,
 "actual_write_length": 800, "direction": "forward", "error": null}
```

`receiver.jsonl`（Proxy-B 侧）：

```json
{"timestamp": 178..., "session_id": "stego_000001", "event": "read",
 "direction": "forward", "observed_length": 800,
 "recovered_bit": 0, "frame_id": null, "crc_status": null,
 "error_reason": null}
```

Normal session 的 `receiver.jsonl` 使用相同字段，但 `recovered_bit` 为 null。

`errors.jsonl` 记录：

- `length_out_of_range`
- `CRCMismatchError`
- `authentication failed`
- `relay_error`

## 5 关键字段：actual_write_length vs observed_length

- `actual_write_length`：Proxy-A 一次 `sendall()` 实际写入的字节数；
- `observed_length`：Proxy-B 一次实际 `recv()` 观察到的字节数；
- TCP 可能 segmentation / coalescing / buffering；

因此：

```text
actual_write_length != observed_length 是允许的
target_length      != observed_length 也是允许的
```

数据集必须分别保留这两个字段，本实现没有互相替代。

## 6 特征定义

第一版每个 event 使用 4 个特征：

| feature | 定义 |
| --- | --- |
| direction | client→server = +1，server→client = -1 |
| length | 当前 event 的 observed_length |
| inter_arrival_time | 当前 event 与前一 event 的 timestamp 差 |
| cumulative_bytes | 当前方向累计字节数 |

数据集构建器只使用 `receiver.jsonl` 的 `observed_length`，不会用
`actual_write_length` 冒充 observed length。

## 7 Window 定义

- `window_size = 128`（配置可改）；
- 每个 session 独立切窗口，不跨 session；
- 只使用完整 128-event 窗口；
- 保存 `session_id` / `window_id` / `label`。

W 个窗口，每个窗口产生：

```text
X.shape = [N, 4, 128]
y.shape = [N]
```

## 8 Train / Val / Test 划分

划分单位是 **session**，不是 window：

```text
80% sessions → train
10% sessions → val
10% sessions → test
```

程序自动检查：

```text
train.session_id ∩ val.session_id = ∅
train.session_id ∩ test.session_id = ∅
val.session_id ∩ test.session_id = ∅
```

这样避免同一 session 的 window 同时进入训练和测试，防止 data leakage。

## 9 统计指标

`dataset_stats.py` 输出：

- session 数量、normal/stego 数量；
- event 数量与 sample 数量；
- class distribution；
- length mean/std/min/max；
- inter-arrival mean/std；
- 每个 session 的 event 数与总 bytes；
- Stego only：BER、frame error rate、CRC failure count；
- Normal 的 BER/CRC/FER 标记为 N/A。

## 10 当前已知限制

1. 当前最小实验只使用 client→server 方向，direction 特征在 Normal/Stego
   中可能接近常数；后续接入正常 HTTP 双向业务后会更有区分度。
2. Normal 模式使用 1024 B 正常写块，Stego 使用 800/1200 B 调制写块；
   两者业务规模接近但不完全相同。
3. `session_duration` 目前用于目标时长记录和 Normal 节流估算，实际时长以
   `metrics.duration_ms` 为准。
4. TCP 合并可能导致 stego 恢复失败，日志会记录
   `length_out_of_range`；第一版不做重传/FEC。
5. 数据集标签来自 session mode，不从流量内容反向推断。
