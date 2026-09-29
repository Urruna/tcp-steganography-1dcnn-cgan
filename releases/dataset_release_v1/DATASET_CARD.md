# 数据集卡片

> 说明：本卡片描述的是 v1 发布快照（每个类别 23 个 session）。
> 工作数据集此后已扩容到每个类别 233 个 session，
> 见 `docs/experiments/dataset-scaleup-20260926.md`。

## 数据集 A：历史 Docker Normal 数据集

- 名称：`historical_normal/raw/docker_chain_smoke`
- 来源：`/home/urruna/docker/tcp-lab/logs/proxy_a_events.csv` 与
  `proxy_b_events.csv`
- 用途：早期验证 Docker TCP 链
  `Client → Proxy-A → Proxy-B → Server` 能承载正常流量。
- 环境：Ubuntu6.21 虚拟机 + Docker Compose TCP 链
- 流量类型：正常的应用层 TCP 流量，无调制
- 采集方式：早期 Docker 链冒烟测试；载荷为 `hello network`（13 字节）
- 时间：2026-07-29 14:02:06（CSV 中为 epoch 时间戳）
- session：2 个代理侧 session（1 个 Proxy-A、1 个 Proxy-B）
- 事件：共 4 个应用层事件（2 组正反向）
- 可用字段：timestamp、proxy_name、session_id、direction、
  event_index、byte_length、inter_event_gap_ms
- 已知局限：
  - 早期冒烟测试数据，规模极小；
  - 那次运行没有 client / server 的 CSV 日志；
  - 无 pcap；
  - 原始 CSV 后来被写入了另一种 schema 的行；早期行原样保留在 `raw/`，
    并在 `processed/early_docker_normal_events.csv` 中提供规范化视图。

### 补充来源：早期的 `baseline_lenmix_v1`

- 位置：`historical_normal/raw/baseline_lenmix_v1`
- 来源：更早的 TCP-lab 基线实验日志。
- 环境：记录为 Ubuntu 20.04 VMware 原生多进程实验，
  不是当前 protocol_stego 的 Docker 对照组。
- session：1 次实验 / 1 个 session
- 事件：256 个 client 事件；512 个 Proxy-A 事件；512 个 Proxy-B 事件
- 长度：循环使用 64、128、256、512、1024 字节
- client 状态：256 / 256 通过
- 无调制、无秘密载荷
- 无 pcap

该补充来源与数据集 A 明确分开，不得与当前 protocol_stego 数据静默合并。

## 数据集 B-Normal：当前 Protocol-Stego 的 Normal

- 名称：`protocol_stego/raw/normal`
- 来源：当前 protocol_stego 实验，
  `run_experiment.py --mode normal`
- 用途：800/1200 调制检测实验的当前对照组
- 环境：protocol_stego 的类 Docker 进程链
  `Client → Proxy-A → Proxy-B → Server`
- 流量类型：正常的应用层转发，**没有** 800/1200 调制
- 采集方式：1024 字节的普通 cover 写入；session 时长与数据规模目标
  与 Stego 一致
- session：23
- 事件：10258
- 总字节数：10,488,000
- 平均时长：9.3986 s
- 可用字段：timestamp、session_id、direction、observed_length、
  actual_write_length、inter_arrival_time、cumulative_bytes
- 已知局限：
  - 长度基本恒为 1024 字节；
  - `direction` 当前恒为 +1；
  - 正常业务的多样性仍然有限。

## 数据集 B-Stego：当前 Protocol-Stego

- 名称：`protocol_stego/raw/stego`
- 来源：当前带 800/1200 调制的 protocol_stego 实验
- 用途：基线调制检测实验的当前实验组
- 流量类型：正常 cover 流量，通过应用层写入长度调制携带秘密比特流
- 采集方式：
  - 比特 0 → 目标 800 字节
  - 比特 1 → 目标 1200 字节
  - 度量的是应用层写入 / 接收长度，不是 TCP 报文长度
- session：23
- 事件：10488
- 总字节数：10,324,000
- 平均时长：9.4216 s
- 字段：
  - `target_length`
  - `actual_write_length`
  - `observed_length`
  - `bit`
  - `recovered_bit`
  - `frame_id`
  - `crc_status`
- 验证结果：
  - actual == target 比例 = 1.0
  - actual == observed 比例 = 1.0（本次实验运行内成立）
  - BER = 0.0
  - 帧错误率 = 0.0
  - CRC 失败率 = 0.0
- 已知局限：
  - 检测任务被显式的 800/1200 签名主导；
  - `direction` 当前恒为 +1；
  - 这不能代表一般意义上的隐写检测。
