# 团队协作指南

## 获取项目

```bash
git clone <repository-url>
cd <repository>
```

建议先读：

1. `README.md`
2. `PROJECT_STATUS.md`
3. `docs/architecture/network-topology.md`
4. `TEAM_GUIDE.md`

## Docker 环境要求

- Docker 26.x
- Docker Compose v2
- 容器内 Python 3.11
- 拉取镜像需要网络（可能需要配置镜像加速）

## 运行基础链路

```bash
cd src/tcp_lab
docker compose up
```

预期输出：

```text
[client] received: hello network
[client] PASS: returned payload matches sent payload
```

## 运行正常文件下载链

```bash
cd src/normal_file_transfer
docker compose up --abort-on-container-exit --exit-code-from client
```

## 运行 protocol_stego 测试

```bash
cd src/protocol_stego
docker compose build
docker compose run --rm tests python -m unittest discover -s tests -v
```

预期：20 个测试全部通过。

## 运行端到端演示

```bash
cd src/protocol_stego
docker compose run --rm tests python examples/demo_secret_transfer.py
```

预期：`PASS=True`，BER=0，CRC 失败=0。

## 各部分在哪里

| 内容 | 位置 |
| --- | --- |
| 基础 Docker 链 | `src/tcp_lab/` |
| 正常文件下载链 | `src/normal_file_transfer/` |
| AES-256-GCM | `src/crypto/crypto.py` |
| 帧协议 | `src/protocol_stego/core/framing.py`、`src/newtry97/framing.py` |
| 基础隐写 | `src/protocol_stego/core/modulation.py`、`src/protocol_stego/proxy/` |
| 当前数据集 | `datasets/protocol_stego/` |
| 1D-CNN 模块 | `src/1dcnn/` |
| cWGAN-GP 模块 | `src/cWGAN-GP/` |
| 数据集发布包 | `releases/dataset_release_v1/` |
| 实验报告 | `docs/experiments/` |
| 规划文档 | `docs/planning/` |

## 未经明确同意不要修改

- AES-256-GCM 实现；
- 帧字段布局与 CRC 定义；
- Docker 网络拓扑与端口映射；
- 800/1200 基线调制；
- 原始实验数据（`dataset/raw/**`、历史 CSV 文件）；
- 数据集发布包内容；
- `src/1dcnn/` 中已训练的 checkpoint 与结果，除非明确重跑并重新记录。

如果发现 bug：

1. 先写清具体现象与证据；
2. 不要悄悄改写已有结果；
3. 新建独立分支或独立实验；
4. 在 `CHANGELOG.md` 中记录改动。

## 新工作应该放在哪里

- 新实验报告：`docs/experiments/`
- 新数据集发布：`releases/`
- 新代码实验：`src/` 下新建子目录
- 新分析脚本：`src/protocol_stego/scripts/`
- 临时笔记或探索：不要提交，放在 `scratch/`（已被 Git 忽略）

## 如何提交新的实验结果

1. 原始日志保持原样，不要改动。
2. 附一份简短的 Markdown 报告，包含：
   - 目的；
   - 执行的命令；
   - 环境；
   - 样本数量；
   - 指标；
   - 已知局限。
3. 大的 `.npz` / `.npy` / `.zip` 文件走 Git LFS 或 Release。
4. 绝对不要提交密钥、token、口令或私有凭证。
