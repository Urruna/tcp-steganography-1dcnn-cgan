# PROJECT_AUDIT

审计范围：

- Ubuntu6.21 虚拟机 `/home/urruna/docker/tcp-lab`
- Windows 本地 `D:\C\work_DC`

审计原则：只读取和汇总，不修改、不删除、不移动任何现有代码或数据。

说明：用户描述中的 `~/tcp-lab` **实际不存在**。虚拟机里的实际项目路径是
`/home/urruna/docker/tcp-lab`。

---

# 1. 项目当前状态

当前项目已经形成两条工程线：

1. **基础通信线**：Docker 多容器 TCP/文件传输链路，以及后续的
   `protocol_stego` 单容器多进程实验链。
2. **协议与基础隐写线**：
   - 已实现 AES-256-GCM；
   - 已实现 Frame / CRC / bitstream；
   - 已实现 application-layer write length 的 800/1200 基础隐写；
   - 已采集并处理 Normal / Stego 数据集；
   - 已有 rule-based 和 Logistic Regression baseline。

当前明确**没有**实现：

- 1D-CNN
- cGAN
- GAN-Stego 数据生成
- FEC / 重传
- pcap 数据采集

当前最新的数据质量结论是 `READY_FOR_CNN`，但这只表示数据格式和基础实验条件
满足第一轮 CNN 实验，不表示 CNN 已经完成。

---

# 2. 项目架构

## 2.1 `new_727.md` 中明确写出的设计

文档明确写出的内容：

- 研究目标：代理转发场景下的 TCP 流量特征调制、秘密数据可靠传输与可检测性评估。
- 方法：1D-CNN 检测器 + cGAN 特征优化。
- 节点：Client、Proxy-A、Proxy-B、Server、Analysis。
- 业务示例：下载文本文件。
- 调制思路：Proxy-A 控制应用层数据块写入长度，例如约 800 B / 1200 B。
- Proxy-B 根据观察到的块长度恢复 0/1。
- 数据集：Normal、Baseline-Stego、GAN-Stego。
- 特征建议：方向、数据块长度、相邻发送间隔、累计字节数。
- 窗口建议：64 或 128 个事件。
- 划分要求：按 session 划分 train/val/test。
- 1D-CNN 示例输入：`[batch, 4, 128]`。
- cGAN 负责生成或推荐受约束的流量特征扰动。
- 实验矩阵 A–F、评价指标和开发阶段建议。

这些是文档设计，不代表全部已经实现。

## 2.2 从代码实际确认的架构

实际代码里不是一个统一的“大系统”，而是多个并行/历史实验子项目：

| 子项目 | 实际形态 | 状态 |
| --- | --- | --- |
| `tcp-lab/` | 4 容器 Docker TCP echo 链路 | 已完成并可运行 |
| `normal/` | 4 容器 Docker 文件下载链 | 已完成并有数据 |
| `crypto/` | 独立 AES-256-GCM 模块 + 容器自检 | 已完成 |
| `protocol_stego/` | 单容器内多线程模拟四节点 + 协议/隐写/数据集 | 已完成局部实现 |
| `newtry97/` | 独立的 v0.2 帧协议 + write-splitting 隐写 demo | 已完成单消息 demo |
| `dataset_release/` | 数据集交付包 | 已生成并通过完整性检查 |

重要区别：

- `new_727.md` 描述的是目标架构。
- `protocol_stego/compose.yaml` 实际上只定义一个 `tests` 服务，
  不是四容器网络。
- 四节点端到端流程在 `protocol_stego/examples/demo_secret_transfer.py`
  和 `scripts/session_runner.py` 中通过**本机线程/进程**模拟。

---

# 3. 基础通信链路

## 3.1 tcp-lab Docker 链路（实际存在）

文件：

- `/home/urruna/docker/tcp-lab/docker-compose.yml`
- `/home/urruna/docker/tcp-lab/Dockerfile`
- `client.py`
- `proxy.py`
- `echo_server.py`
- `batch_client.py`

实际配置：

| 容器 | 端口 | 上游 | 作用 |
| --- | ---: | --- | --- |
| `client` | - | `proxy_a:9001` | 发送 `hello network` |
| `proxy_a` | 9001 | `proxy_b:9002` | 透明 TCP 转发 |
| `proxy_b` | 9002 | `server:9003` | 透明 TCP 转发 |
| `server` | 9003 | - | 行式/字节 echo 服务 |

容器镜像：`python:3.11-slim` + `COPY . /app`。

网络：

```text
client_net (internal)
backbone_net (internal)
server_net (internal)
```

Client 行为（`client.py`）：连接 `proxy_a:9001`，发送
`TEST_MESSAGE=hello network`，读取相同长度并比较。

Proxy 行为（`proxy.py`）：asyncio 双向转发，每次 `read(4096)` 记录 CSV
事件到 `logs/proxy_a_events.csv` / `logs/proxy_b_events.csv`。

Server 行为（`echo_server.py`）：`0.0.0.0:9003`，收到多少字节回多少字节。

`batch_client.py` 是更早的批量测试客户端：

- 支持 size choices / uniform；
- 支持 fixed / uniform interval；
- 支持 `EVENT_COUNT`、`SEED`；
- 生成 `client_events.csv`。

## 3.2 normal/ 文件下载链（实际存在）

文件：

- `normal/compose.yaml`
- `normal/Dockerfile`
- `normal/file_server.py`
- `normal/file_client.py`
- `normal/normal_proxy.py`
- `normal/make_files.py`

实际配置：

| 服务 | 作用 |
| --- | --- |
| `server` | 生成并 HTTP 提供 `report_small.txt` / `report_medium.txt` / `report_large.bin` |
| `proxy_a` | 普通透明转发 + CSV 日志 |
| `proxy_b` | 普通透明转发 + CSV 日志 |
| `client` | 通过代理链下载 8 次文件 |

端口沿用 9001/9002/9003。

## 3.3 protocol_stego 端到端链路

`protocol_stego/compose.yaml`：

- 只有一个服务 `tests`；
- 镜像 `protocol-stego:1`；
- build context 是 `..`（即 `tcp-lab`）；
- 挂载 logs/out/data/dataset/docs/scripts；
- 默认命令跑 unittest。

真正四节点流程在代码中由线程模拟：

- `examples/demo_secret_transfer.py`
- `scripts/session_runner.py`

监听：

```text
client -> proxy_a(9101) -> proxy_b(9102) -> server(9103)
```

在批量实验中端口是动态分配的临时端口。

## 3.4 newtry97 四节点 demo

`newtry97/compose.yaml` 定义 `newtry97-917`：

| 服务 | 作用 |
| --- | --- |
| `server` | 行式 TCP echo |
| `proxy_a` | 按 bit 拆分 write |
| `proxy_b` | 按 recv 事件恢复 bit |
| `client` | 发送 cover 行 |

端口：9001/9002/9003。

注意：newtry97 的基础隐写是 **bit=0 单 write，bit=1 拆成两次 write**，
不是 protocol_stego 的 800/1200 长度等级。

---

# 4. Docker 环境

虚拟机实际环境：

- Docker 26.1.3
- Docker Compose 2.27.1
- Docker buildx 0.14.1
- `urruna` 在 docker 组
- daemon.json：
  - registry mirror；
  - `223.5.5.5` / `119.29.29.29` DNS；
  - json-file 日志轮转。

已构建镜像（实际存在）：

- `tcp-lab-client/proxy_a/proxy_b/server:latest`
- `normal-dataset-node:1`
- `crypto-node:1`
- `newtry97-node:917`
- `protocol-stego:1`

当前容器：

- 只有 `crypto-lab-selftest-1` 处于 `Exited (0)`。
- 没有长期运行的实验容器。

当前网络：

- `crypto-lab_default`
- `protocol-stego_default`

`tcp-lab_*` 网络在之前 `docker compose down` 后不存在，需要重新 `up` 才创建。

---

# 5. AES-256-GCM

实现文件：

- `crypto/crypto.py`
- `crypto/crypto_tool.py`
- `crypto/crypto.md`

实际算法：AES-256-GCM。

密文格式：

```text
+------------+---------+------------+------------+-----------+
| Header(1B) | Flags(1B) | Nonce(12B) | Ciphertext | GCM Tag(16B) |
+------------+---------+------------+------------+-----------+
```

固定开销：30 B。

Key：

- `keygen()` 使用 `os.urandom(32)`；
- `derive_key()` 使用 PBKDF2-HMAC-SHA256，默认固定 salt
  `newtry97-crypto-v1`，200000 次迭代；
- 当前是预共享 key / 口令派生，没有密钥交换协议。

Nonce：

- 每条消息随机生成 12 B；
- nonce 随密文一起保存；
- 文档标明同一 key 下不可复用。

Tag：

- 由 `AESGCM.encrypt()` 产生 16 B；
- 解密失败抛 `CryptoError`。

接口：

- `encrypt(plaintext, key, aad=b"", pad_to=None)`
- `decrypt(blob, key, aad=b"")`
- `keygen()`
- `derive_key(passphrase)`
- `ciphertext_overhead()`

固定长度模式：

- `pad_to` 不为空时，明文前加 4 B 长度再补零；
- 密文长度恒为 `pad_to + 30`。

测试证据：

- `crypto/out/crypto_selftest.json`
- 200 轮往返通过；
- padded_ok / tamper_detected / wrong_key_detected 均为 true；
- 实际示例：`HELLO` 5 B → 35 B，`pad_to=64` → 94 B。

没有实现：

- 密钥交换；
- 密钥轮换；
- 随机 salt 分发（当前是固定 salt）；
- 生产级密钥管理。

---

# 6. 协议设计

实际存在两套帧实现，字段一致但 API 和使用层不同。

## 6.1 newtry97 v0.2 位级协议

文件：`newtry97/framing.py`

格式：

```text
| Preamble(32bit) | Version+Reserved(8bit) |
| Frame ID(16bit) | Payload Length(16bit) |
| Payload | CRC-16(16bit) |
```

实际常量：

- Preamble = `0x6E9797A1`
- Version = 1
- Frame ID = 16 bit
- Payload Length = 16 bit，代码上限 512 B
- CRC = CRC-16/XMODEM
- CRC 覆盖 Preamble 之后的 Version/Frame ID/Length/Payload

实际实现：

- `build_frame()`
- `bytes_to_bits()` / `bits_to_bytes()`
- `FrameDecoder`：滑窗搜索 Preamble、CRC 失败后重同步

实际限制：

- 只有单帧恢复逻辑；
- 没有完整的多帧 Frame 重组；
- 没有 FEC / 重传；
- 未实现 Version 协商，只支持 version=1。

## 6.2 protocol_stego 字节级协议

文件：

- `protocol_stego/core/framing.py`
- `protocol_stego/core/reassembly.py`

字段复用 v0.2 常量：

```text
Preamble 0x6E9797A1
Version 1
Frame ID 16 bit
Payload Length 16 bit (max 512)
Payload
CRC-16/XMODEM
```

实际实现：

- `encode_frame()`
- `decode_frame()`
- `FrameStreamDecoder`
- `split_payload()`：除最后一帧外固定满 payload，整除时追加 0 长度终止帧
- `frames_complete()`
- `reassemble_frames()`：检测 duplicate / missing / out-of-order
- 明确异常：
  - `PreambleNotFoundError`
  - `UnsupportedVersionError`
  - `InvalidPayloadLengthError`
  - `IncompleteFrameError`
  - `CRCMismatchError`

测试：

- `tests/test_framing.py`
- `tests/test_reassembly.py`
- `tests/test_crc.py`

当前没有实现：

- FEC；
- 重传；
- 多 Version 兼容；
- 版本协商；
- 协议级密钥交换。

---

# 7. 基础隐写

## 7.1 protocol_stego 的 800/1200 长度调制（当前 Baseline）

配置文件：`protocol_stego/config.yaml`

```yaml
stego:
  low_length: 800
  high_length: 1200
  tolerance: 80
  block_gap_ms: 5
```

实际调制逻辑：

- bit 0 → 目标 800 B；
- bit 1 → 目标 1200 B；
- LOW 合法范围：720–880；
- HIGH 合法范围：1120–1280。

Proxy-A（`proxy/sender_stego.py`）：

1. 读取 secret；
2. 调用 AES 模块加密；
3. 分帧、编码、转 bitstream；
4. 对每个 bit：
   - 计算 target length；
   - 从 cover 流读 exact target bytes；
   - `upstream.sendall(block)`；
   - 记录 `target_length / actual_write_length / bit / frame_id`。

Proxy-B（`proxy/receiver_stego.py`）：

1. 按 LOW/HIGH 范围积累 recv 数据；
2. `_read_modulated_block()` 处理 TCP 分段/合并；
3. `length_to_bit()` 恢复 bit；
4. bitstream → bytes；
5. Frame decode / CRC；
6. 重组 ciphertext；
7. AES 解密。

日志：

- `sender.jsonl`
- `receiver.jsonl`
- `errors.jsonl`

日志字段包括：

```text
target_length
actual_write_length
observed_length
bit
recovered_bit
frame_id
crc_status
```

实际数据验证（23 + 23 sessions）：

- target 800/1200：5654 / 4834；
- actual == target ratio = 1.0；
- actual == observed ratio = 1.0；
- BER = 0；
- frame error rate = 0；
- CRC failure rate = 0；
- observed 超出 800/1200 的事件 = 0。

重要边界：

- 控制的是 application-layer write length；
- 不是 TCP packet length；
- 代码没有操作 TCP header/segment。

## 7.2 newtry97 的 write-splitting 隐写

`newtry97/sender_proxy.py` / `receiver_proxy.py` 实现的是另一种策略：

- bit=0：整行一次 write；
- bit=1：整行拆成两次 write，中间 sleep。

这不是 800/1200 长度等级策略，必须和 protocol_stego 的基础隐写区分。

---

# 8. 数据集

## 8.1 历史 Docker Normal 数据

位置：`/home/urruna/docker/tcp-lab/logs/`

文件：

- `proxy_a_events.csv`
- `proxy_b_events.csv`

实际内容：

- 早期 Docker 链路 smoke 数据；
- payload `hello network`，13 B；
- Proxy-A：1 session，2 events（forward/reverse）；
- Proxy-B：1 session，2 events（forward/reverse）；
- 无 pcap；
- 原始 CSV 后续被另一套 schema 的写入追加过；
- 交付包中提供了早期行的规范化视图：
  `historical_normal/processed/early_docker_normal_events.csv`。

## 8.2 baseline_lenmix_v1

位置：

- Windows：`D:\C\work_DC\baseline_lenmix_v1`
- Ubuntu：`/home/urruna/docker/tcp-lab/logs/baseline_lenmix_v1`

实际规模：

- client events：256，全部 passed；
- Proxy-A events：512（forward 256，reverse 256）；
- Proxy-B events：512（forward 256，reverse 256）；
- length：64 / 128 / 256 / 512 / 1024 B 循环；
- 1 个 experiment/session；
- 无 pcap。

环境说明：项目文档 `Docker_m1.md` 描述该数据来自早期
Ubuntu 20.04 VMware 原生多进程实验，不是当前 protocol_stego 的 Docker
对照组。

## 8.3 normal/ 文件下载 Normal 数据

位置：`D:\C\work_DC\normal` 与 Ubuntu `.../normal`

`normal/dataset_summary.json` 实际统计：

- `client_events.csv`：8 行，8 个下载全部 ok；
- `proxy_a_events.csv`：771 行，8 forward + 763 reverse，sessions=8；
- `proxy_b_events.csv`：773 行，8 forward + 765 reverse，sessions=8；
- `server_events.csv`：8 行；
- 总 bytes：3,082,890；
- 文件：64 KiB / 256 KiB / 1 MiB；
- 无 modulation，无秘密 payload；
- 无 pcap；
- 不是 session JSONL 数据集。

## 8.4 newtry97 v0.2 demo 数据

位置：`newtry97/logs/`

实际内容：

- `proxy_a_events.csv`、`proxy_b_events.csv`：816 行/文件（forward 472，reverse 344）；
- `recovered.txt`：`Hello from A to B (newtry97)`；
- `run_demo.log`；
- 这是单消息 demo 的实验产物，不是正式 ML 数据集。

## 8.5 protocol_stego 数据集（当前主数据集）

位置：`protocol_stego/dataset/`

Raw：

- Normal：23 sessions，10258 events；
- Stego：23 sessions，10488 events；
- 每个 session 有 metadata / session_config / sender.jsonl / receiver.jsonl /
  errors.jsonl / sender_result.json / receiver_result.json。

Processed：

- `windows.npz`，内含 `X.npy` / `y.npy`；
- `X.shape = [138, 4, 128]`；
- `y.shape = [138]`；
- features：

```text
0 direction
1 length
2 inter_arrival_time
3 cumulative_bytes
```

- label：0=Normal，1=Stego。

Splits：

- train：38 sessions / 114 windows；
- val：4 sessions / 12 windows；
- test：4 sessions / 12 windows；
- session 无交叉；
- duplicate sample = 0；
- NaN = 0；
- Inf = 0；
- BER / frame error / CRC failure rate = 0。

数据质量结论：`READY_FOR_CNN`。

数据限制：

- Normal 主要是 1024 B；
- Stego 是 800/1200 B；
- `direction` 当前恒为 +1；
- 当前任务主要检测 800/1200 modulation，不是一般隐写检测；
- 每类 23 sessions 仍低于文档建议的 50/类。

## 8.6 dataset_release 交付包

位置：

- Windows：`D:\C\work_DC\dataset_release` 与 `dataset_release.zip`
- Ubuntu：`/home/urruna/docker/tcp-lab/dataset_release` 与
  `dataset_release.zip`

实际完整性检查结果：

- Passed = True；
- session：Normal 23 / Stego 23；
- events：Normal 10258 / Stego 10488；
- X `[138,4,128]`，y `[138]`；
- label 分布 69/69；
- split overlap 空；
- duplicate sample 0；
- NaN/Inf 0；
- JSONL parse errors 0；
- checksum 文件：`checksums/SHA256SUMS.txt`。

其中：

- `dataset_release/protocol_stego/processed/X.npy`
- `dataset_release/protocol_stego/processed/y.npy`

---

# 9. 1D-CNN 当前状态

实际代码搜索：

- 没有找到 `torch` / `tensorflow` / `sklearn` 训练代码；
- 没有 `cnn_detector.py`；
- 没有模型权重/checkpoint。

当前只有：

- `new_727.md` 中的 CNN 设计；
- 数据质量报告的 `READY_FOR_CNN` 结论；
- baseline_analysis 的 rule-based / Logistic Regression 对照。

因此 1D-CNN 状态是：**未实现**。

---

# 10. cGAN 当前状态

实际代码搜索：

- 没有 cGAN / GAN 代码；
- 没有 GAN-Stego 数据；
- 没有 cGAN 产生的策略或特征。

`new_727.md` 和文档中有 cGAN 设计，但项目内没有实现。

因此 cGAN 状态是：**设计阶段**。

---

# 11. 已完成内容

- Docker 基础 TCP 链路与验证；
- Normal 文件下载链路；
- AES-256-GCM 模块与自检；
- v0.2 帧格式、CRC、bitstream、滑窗解码；
- protocol_stego 字节级 frame encode/decode、重组；
- 800/1200 application-layer 长度调制；
- Proxy-A 发送端与 Proxy-B 接收端；
- JSONL 结构化日志；
- 单元测试与 E2E 测试；
- 23 Normal + 23 Stego session 数据；
- processed X/y 与 session-level split；
- rule-based 和 Logistic Regression baseline；
- 数据质量报告、baseline 报告、dataset_release 交付包与完整性检查。

---

# 12. 进行中内容

从文件和报告可确认的“进行中”主要是：

- 扩大数据规模（当前 23/类，文档建议 50/类）；
- 增加 Normal 业务多样性；
- 未来把 protocol_stego 的四节点流程真正接入 Docker 四容器网络；
- 准备后续 1D-CNN 实验（数据已 READY_FOR_CNN，但模型未开始）。

没有发现正在运行的训练进程或长期运行的数据采集容器。

---

# 13. 尚未实现内容

- 1D-CNN 检测器；
- cGAN 特征优化器；
- GAN-Stego 数据；
- FEC / 重传；
- 多 Version 协议；
- 协议级密钥交换/轮换；
- pcap 抓包数据；
- TCP packet length 控制；
- protocol_stego 的四容器 Docker 化运行（当前是单容器线程模拟）；
- 真实网络条件下的 RTT/带宽/丢包实验；
- 混合 Normal 数据集的正式实验方案。

---

# 14. 文件结构

## 14.1 Ubuntu6.21

实际根目录：

```text
/home/urruna/docker/tcp-lab/
├── batch_client.py
├── client.py
├── docker-compose.yml
├── Dockerfile
├── echo_server.py
├── proxy.py
├── logs/
│   ├── proxy_a_events.csv
│   ├── proxy_b_events.csv
│   ├── baseline_lenmix_v1/
│   └── baseline_lenmix_v1.zip
├── crypto/
├── normal/
├── newtry97/
├── protocol_stego/
├── dataset_release/
└── dataset_release.zip
```

注意：`~/tcp-lab` 不存在，不要按该路径检索。

## 14.2 Windows

```text
D:\C\work_DC\
├── baseline_lenmix_v1/
├── crypto/
├── dataset_release/
├── dataset_release.zip
├── newtry97/
├── normal/
├── picture/
├── Docker_m1.md
├── new_727.md
├── new_727.pdf
├── newtry97.md
└── PROJECT_AUDIT.md
```

---

# 15. 文件之间的依赖关系

## 15.1 tcp-lab 基础链

```text
docker-compose.yml
  → Dockerfile
  → client.py / proxy.py / echo_server.py
  → logs/*.csv
```

## 15.2 normal 文件链

```text
normal/compose.yaml
  → normal/Dockerfile
  → normal/file_client.py / file_server.py / normal_proxy.py / make_files.py
  → logs CSV / files / downloads
```

## 15.3 crypto

```text
crypto/crypto_tool.py
  → crypto/crypto.py
  → out/crypto_selftest.json
```

## 15.4 protocol_stego

```text
compose.yaml
  → Dockerfile
  → core/*.py
  → proxy/sender_stego.py / receiver_stego.py
  → examples/demo_secret_transfer.py
  → scripts/session_runner.py
  → scripts/dataset_builder.py / split_dataset.py / dataset_stats.py
  → scripts/data_quality_report.py / baseline_analysis.py
  → dataset/raw / processed / splits
  → docs/*.md
```

`core/crypto_adapter.py` 通过路径加载 `crypto/crypto.py`，没有重新实现 AES。

## 15.5 dataset_release

```text
scripts/build_dataset_release.py
  → protocol_stego/dataset/*
  → historical_normal/raw/*
  → dataset_release/*
  → dataset_release.zip
```

dataset_release 是交付产物，不是运行时源码依赖。

---

# 16. 当前已知问题

1. **路径不一致**：用户描述的 `~/tcp-lab` 不存在，实际路径是
   `/home/urruna/docker/tcp-lab`。
2. **protocol_stego 不是四容器 Docker 链**：compose 只有一个 `tests`
   服务；四节点流程是线程模拟。
3. **历史 Docker Normal 数据格式混合**：原始 CSV 后续被另一种 schema
   追加；原始文件保留，规范化早期行单独输出。
4. **多个 Normal 数据源容易混淆**：
   - tcp-lab early Docker normal；
   - baseline_lenmix_v1；
   - normal/ 文件下载 norml_v1；
   - protocol_stego protocol normal。
5. **direction 当前无区分度**：Normal/Stego 都是 +1。
6. **Normal length 过于单一**：窗口内主要是 1024 B。
7. **Stego 检测任务偏简单**：800/1200 是显式调制签名。
8. **application-layer block 依赖**：TCP 合并/分段可能导致
   `length_out_of_range`；第一版无 FEC/重传。
9. **没有 pcap**：所有现有数据都是应用层日志或 CSV，没有抓包数据。
10. **无密钥交换/轮换**：当前 AES key 是预共享/口令派生，固定 KDF salt。
11. **newtry97 与 protocol_stego 两套协议/隐写策略并存**：字段格式相似，
    但调制方式不同，不能混称。
12. **Windows 与 Ubuntu 存在多份拷贝**：需要明确哪一份是权威源；
    本次审计显示两边内容基本一致，但不保证未来自动同步。

---

# 17. 后续工作建议

1. 先统一并固定权威项目路径，避免继续在多个拷贝间漂移。
2. 明确使用哪一份 Normal 作为正式对照：
   - 严格对照：protocol_stego Normal vs protocol_stego Stego；
   - 补充对照：historical Normal vs protocol_stego Stego。
3. 如果要进入 1D-CNN，直接使用
   `dataset_release/protocol_stego/processed/X.npy`、`y.npy`
   和 `dataset_release/protocol_stego/splits/`。
4. 1D-CNN 结果必须与 rule-based 和 Logistic Regression baseline 对照。
5. 继续扩采时优先增加 Normal 业务多样性；不要修改原始数据。
6. 若要做协议级 Docker 四容器化，需要新增 compose，而不是改写现有
   protocol_stego 单容器测试链。
7. cGAN / GAN-Stego 在 1D-CNN 与基础数据集稳定后再启动。

---

# 最终状态表

| 模块状态实际证据说明 | 状态 | 证据 |
| --- | --- | --- |
| Docker | 已完成 | tcp-lab compose、normal compose、protocol_stego compose 实际存在；镜像和链路验证完成 |
| Normal Traffic | 部分完成 | 已有 historical Docker normal、baseline_lenmix_v1、normal_v1、protocol_stego Normal 23 sessions；但 Normal 业务多样性有限 |
| AES-256-GCM | 已完成 | `crypto/crypto.py`、`crypto_tool.py`、自检 200 轮通过、30 B overhead |
| Protocol | 已完成 | `newtry97/framing.py` 与 `protocol_stego/core/framing.py`、CRC、bitstream、Frame、reassembly 均有实现和测试 |
| Basic Stego | 已完成 | 800/1200 length modulation 已由 Proxy-A/B 实现并生成 23 Stego sessions；BER/FER/CRC=0 |
| Dataset | 部分完成 | 46 sessions / 138 windows，X[138,4,128]，splits 无泄漏；但每类 23 sessions，低于 50/类建议 |
| 1D-CNN | 未实现 | 无 torch/tensorflow/sklearn/CNN 代码，只有设计文档和数据集 READY_FOR_CNN 结论 |
| cGAN | 设计阶段 | `new_727.md` 有设计；项目内无 GAN 代码、无 GAN-Stego 数据 |
