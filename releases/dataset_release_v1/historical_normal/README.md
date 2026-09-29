# 历史 Normal 数据

本目录**不属于**当前 protocol_stego 的对照组。

它包含两个界限清晰的历史来源。

## 1. `raw/docker_chain_smoke`

早期 Docker 链的正常流量：

```text
Client → Proxy-A → Proxy-B → Server
```

文件：

- `proxy_a_events.csv`
- `proxy_b_events.csv`

原始文件按字节原样保留。

原始 CSV 后来还被写入了另一种 schema 的行。因此早期 Docker 会话
另外提供了一份规范化视图：

```text
processed/early_docker_normal_events.csv
```

早期 Docker 会话的事实：

- 时间：2026-07-29 14:02:06（CSV 中为 epoch 时间戳）
- 载荷：`hello network`（13 字节）
- Proxy-A 事件：2（正向 + 反向）
- Proxy-B 事件：2（正向 + 反向）
- 无 pcap
- 原始运行没有做特征提取

## 2. `raw/baseline_lenmix_v1`

更早的正常流量基线：

- 1 次实验 / 1 个 session
- 256 个 client 事件，全部 `passed`
- 512 个 Proxy-A 事件（256 正向 + 256 反向）
- 512 个 Proxy-B 事件（256 正向 + 256 反向）
- 长度循环使用 64、128、256、512、1024 字节
- 无调制、无隐藏载荷
- 无 pcap

按项目记录，该来源来自更早的 Ubuntu 20.04 VMware 原生多进程实验，
不是当前的 protocol_stego Docker 对照组。

解析后的摘要位于：

```text
processed/baseline_lenmix_v1_summary.json
```
