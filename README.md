# 授权环境下的 TCP 流量隐写实验

## 项目简介

本仓库汇总了一个封闭授权实验项目目前的全部成果，研究内容包括：

- 经两级代理转发的正常 TCP 流量；
- 在同一条代理链上传输秘密数据；
- 应用层流量特征调制；
- 为后续 1D-CNN / cGAN 检测实验构建数据集。

本项目**不是**生产系统，只能在授权的实验环境中使用。

## 研究目标

长期目标是研究以下四者之间的权衡关系：

```text
秘密载荷容量
        ↔
可靠交付（BER / FER）
        ↔
网络性能（时延 / 吞吐）
        ↔
可检测性（1D-CNN / cGAN 实验）
```

加密、隐写与 GAN 特征优化是三个不同的层次，不能混为一谈：

| 层次 | 解决的问题 |
| --- | --- |
| AES-256-GCM | 内容看不懂 |
| 应用层长度调制 | 看不出有秘密通信 |
| cGAN（规划中） | 让调制后的流量分布更接近正常流量 |

## 整体架构

```text
Client → Proxy-A → Proxy-B → Server
              ↘       ↙
           日志 / 数据集
                  ↓
               分析
```

当前已实现的技术栈：

1. `src/tcp_lab/` —— 最早的 Docker 四容器 TCP echo 链。
2. `src/normal_file_transfer/` —— 用正常流量采集数据的 Docker 文件下载链。
3. `src/crypto/` —— AES-256-GCM 加密模块。
4. `src/newtry97/` —— v0.2 帧协议与写拆分（write-splitting）演示。
5. `src/protocol_stego/` —— 当前使用的协议、800/1200 隐写、数据集与实验脚本。

## 网络拓扑

### 基础 Docker 链

```text
client → proxy_a:9001 → proxy_b:9002 → server:9003
```

网络：

```text
client_net, backbone_net, server_net   （internal）
```

### 当前 protocol_stego 实验

```text
client → proxy_a:9101 → proxy_b:9102 → server:9103
```

注意：`src/protocol_stego/compose.yaml` 目前只启动一个 `tests` 容器，
四节点流程由 `examples/demo_secret_transfer.py` 和
`scripts/session_runner.py` 在进程内模拟。

详见 `docs/architecture/network-topology.md`。

## 当前状态

完整状态表见 `PROJECT_STATUS.md`，简要版如下：

- Docker 基础链路：已完成
- 正常流量采集：部分完成
- AES-256-GCM：已完成
- 帧协议 / CRC / 比特流 / 重组：已完成
- 800/1200 应用层隐写：已完成
- 数据集（raw / processed / splits）：部分完成（466 个 session：233 Normal + 233 Stego，1398 个窗口；Normal 仍是固定 1024 字节写入）
- 规则基线与逻辑回归基线：已完成
- 1D-CNN：部分完成（`src/1dcnn/` 中已实现并训练；但现有指标用的是另一套 168 窗口数据，session 划分未验证）
- cGAN：部分完成（`src/cWGAN-GP/` 已实现条件 WGAN-GP；训练尚未跑通，无 checkpoint、无结果）
- GAN-Stego：未实现

仓库、Ubuntu6.21 虚拟机与本地旧目录三个来源的合并说明见
`PROJECT_REVIEW.md`。

## 仓库结构

```text
.
├── README.md
├── PROJECT_REVIEW.md
├── PROJECT_STATUS.md
├── PROJECT_AUDIT.md
├── REPOSITORY_PLAN.md
├── CHANGELOG.md
├── TEAM_GUIDE.md
├── LICENSE_OR_USAGE.md
├── docs/
│   ├── architecture/
│   ├── crypto/
│   ├── protocol/
│   ├── steganography/
│   ├── dataset/
│   ├── experiments/
│   ├── planning/
│   └── audit/
├── src/
│   ├── tcp_lab/
│   ├── normal_file_transfer/
│   ├── crypto/
│   ├── newtry97/
│   ├── protocol_stego/
│   ├── 1dcnn/
│   └── cWGAN-GP/
├── datasets/
│   ├── historical/
│   ├── normal_v1/
│   └── protocol_stego/
└── releases/
    ├── dataset_release_v1/
    └── dataset_release_v1.zip
```

## 快速开始

### 1. 基础 Docker TCP 链

```bash
cd src/tcp_lab
docker compose up
```

客户端预期输出：

```text
[client] received: hello network
[client] PASS: returned payload matches sent payload
```

### 2. 正常文件下载链

```bash
cd src/normal_file_transfer
docker compose up --abort-on-container-exit --exit-code-from client
```

### 3. 加密模块自检

```bash
cd src/crypto
docker compose up --build
```

### 4. protocol_stego 测试与端到端演示

```bash
cd src/protocol_stego
docker compose build
docker compose run --rm tests python -m unittest discover -s tests -v
docker compose run --rm tests python examples/demo_secret_transfer.py
```

### 5. 重跑数据集管线

注意：运行入口必须用模块方式 `python -m`，直接写 `python scripts/xxx.py`
会因 `sys.path` 不含项目根目录而报 `ModuleNotFoundError`。

```bash
cd src/protocol_stego
docker compose run --rm tests python -m scripts.run_experiment \
  --mode both --normal 20 --stego 20 --seed 42 \
  --secret-size 16 --block-gap-ms 20 --window-size 128
docker compose run --rm tests python -m scripts.dataset_builder --window-size 128
docker compose run --rm tests python -m scripts.split_dataset
docker compose run --rm tests python -m scripts.dataset_stats
docker compose run --rm tests python -m scripts.data_quality_report
docker compose run --rm tests python -m scripts.baseline_analysis
```

## 数据集

主机器学习数据集：

```text
datasets/protocol_stego/processed/windows.npz
releases/dataset_release_v1/protocol_stego/processed/X.npy
releases/dataset_release_v1/protocol_stego/processed/y.npy
```

当前形状：

```text
X.shape = [1398, 4, 128]
y.shape = [1398]
标签：0 = Normal，1 = Stego
特征：
  0 direction              方向
  1 length                 数据块长度
  2 inter_arrival_time     相邻事件间隔
  3 cumulative_bytes       累积字节数
```

当前 session 概况：

```text
Normal session：233，全部成功
Stego session： 233，全部成功
事件总数：      210165
窗口总数：      1398（699 Normal / 699 Stego）
```

按 session 划分：

```text
train：374 个 session，1122 个窗口
val：   46 个 session， 138 个窗口
test：  46 个 session， 138 个窗口
```

不要随机重划分窗口，必须使用 `datasets/protocol_stego/splits/` 中已有的
session 级划分。

数据集在 2026-09-26 从 46 个 session 扩到 466 个 session，具体命令、
8 个被隔离的 Stego session 以及仍然存在的局限见
`docs/experiments/dataset-scaleup-20260926.md`。

详见 `docs/dataset/dataset-overview.md`。

## 加密

实现位置：

```text
src/crypto/crypto.py
src/crypto/crypto_tool.py
```

算法：AES-256-GCM。

数据格式：

```text
Header(1B) + Flags(1B) + Nonce(12B) + Ciphertext + Tag(16B)
```

固定开销 30 字节。

详见 `docs/crypto/aes-256-gcm.md`。

## 协议

已实现的协议字段：

```text
Preamble(32 bit) | Version(8 bit 字段, version=1)
| Frame ID(16 bit) | Payload Length(16 bit)
| Payload | CRC-16/XMODEM(16 bit)
```

Preamble：`0x6E9797A1`。

实现位置：

```text
src/newtry97/framing.py
src/protocol_stego/core/framing.py
```

详见 `docs/protocol/protocol-design.md`。

## 隐写

当前基线策略：

```text
比特 0 → 约 800 字节的应用层写入长度
比特 1 → 约 1200 字节的应用层写入长度
```

调制的是**应用层写入长度**，不是 TCP 报文长度。

实现位置：

```text
src/protocol_stego/core/modulation.py
src/protocol_stego/proxy/sender_stego.py
src/protocol_stego/proxy/receiver_stego.py
```

详见 `docs/steganography/basic-stego.md`。

## 实验结果

已有实验报告：

- `docs/experiments/data-quality-report.md`
- `docs/experiments/baseline-analysis.md`
- `docs/experiments/newtry97-v0.2.md`
- `docs/experiments/1dcnn-results.md`
- `docs/experiments/cwgan-results.md`
- `docs/experiments/dataset-scaleup-20260926.md`

当前数据质量结论：`READY_FOR_CNN`。

但要注意：当前 Normal 数据基本都是 1024 字节写入，而 Stego 是 800/1200
字节。因此 CNN 实验实际上测的是「有没有 800/1200 这个调制签名」，
而不是「一般意义上的隐写可检测性」。

## 1D-CNN

独立的 1D-CNN 交付物位于：

```text
src/1dcnn/
```

其中包含 CNN 模型、训练与评估脚本、面向 GAN / 外部窗口的冻结推理接口、
逻辑回归与规则基线、已训练权重以及结果报告。

运行方式：

```bash
cd src/1dcnn
python -m pip install -r requirements.txt
python evaluate.py
python -m unittest discover -s tests -v
```

重要提示：该模块目前使用的是一套**独立的 168 窗口数据集**
（`window=128`，`step=64`），且没有 session 索引。它与
`datasets/protocol_stego/` 的 1398 窗口数据集**没有任何精确重叠**。
因此：

- 不要把两套数据集静默合并；
- 不要用当前 1D-CNN 指标声称跨 session 泛化能力。

当前报告的结果：

```text
CNN：  accuracy=0.9200，F1=0.9375，ROC-AUC=0.9867
LR：   accuracy=0.8800，F1=0.8889，ROC-AUC=1.0000
规则： accuracy=0.8800，F1=0.8889
```

详见 `docs/experiments/1dcnn-results.md`。

## cGAN（cWGAN-GP）

模块位置：

```text
src/cWGAN-GP/cWGAN-GP.py
src/cWGAN-GP/README_cWGAN.md
```

它实现了一个条件 WGAN-GP，生成器只输出应用层**长度通道** `[B, 128]`，
并投影到两个互不重叠的长度区间（对标准化后的长度通道使用
`BIT0_RANGE = (-1.5, -0.5)`、`BIT1_RANGE = (0.5, 1.5)`），
Proxy-B 只需一个阈值即可判定比特。

当前状态：**只有代码，没有任何结果。**

- 模块要求至少 **1000 个训练窗口**；
- 数据集已于 2026-09-26 扩容，train split 现有 **1122 个窗口**，
  数据量门槛已经满足；
- 但默认的 `--data-dir` 需要 `datasets/protocol_stego/` 下的
  `real_train_X.npy` / `real_train_y.npy`，仓库里实际只有
  `processed/windows.npz`；
- 长度区间常量假定长度通道已标准化，而协议数据集里存的是原始字节数。

目前没有 checkpoint、没有生成数据、也没有 GAN-Stego 评估结果。
详见 `docs/experiments/cwgan-results.md`。

## 团队开发约定

修改任何内容前请先阅读 `TEAM_GUIDE.md`。

未经明确同意，不要修改：

- AES-256-GCM 实现；
- 现有协议字段布局；
- Docker 网络拓扑；
- 已有原始数据集；
- 800/1200 基线调制。

新的实验请放到 `docs/experiments/` 与 `src/protocol_stego/`（或新建一个
命名清晰、独立的子项目），不要在已有结果上覆盖重写。
