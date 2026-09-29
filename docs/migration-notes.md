# 迁移记录

本文件记录在整理仓库过程中发现的各种差异。

## Git 历史

- Windows `D:\C\work_DC\.git`：当时不存在。
- Ubuntu `/home/urruna/docker/tcp-lab`：没有 `.git` 目录。

当时没有可用于比对的提交历史。

## 比对过的目录

以下目录在 Windows 与 Ubuntu 两边都存在：

```text
crypto/
normal/
newtry97/
protocol_stego/
```

比对方式是 SHA256 清单（Ubuntu 用 `sha256sum`，Windows 用 Python
`hashlib`）。

## 只在 Ubuntu 存在的文件

- `crypto/out/crypto_selftest.json`
- `crypto/out/*.enc` 演示密文
- `newtry97/__pycache__/*`（缓存，不提交）
- `newtry97/logs/docker917/proxy_a_events.csv`
- `newtry97/logs/docker917/proxy_b_events.csv`
- `newtry97/logs/docker917/recovered.txt`
- `normal/files/manifest.json`
- `normal/files/report_small.txt`
- `normal/files/report_medium.txt`
- `normal/files/report_large.bin`
- `normal/logs/client_events.csv`
- `normal/logs/dataset_summary.json`
- `normal/logs/proxy_a_events.csv`
- `normal/logs/proxy_b_events.csv`
- `normal/logs/server_events.csv`
- `protocol_stego/out/client_result.json`
- `protocol_stego/out/demo_config.yaml`
- `protocol_stego/out/demo_key.bin`
- `protocol_stego/out/server_result.json`

处理方式：

- Docker917 日志复制到 `src/newtry97/logs/docker917/`；
- normal 文件复制到 `datasets/normal_v1/files/`；
- normal 的 CSV 数据复制到 `datasets/normal_v1/logs/`（内容一致，已用
  SHA256 校验）；
- 加密模块自检产物复制到 `docs/experiments/crypto-selftest/`；
  `demo.key` 没有复制进仓库。

## 只在 Windows 存在的文件

- `normal/client_events.csv`
- `normal/dataset_summary.json`
- `normal/proxy_a_events.csv`
- `normal/proxy_b_events.csv`
- `normal/server_events.csv`
- `normal/normalTraffic.zip`
- `protocol_stego/dataset/processed/.gitkeep`
- `protocol_stego/dataset/raw/normal/.gitkeep`
- `protocol_stego/dataset/raw/stego/.gitkeep`
- `protocol_stego/dataset/splits/.gitkeep`
- `protocol_stego/docs/plots/.gitkeep`
- `protocol_stego/scripts/build_dataset_release.py`

说明：

- Windows 下的 `normal/*.csv` 与 Ubuntu 下的 `normal/logs/*.csv` 逐字节
  相同（已用 SHA256 确认）；
- `build_dataset_release.py` 是只在 Windows 侧存在的工具，已复制到
  `tools/build_release/`；
- `normalTraffic.zip` 的用途当时未确认，已按用户要求删除（确认无用）。

## 同名路径但内容不同

以下路径两边都存在，但哈希不同：

```text
protocol_stego/data/secret.txt
protocol_stego/logs/receiver.jsonl
protocol_stego/logs/sender.jsonl
protocol_stego/out/experiment_summary.json
protocol_stego/out/receiver_result.json
protocol_stego/out/recovered_secret.txt
protocol_stego/out/sender_result.json
```

差异来自不同的 demo 运行（随机秘密 / 密钥不同，或后续重跑）。
迁移过程中没有覆盖任何文件，两边原始文件都保留在各自环境中。

## 路径决策

- `src/crypto` 与 `src/protocol_stego` 保持同级，这样
  `core/crypto_adapter.py` 仍能解析 `../crypto/crypto.py`；
- 工作数据集从 `src/protocol_stego/dataset` 移到
  `datasets/protocol_stego`，以便代码与数据清晰分离。容器内挂载目标仍是
  `/work/protocol_stego/dataset`，因此容器内脚本的运行路径不变；
- `releases/dataset_release_v1/` 是交付产物，不是运行时源码；
- 历史数据与协议数据集保持隔离；
- Ubuntu 运行目录 `/home/urruna/docker/tcp-lab` 被有意保留：它被用作
  Ubuntu 独有文件的来源，这些文件已复制进本仓库。没有删除或移动任何
  Ubuntu 实验数据。

## 其他

- 大的 `data_quality_report.json` 文件有意不放进 Git 仓库：它们仍保留在
  磁盘上，以及发布压缩包中。
- 2026-09-26 起，工作数据集已扩容到 466 个 session，详见
  `docs/experiments/dataset-scaleup-20260926.md`。
