# 变更记录

## 关于证据的说明

本文件创建时项目还没有 Git 仓库和提交历史
（`D:\C\work_DC\.git` 不存在；Ubuntu 的 `tcp-lab` 也没有 `.git`）。

因此本记录的依据是：

- 项目中的 Markdown 文档；
- 文件修改时间；
- 真实的执行记录与报告。

下面的日期是依据证据推断的，不是提交日期。

## 2026-07-28

- 新增 `new_727.md` / `new_727.pdf`：项目研究计划与架构。
- 提出目标工作流：Normal → Baseline-Stego → GAN-Stego，
  以及 1D-CNN 与 cGAN。

来源：`docs/planning/new_727.md`、文件时间戳。

## 2026-07-29

- 新增 `Docker_m1.md`：早期 Docker / TCP 实验记录。
- 新增早期 `baseline_lenmix_v1` 数据：
  256 个 client 事件，512 个 Proxy-A 事件，512 个 Proxy-B 事件。
- 新增早期 Docker Normal 冒烟数据：
  13 字节的 `hello network`，2 个代理侧 session，4 个事件。

来源：`docs/planning/docker_m1.md`、
`datasets/historical/baseline_lenmix_v1/`、
`datasets/historical/docker_chain_smoke/`。

## 2026-09-07 至 2026-09-08

- 新增 `newtry97` v0.1 / v0.2：
  - 基于行的 cover 业务；
  - Preamble / Version / Frame ID / Length / CRC；
  - 滑动窗口搜索 Preamble；
  - 写拆分隐写；
  - 端到端演示与日志。
- 新增容器化的 `newtry97` 链与 `work917.md`。

来源：`docs/experiments/newtry97-v0.2.md`、
`docs/planning/work917.md`、`src/newtry97/`。

## 2026-09-17

- 在 Ubuntu6.21 上配置 Docker 环境：
  Compose v2、buildx、镜像加速、daemon DNS 与日志轮转。
- 新增 `normal` 文件传输链与 `normal_v1` 数据集：
  8 次下载，client / proxy / server 的 CSV 日志，共 3,082,890 字节。
- 新增 `data.md` 实验记录。

来源：`src/normal_file_transfer/data.md`、
`datasets/normal_v1/`、`docs/planning/work917.md`。

## 2026-09-18 至 2026-09-19

- 新增 `crypto` 模块：
  AES-256-GCM、PBKDF2 密钥派生、固定 30 字节开销、自检。
- 新增 `protocol_stego`：
  帧编解码、CRC、比特流、重组、800/1200 调制、
  Proxy-A/B、JSONL 日志、单元测试与端到端演示。
- 协议数据集扩到 23 个 Normal + 23 个 Stego session。
- 构建处理后数据集：
  `X=[138,4,128]`、`y=[138]`，按 session 划分。
- 新增数据质量报告与规则 / 逻辑回归基线。
- 构建 `dataset_release_v1` 与 SHA256 校验和。

来源：`docs/experiments/`、
`src/protocol_stego/docs/`、`releases/dataset_release_v1/`。

## 仓库整理

- 源码统一整理到 `src/`；
- 文档统一整理到 `docs/`；
- 数据统一整理到 `datasets/` 与 `releases/`；
- 新增根目录的 README / 状态表 / 团队指南 / 迁移记录。

本次整理没有改动任何算法、AES、协议、Docker 网络或数据集内容。
详见 `docs/migration-notes.md`。

## 2026-09-19 – 1D-CNN 模块

- 新增独立的 1D-CNN 交付物 `src/1dcnn/`：
  两层 1D-CNN、训练与评估脚本、冻结推理接口、逻辑回归与规则基线、
  已训练权重、结果文件与图表。
- 该模块使用另一套 168 窗口数据：
  `train=117（32 Normal / 85 Stego）`、
  `val=26（6/20）`、`test=25（10/15）`。
- 记录的软件测试：6 项全部通过。
- 报告的测试对比：
  CNN accuracy 0.9200 / F1 0.9375 / ROC-AUC 0.9867；
  逻辑回归 accuracy 0.8800 / F1 0.8889 / ROC-AUC 1.0000；
  规则基线 accuracy 0.8800 / F1 0.8889。
- 该数据集没有 session 索引，session 隔离**未经验证**。
  168 个窗口与 `datasets/protocol_stego` 的窗口精确重叠为 0，
  两者不得静默合并。

来源：`src/1dcnn/README.md`、`src/1dcnn/results/result_report.md`、
`src/1dcnn/results/software_tests.txt`。

## 2026-09-21 – cWGAN-GP 模块

- 新增 `src/cWGAN-GP/`：一个条件 WGAN-GP，生成器只输出应用层长度通道
  `[B, 128]`，并投影到两个互不重叠的长度区间，另附
  `README_cWGAN.md`。
- 该模块明确要求至少 **1000 个训练窗口**。当时只有 114 个训练窗口，
  Critic 与 Generator 的 loss 都单调爆炸，没有产出 checkpoint，也没有
  生成任何数据。

来源：Git 提交 `6840169`（"Add cWGAN-GP module and README"），
这也是本记录中第一条直接取自 Git 历史、而非文件时间的条目。

## 2026-09-26 – 数据集扩容到 466 个 session

没有改动任何协议、调制、加密或 Docker 定义。

- 在 Ubuntu6.21 虚拟机上，用与最初 23 + 23 完全相同的参数
  （`seed=42`、`secret_size=16`、`block_gap_ms=20`、`window_size=128`）
  新采了 210 个 Normal 与 210 个 Stego session。
- 有 8 个 Stego session 出现此前已记录过的 `length_out_of_range`
  （接收端把两次代理写入合并观测成 1600/2000 字节）。它们没有被删除，
  而是移到虚拟机的 `protocol_stego/raw_failed/stego/`，并补采新 session
  直到 233 个 Stego session 全部成功。
- 重建处理后数据集与划分：

  ```text
  session：466（233 Normal + 233 Stego，全部成功）
  窗口：   1398（699 / 699），X = [1398, 4, 128]
  划分：   train 374 session / 1122 窗口
           val    46 session /  138 窗口
           test   46 session /  138 窗口
  ```

- 重新生成 `DATA_QUALITY_REPORT.md`（结论 `READY_FOR_CNN`）、
  `BASELINE_ANALYSIS.md`、`stats.json`、`build_summary.json` 与图表。
  BER、帧错误率、CRC 失败率均为 0；无 session 重叠、无重复样本、
  无 NaN/Inf。
- 重建 `raw/run_summary.json`：因为两个并行采集进程都会各自覆盖该文件，
  所以改为按所有 session 的 `metadata.json` 聚合生成。
- 整个过程、被隔离的 session id 以及仍然存在的局限，记录在
  `docs/experiments/dataset-scaleup-20260926.md`。

对 cWGAN-GP 的影响：1000 训练窗口的门槛已经满足（现有 1122 个训练窗口）。
但由于数据接口不一致，仍然无法直接训练，详见
`docs/experiments/cwgan-results.md`。

## 2026-09-26 – 项目汇总与状态复核

本次没有改动任何算法、数据集或 Docker 定义。

- 把 GitHub 仓库克隆到 OS 的 projects 目录：`projects/tcp-steganography`。
- 以只读方式核对 Ubuntu6.21 虚拟机中的项目目录
  （`/home/urruna/docker/tcp-lab`，1162 个文件）：没有任何 2026-09-20
  之后修改的文件，也没有 `1dcnn` 或 `cWGAN-GP` 目录，没有任何仓库里
  缺失的成果。
- 比对本地旧副本（`D:\C\work_DC`，提交 `01f8304`）：多出的文件只有 4 个
  有意忽略的产物（两个 19.7 MB 的 `data_quality_report.json`，以及两个
  `*.log`）。
- 新增 `PROJECT_REVIEW.md`：中文总览，包含三个来源的合并结果、
  真实进展与优先级方案。
- 新增 `docs/experiments/cwgan-results.md`：说明 cWGAN-GP 模块实际包含
  什么、数据量门槛，以及已核实的数据接口不一致。
- 修正 cGAN 的状态：从 `Design` 改为 `Partial`，涉及 `PROJECT_STATUS.md`、
  `README.md`、`docs/architecture/workflow.md` 与
  `docs/architecture/project-overview.md`。

## 2026-09-29 – 状态文档同步到最新进展

- 状态文档同步到最新进展：数据集 466 个 session / 1398 个窗口、
  训练集 1122 个窗口。
- 修正了文档中已过时的说法，例如「cGAN 受限于数据量」（现已改为
  「受限于数据接口」）。


