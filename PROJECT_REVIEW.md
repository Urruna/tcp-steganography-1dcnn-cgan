# 项目总览与进展总结

本文件是给项目负责人阅读的**中文汇总**，把三个来源（GitHub 仓库、Ubuntu621 虚拟机、
Windows 旧工作目录）合并后的真实状态写在一处。技术细节仍以仓库内的英文文档为准。

核对日期：2026-09-26

---

## 0. 本次核对做了什么

| 来源 | 实际情况 | 核对方式 |
| --- | --- | --- |
| GitHub 仓库 | `Urruna/tcp-steganography-1dcnn-cgan`，最新提交 `6840169`（2026-09-21） | 全量 clone 到 `projects/tcp-steganography`，工作区干净 |
| Ubuntu621 虚拟机 | `/home/urruna/docker/tcp-lab`，1162 个文件，63 MB | 通过 VMware Tools 只读导出完整文件清单比对 |
| Windows 旧目录 | `D:\C\work_DC`，1257 个文件，停在提交 `01f8304` | 与新克隆逐文件比对 |

关于路径：请求里写的 `D:\C\work\_DC` **不存在**，真实的旧目录是 `D:\C\work_DC`。
因此没有对它做任何删除。

结论：**虚拟机与 Windows 旧目录都没有仓库之外的成果**。差异只有 4 类，
且都属于"有意不提交"或"可重复生成"的文件（见第 7 节）。

---

## 1. 项目在研究什么

在**授权的实验环境**里，研究同一条代理链上的两类流量：

```text
正常业务流量          秘密数据流量
     ↓                     ↓
  直接转发            AES-256-GCM 加密
                           ↓
                      帧封装 + CRC
                           ↓
                  比特流 → 应用层写入长度调制
                           ↓
                      经代理链传输
```

长期目标是刻画这条权衡链：

```text
秘密载荷容量  ↔  可靠交付(BER/FER)  ↔  网络性能(时延/吞吐)  ↔  可检测性(1D-CNN / cGAN)
```

项目里反复强调的一条原则（三层不能混为一谈）：

| 层次 | 解决的问题 |
| --- | --- |
| AES-256-GCM | 内容看不懂 |
| 应用层长度调制（基础隐写） | 看不出有秘密通信 |
| cGAN | 让调制后的流量特征更接近正常分布 |

密码学安全 ≠ 流量隐蔽。当前基线把比特映射成固定的 800 / 1200 字节写入长度，
**内容安全，但长度序列本身极容易被识别**——这正是后面 cGAN 要处理的问题。

---

## 2. 系统架构

### 2.1 通信链路

```text
Client → Proxy-A → Proxy-B → Server
```

- **Proxy-A**：转发业务数据；在隐写模式下，按比特决定本次应用层写入长度。
- **Proxy-B**：转发业务数据；在隐写模式下，按长度反推比特并重组。
- **Server**：业务终点（早期是 echo，现在是文件下载）。

三种代理链现实存在，互不覆盖：

| 链路 | 位置 | 端口 | 形态 |
| --- | --- | --- | --- |
| 基础 TCP echo 链 | `src/tcp_lab/` | 9001/9002/9003 | 真正的 4 容器 Docker |
| 正常文件下载链 | `src/normal_file_transfer/` | 9001/9002/9003 | 真正的 4 容器 Docker |
| protocol_stego 链 | `src/protocol_stego/` | 9101/9102/9103 | **单容器内多线程模拟**，不是 4 容器 |
| newtry97 v0.2 链 | `src/newtry97/` | — | 独立实验，不是 800/1200 基线 |

### 2.2 分析链路

```text
raw session JSONL
 → observed_length 事件流
 → 128 事件定长窗口
 → X = [N, 4, 128]（direction, length, inter_arrival_time, cumulative_bytes）
 → 按 session 划分 train/val/test
 → 规则基线 / 逻辑回归 / 1D-CNN / (未来) GAN-Stego 对比
```

### 2.3 目标工作流与实际完成度

```text
Normal Traffic → Basic Stego → Dataset → 1D-CNN → cGAN → GAN-Stego → Evaluation
   部分完成        已完成       部分完成   部分完成   部分完成    未实现      部分完成
```

---

## 3. 模块清单与状态

状态只用：已完成 / 部分完成 / 设计阶段 / 未实现 / 未确认。

| 模块 | 状态 | 证据 | 说明 |
| --- | --- | --- | --- |
| Network | 已完成 | `src/tcp_lab/`, `src/normal_file_transfer/` | Client→Proxy-A→Proxy-B→Server 真实跑通 |
| Docker | 已完成 | 各 `compose.yaml` / `docker-compose.yml` | 虚拟机中已构建镜像并运行过 |
| Encryption | 已完成 | `src/crypto/` | AES-256-GCM，PBKDF2 派生，固定 30 B 开销，自检通过 |
| Protocol | 已完成 | `src/protocol_stego/core/framing.py` 等 | Preamble/Version/FrameID/Length/Payload/CRC 已实现并有测试 |
| Steganography（基础隐写） | 已完成 | `core/modulation.py`, `proxy/` | 800/1200 应用层写入长度调制，已实测 |
| Dataset | 部分完成 | `datasets/protocol_stego/` | 23+23 session、138 窗口；未达到计划的每类 50 |
| 1D-CNN | 部分完成 | `src/1dcnn/` | 有代码、权重、结果；但用的是另一套 168 窗口数据，session 隔离未验证 |
| cGAN | 部分完成 | `src/cWGAN-GP/` | 代码已实现；训练被数据量卡住，无产物、无结果 |
| GAN-Stego 数据 | 未实现 | — | 无生成器 checkpoint，无合成数据 |
| pcap 抓包 | 未实现 | — | 仓库内无 `.pcap` |
| FEC / 重传 | 未实现 | — | 协议代码中不存在 |

---

## 4. 已确认的实验事实

### 4.1 主数据集 `protocol_stego`

```text
Normal session : 23      Stego session : 23      全部成功
Normal 事件数   : 10258   Stego 事件数   : 10488
窗口总数        : 138     Normal 69 / Stego 69
X.shape = [138, 4, 128]   y.shape = [138]

按 session 划分：train 38 session / 114 窗口，val 4 / 12，test 4 / 12
无 session 泄漏，无重复样本，无 NaN/Inf
BER = 0，frame error rate = 0，CRC failure rate = 0
```

质量报告的结论是 `READY_FOR_CNN`。

但报告同时指出一个关键事实：**Normal 数据基本都是 1024 字节定长写入，
Stego 是 800/1200 字节写入**。也就是说，当前检测器实际学到的是
"800/1200 这个调制签名"，而不是"这里有没有秘密通信"。

### 4.2 1D-CNN

```text
数据：168 窗口（train 117 = 32/85，val 26 = 6/20，test 25 = 10/15）
      window=128, step=64, 无 session 索引
结果：CNN  acc 0.9200 / F1 0.9375 / ROC-AUC 0.9867
      LR   acc 0.8800 / F1 0.8889 / ROC-AUC 1.0000
      Rule acc 0.8800 / F1 0.8889
```

**重要限制**：这 168 个窗口与 `datasets/protocol_stego/` 的 138 个窗口
**没有任何精确重叠**，而且这套数据没有 session 索引，
`session_split_verified=false`。所以：

- 现有准确率只能当作"流程跑通了"的初步数字；
- 不能声称跨 session 泛化能力；
- 两套数据不能静默合并。

### 4.3 cWGAN-GP（本次新发现的重点）

`src/cWGAN-GP/` 已经实现了一个条件 WGAN-GP：

- 生成器只输出 **长度通道** `[B, 128]`，投影到两个不重叠的长度带：
  `BIT0_RANGE = (-1.5, -0.5)`，`BIT1_RANGE = (0.5, 1.5)`；
- 用 WGAN-GP 梯度惩罚 + 类别平衡采样；
- 推理时 Proxy-B 只需一个阈值（如 1000 字节）即可判比特。

**为什么设计成两个"宽区间"而不是固定 800/1200**：固定值是长度直方图上的两个尖峰，
极易被检测；宽区间把尖峰摊成宽峰，比特信息仍由区间不重叠来保证。
这个思路与项目的"降低可检测性"目标是一致的。

**当前卡点（必须解决才能继续）**：

1. 模块文档自己写明**至少需要 1000 个训练窗口**；当前只有 114 个。
   实测在 114 窗口下 Critic / Generator loss 单调爆炸。
2. 数据接口对不上：代码默认读
   `datasets/protocol_stego/real_train_X.npy`，但仓库里实际只有
   `datasets/protocol_stego/processed/windows.npz`。
3. 代码假定长度通道已标准化（mean≈0, std≈1），但协议数据集存的是原始值
   （direction ±1，length 800/1200），没有共享的 scaler。
4. 文档中"1D-CNN 使用 `datasets/protocol_stego`"的说法与实现不符，
   1D-CNN 实际用的是 `src/1dcnn/data/` 的 168 窗口数据。

目前**没有** checkpoint、没有合成数据、没有 GAN-Stego 的任何检测结果。

---

## 5. 三个来源的合并结果

### 5.1 Ubuntu621 虚拟机

已用只读清单核对（1162 个文件）：

- 目录内容与仓库 `src/tcp_lab`、`src/normal_file_transfer`、`src/crypto`、
  `src/newtry97`、`src/protocol_stego` 一一对应；
- **没有任何 2026-09-20 之后修改的文件**；
- **没有 `1dcnn`、没有 `cWGAN-GP`** —— 这两个模块只存在于 GitHub 与本地；
- 镜像已构建：`protocol-stego:1`、`crypto-node:1`、`normal-dataset-node:1`、`python:3.11-slim`。

即：虚拟机是**运行环境 + 早期实验产地**，不是最新代码来源。

### 5.2 Windows `D:\C\work_DC`

是仓库在提交 `01f8304` 的本地副本（比 origin 落后一个提交），工作区干净。
相对新克隆多出 4 个文件，全部是有意忽略的：

| 文件 | 大小 | 为什么不在仓库 |
| --- | --- | --- |
| `datasets/protocol_stego/processed/data_quality_report.json` | 19.7 MB | `.gitignore` 显式排除的大报告 |
| `releases/dataset_release_v1/.../data_quality_report.json` | 19.7 MB | 同上（发布包内的副本） |
| `src/1dcnn/results/run.log` | 697 B | `*.log` 被忽略 |
| `src/newtry97/logs/run_demo.log` | 288 B | `*.log` 被忽略 |

### 5.3 虚拟机里有、但仓库里没有的文件（逐条说明）

| 文件 | 处理建议 |
| --- | --- |
| `crypto/out/demo.key`, `demo_key.bin`, `demo_config.yaml` | **密钥类，不能提交**。目前只存在于虚拟机，建议你确认是否需要单独备份 |
| `crypto/out/*.enc`（6 个） | 自检产物，可重复生成；仓库已保留 `hello.txt.padded.enc` 作为样例 |
| `data_quality_report.json` | 大文件，保持忽略 |
| `dataset_release.zip` | 与仓库 `releases/dataset_release_v1.zip` 一致 |
| `logs/baseline_lenmix_v1.zip` | 内容已展开进 `datasets/historical/baseline_lenmix_v1/` |
| `newtry97/__pycache__/*.pyc` | 编译缓存，忽略 |

---

## 6. 已知问题与风险

按严重程度排列：

1. **两套数据集口径并存**，且 1D-CNN 的那套没有 session 索引 ——
   现有 0.92 的准确率在 session 级别上不可信。
2. **数据量不足**：cGAN 需要 ≥1000 窗口，现在 114；数据集本身也远未到计划的每类 50 session。
3. **cWGAN-GP 与数据管线接口不一致**（路径、标准化、区间常量）。
4. **Normal 流量多样性不足**：几乎全是 1024 字节定长写入，与 Stego 的 800/1200
   形成"与实验目的无关"的人为差异，会让检测任务变得过于简单。
5. 文档与实现存在若干不一致（project-overview 曾把 1D-CNN 写成"未实现"；
   cWGAN README 写错了 1D-CNN 的数据来源）。本次已修正可确认的部分。

---

## 7. 下一步方案

### P0 —— 不做完后面都白做

1. **统一数据集口径**：确定 `datasets/protocol_stego/` 为唯一权威数据集，
   把 1D-CNN 的训练/评估切到它的 session-level split 上；
   若要保留 168 窗口那套，必须补出它到 session 的映射。
2. **扩充到 167 Normal + 167 Stego session**（≈1000+ 窗口），
   固定 seed、每个 session 独立 metadata、保留原始 sender/receiver JSONL、
   不覆盖现有 23+23。
3. **修 cWGAN-GP 数据接口**：改读 `processed/windows.npz` 或补出
   `real_train_X.npy`/`real_train_y.npy`；确定长度通道是原始字节还是标准化值，
   并同步修改 `BIT0_RANGE` / `BIT1_RANGE`。

### P1 —— 让结论站得住

4. **Normal 流量多样化**：给正常业务引入可变的写入块长（例如按文件分片自然变化），
   使 Normal 不再是"清一色 1024"。注意：**不要动 800/1200 这个 Stego 基线**。
5. **补全实验环境记录**：虚拟机版本、Docker/Compose 版本、seed、完整命令，
   保证别人能复现。
6. **重跑基线对照**：在统一数据集上重出 Rule → Logistic Regression → 1D-CNN 三级对比。

### P2 —— 闭环与新结论

7. **打通评估闭环**：cWGAN 生成长度策略 → Proxy-A 实际执行 → 重新采集数据
   → 用 1D-CNN 评估 GAN-Stego 是否比 Baseline-Stego 更难检测
   （关键指标是 GAN-Stego 的 AUC 是否低于 Baseline-Stego）。
8. 补充性能侧指标（时延、吞吐）与可靠性指标（BER/FER）的联合报告。

---

## 8. 需要你决定的事

1. `D:\C\work_DC`（真实的旧目录）是否删除？建议先打包归档再删，
   因为它是唯一保留 `data_quality_report.json` 和两个 `run.log` 的位置。
2. 本次整理是否提交并推送到 GitHub？（按规则，push 需要你确认）
3. `crypto/out/demo.key` 等密钥是否需要在虚拟机之外备份？
4. 我为了核对只读地启动了 Ubuntu621，目前仍在运行。需要我关闭它吗？

---

## 9. 相关文档索引

| 内容 | 位置 |
| --- | --- |
| 仓库总入口 | `README.md` |
| 模块状态总表 | `PROJECT_STATUS.md` |
| 链路与端口 | `docs/architecture/network-topology.md` |
| 目标工作流 | `docs/architecture/workflow.md` |
| AES-256-GCM | `docs/crypto/aes-256-gcm.md` |
| 协议字段 | `docs/protocol/protocol-design.md` |
| 基础隐写 | `docs/steganography/basic-stego.md` |
| 数据集 | `docs/dataset/dataset-overview.md` |
| 数据质量报告 | `docs/experiments/data-quality-report.md` |
| 基线分析 | `docs/experiments/baseline-analysis.md` |
| 1D-CNN 结果 | `docs/experiments/1dcnn-results.md` |
| cWGAN-GP 现状 | `docs/experiments/cwgan-results.md` |
