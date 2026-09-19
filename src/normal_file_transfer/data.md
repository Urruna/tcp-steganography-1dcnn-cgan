# Normal 数据集采集记录

日期：2026-09-17

## 0 项目目标

本项目研究代理转发场景下的 TCP 流量特征调制与可检测性：业务字节保持正常，
仅通过应用层写入分块与时间节奏承载秘密信息，并用 1D-CNN/cGAN 评估可靠性与
可检测性。

依据 `new_727.pdf` 的数据集设计，至少需要三类流量：

| 类别 | 含义 | 作用 |
| --- | --- | --- |
| Normal | 正常代理转发流量，无秘密数据 | 检测器负样本 |
| Baseline-Stego | 基础规则调制后的流量 | 评估基础方案 |
| GAN-Stego | cGAN 优化后的调制流量 | 评估改进效果 |

本次任务：先完成 **Normal（无秘密数据）** 数据集采集。

## 1 采集目标

- 构造 `Client → Proxy-A → Proxy-B → Server` 的正常文件下载业务；
- 全程不进行任何隐蔽编码、不改变业务字节；
- 记录 Proxy-A、Proxy-B、Client、Server 四侧事件；
- 后续可按固定窗口（64/128 事件）截取序列特征：
  方向、数据块长度、相邻事件间隔、累计字节数。

## 2 实验设计

拓扑：

```text
client ──client_net──> proxy_a ──backbone_net──> proxy_b ──server_net──> server
```

业务：Client 通过代理链向文件服务请求文件。

本次选择的文件内容由 `make_files.py` 确定性生成：

| 文件 | 大小 | 内容 |
| --- | --- | --- |
| `report_small.txt` | 64 KiB | 带序号与固定 payload 的文本记录行 |
| `report_medium.txt` | 256 KiB | 同上，记录数更多 |
| `report_large.bin` | 1 MiB | 固定种子生成的二进制数据 |

`manifest.json` 记录三个文件的字节数与 SHA-256，便于校验传输完整性。

Client 默认执行 8 次下载，文件循环选择：

```text
small → medium → large → small → medium → large → small → medium
```

每次下载使用新的 TCP 连接，间隔 0.5 s。

## 3 采集代码与日志

项目文件：

```text
normal/
├── Dockerfile
├── compose.yaml
├── normal_proxy.py      # 普通透明转发代理（线程版）+ CSV 事件日志
├── file_server.py       # HTTP 文件服务 + 服务端事件日志
├── file_client.py       # 正常下载客户端 + 客户端事件日志
├── make_files.py        # 生成测试文件与 manifest
├── summarize_dataset.py # 汇总日志
└── data.md
```

运行后产出：

```text
normal/
├── files/               # 测试文件与 manifest
├── downloads/           # Client 下载结果
└── logs/
    ├── proxy_a_events.csv
    ├── proxy_b_events.csv
    ├── client_events.csv
    ├── server_events.csv
    └── dataset_summary.json
```

代理日志字段与 `baseline_lenmix_v1/*.csv` 一致：

```text
timestamp,proxy_name,experiment_id,session_id,direction,
event_index,byte_length,inter_event_gap_ms
```

## 4 执行步骤

```bash
cd /home/urruna/docker/tcp-lab/normal
docker compose build
docker compose up --abort-on-container-exit --exit-code-from client
python3 summarize_dataset.py   # 或在宿主机用容器运行汇总脚本
docker compose down
```

## 5 实测结果

实际执行时间：2026-09-17。

### 5.1 业务结果

8 次下载全部成功，客户端校验结果：

| session | 文件 | 状态 | 字节数 | 耗时 ms | 校验 |
| --- | --- | --- | ---: | ---: | --- |
| 0 | `/report_small.txt` | 200 | 65536 | 63.954 | SHA-256 ok |
| 1 | `/report_medium.txt` | 200 | 262144 | 40.844 | SHA-256 ok |
| 2 | `/report_large.bin` | 200 | 1048576 | 159.541 | SHA-256 ok |
| 3 | `/report_small.txt` | 200 | 65536 | 26.522 | SHA-256 ok |
| 4 | `/report_medium.txt` | 200 | 262144 | 68.609 | SHA-256 ok |
| 5 | `/report_large.bin` | 200 | 1048576 | 117.371 | SHA-256 ok |
| 6 | `/report_small.txt` | 200 | 65536 | 28.425 | SHA-256 ok |
| 7 | `/report_medium.txt` | 200 | 262144 | 48.696 | SHA-256 ok |

### 5.2 事件日志统计

| 日志 | 行数 | forward | reverse | sessions | 总字节 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `logs/proxy_a_events.csv` | 771 | 8 | 763 | 8 | 3,082,890 |
| `logs/proxy_b_events.csv` | 773 | 8 | 765 | 8 | 3,082,890 |
| `logs/client_events.csv` | 8 | - | - | 8 | 3,080,192（下载内容） |
| `logs/server_events.csv` | 8 | - | - | 8 | 3,080,192（发送内容） |

说明：

- 正向事件少、反向事件多，符合“请求很小、文件响应很大”的正常下载业务；
- Proxy-A/B 的 `byte_length` 与 `inter_event_gap_ms` 已按事件记录；
- `client_events.csv` 中 `result=ok` 共 8 条，SHA-256 与 `manifest.json` 一致。

### 5.3 遇到的问题与处理

1. `make_files.py` 最初用 `bytearray.extend(bytes)` 生成二进制文件，运行报
   `TypeError`；改为 `random.Random(seed).randbytes(size)` 后正常。
2. 最初使用 `proxy.py` 的 asyncio 转发实现时，服务端已经发送完文件，但
   客户端一直读不到响应并超时；改为线程版 `normal_proxy.py`（阻塞
   `recv/sendall` + 双向线程）后恢复稳定。
3. 客户端最初读到连接 EOF 才结束 body 读取；现在按 HTTP
   `Content-Length` 精确读取，避免依赖连接关闭时序。
4. compose 增加 healthcheck 和 `service_healthy` 依赖，保证
   `server → proxy_b → proxy_a → client` 的启动顺序与就绪状态。

### 5.4 数据集位置

```text
/home/urruna/docker/tcp-lab/normal/
├── files/                 # 测试文件与 manifest.json
├── downloads/             # 客户端下载目录（本次只记录哈希，未保留副本）
└── logs/
    ├── proxy_a_events.csv
    ├── proxy_b_events.csv
    ├── client_events.csv
    ├── server_events.csv
    └── dataset_summary.json
```

## 6 下一步

1. 基于 `logs/*.csv` 写窗口切分脚本，生成 `[样本数, 4, 128]` 数据集；
2. 用同样流程采集 Baseline-Stego；
3. 训练传统基线模型与 1D-CNN，比较 Normal / Baseline-Stego 的检测 AUC/F1。
