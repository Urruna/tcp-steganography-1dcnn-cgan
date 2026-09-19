# REPOSITORY_PLAN

> Execution update: Phase 1 organization has been performed. The working
> protocol_stego dataset was moved to `datasets/protocol_stego/`; the
> container mount target remains `/work/protocol_stego/dataset`.

本文件只做 GitHub 仓库规划，**不执行任何移动、删除、重构或代码修改**。

审计依据：`PROJECT_AUDIT.md`（Windows `D:\C\work_DC` 与 Ubuntu
`/home/urruna/docker/tcp-lab`）。

---

## 0. 规划前提

### 0.1 当前实际位置

```text
Ubuntu: /home/urruna/docker/tcp-lab/
Windows: D:\C\work_DC\
```

用户描述中的 `~/tcp-lab` 在虚拟机中不存在。

### 0.2 Git 状态

实际检查：

- `D:\C\work_DC\.git`：不存在；
- Ubuntu `/home/urruna/docker/tcp-lab` 下没有 `.git`；
- 两边都没有现成 Git commit history。

因此：

- `CHANGELOG.md` 不能依据 commit history 编写；
- 只能依据项目文档、文件修改时间和实验记录谨慎整理，并标注来源。

### 0.3 当前目录的主要问题

1. 多个子项目平铺在 `tcp-lab/` 和 `D:\C\work_DC`。
2. `protocol_stego/` 同时包含源码、文档和 27 MB 数据。
3. `dataset_release/` 又复制了一份 protocol_stego 数据，仓库里会出现
   重复约 27 MB 的数据。
4. Windows 与 Ubuntu 都有副本，容易产生“哪个是权威版本”的问题。
5. 没有统一 README，新成员无法从根目录理解项目。

---

# 1. Repository Structure

建议仓库名（示例）：`authorized-tcp-stego-lab`。

```text
authorized-tcp-stego-lab/
│
├── README.md
├── PROJECT_STATUS.md
├── PROJECT_AUDIT.md
├── REPOSITORY_PLAN.md
├── CHANGELOG.md
├── TEAM_GUIDE.md
├── LICENSE_OR_USAGE.md
├── .gitignore
├── .gitattributes                 # Git LFS 规则（如果采用 LFS）
│
├── docs/
│   ├── architecture/
│   │   ├── project-overview.md
│   │   ├── network-topology.md
│   │   └── workflow.md
│   ├── crypto/
│   │   └── aes-256-gcm.md
│   ├── protocol/
│   │   └── protocol-design.md
│   ├── steganography/
│   │   └── basic-stego.md
│   ├── dataset/
│   │   ├── dataset-overview.md
│   │   ├── dataset-format.md
│   │   └── data-generation.md
│   ├── experiments/
│   │   ├── data-quality-report.md
│   │   ├── baseline-analysis.md
│   │   └── newtry97-v0.2.md
│   ├── planning/
│   │   ├── new_727.md
│   │   ├── docker_m1.md
│   │   └── work917.md
│   ├── audit/
│   │   └── project-audit.md
│   └── assets/
│       └── pictures/
│
├── src/
│   ├── tcp_lab/                  # 最早的 Docker 四容器 TCP echo 链
│   │   ├── client.py
│   │   ├── proxy.py
│   │   ├── echo_server.py
│   │   ├── batch_client.py
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   │
│   ├── normal_file_transfer/     # 当前 normal/ 文件下载链
│   │   ├── compose.yaml
│   │   ├── Dockerfile
│   │   ├── file_client.py
│   │   ├── file_server.py
│   │   ├── normal_proxy.py
│   │   ├── proxy.py               # 历史 asyncio 版本，保留但标注
│   │   └── make_files.py
│   │
│   ├── crypto/                   # 必须与 protocol_stego 保持兄弟目录
│   │   ├── crypto.py
│   │   ├── crypto_tool.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── compose.yaml
│   │
│   ├── newtry97/                 # v0.2 帧协议 + write-splitting demo
│   │   ├── framing.py
│   │   ├── event_log.py
│   │   ├── sender_proxy.py
│   │   ├── receiver_proxy.py
│   │   ├── covert_client.py
│   │   ├── echo_server.py
│   │   ├── run_demo.py
│   │   ├── container_client.py
│   │   ├── compose.yaml
│   │   └── Dockerfile
│   │
│   └── protocol_stego/           # 当前主协议 + 800/1200 基础隐写
│       ├── core/
│       ├── proxy/
│       ├── tests/
│       ├── examples/
│       ├── scripts/
│       ├── config.yaml
│       ├── requirements.txt
│       ├── Dockerfile
│       ├── compose.yaml
│       └── dataset/              # 第一阶段保留原位，避免改代码
│
├── datasets/
│   ├── README.md
│   ├── historical/
│   │   ├── docker_chain_smoke/
│   │   └── baseline_lenmix_v1/
│   ├── normal_v1/
│   └── protocol_stego/
│       ├── raw/
│       ├── processed/
│       ├── splits/
│       └── metadata/
│
├── releases/
│   ├── dataset_release_v1/
│   │   ├── README.md
│   │   ├── DATASET_CARD.md
│   │   ├── DATA_DICTIONARY.md
│   │   ├── DATASET_INTEGRITY.md
│   │   ├── LICENSE_OR_USAGE.md
│   │   ├── historical_normal/
│   │   ├── protocol_stego/
│   │   └── checksums/
│   └── dataset_release_v1.zip
│
└── tools/
    └── build_release/
        └── build_dataset_release.py
```

### 结构决策说明

1. `src/crypto` 和 `src/protocol_stego` 必须保持**兄弟目录关系**。
   原因：`protocol_stego/core/crypto_adapter.py` 通过
   `parents[2] / "crypto" / "crypto.py"` 定位 AES 模块。
2. `src/protocol_stego/dataset` 第一阶段**保留原位**。
   原因：脚本默认路径指向该目录；移动数据集需要改 compose 挂载和默认路径。
   第二阶段可迁到 `datasets/protocol_stego`，用已有
   `--raw-dir/--out-dir` 参数规避代码重构。
3. `dataset_release` 放入 `releases/`，它是交付产物，不是运行源码。
4. `newtry97` 保持独立，因为它的隐写策略是 write-splitting，
   不是 800/1200 长度调制。

---

# 2. 文件迁移关系

动作定义：

- **MOVE**：调整位置，内容不变。
- **COPY**：复制到仓库结构，原位置保留。
- **KEEP**：原样保留，不移动。
- **SPLIT**：目录拆分，代码与数据分离。

| 当前路径 | 目标位置 | 动作 | 说明 |
| --- | --- | --- | --- |
| Ubuntu tcp-lab `client.py/proxy.py/echo_server.py/batch_client.py/Dockerfile/docker-compose.yml` | `src/tcp_lab/` | COPY | 只有 Ubuntu 有；Windows 根目录需补齐 |
| Windows/Ubuntu `newtry97/` | `src/newtry97/` | MOVE/COPY | 整体移动即可，内部相对导入保持 |
| `newtry97/work917.md` | `docs/planning/work917.md` | COPY | 文档与代码分离 |
| `normal/` 代码 | `src/normal_file_transfer/` | SPLIT | compose/Dockerfile/py 保留 |
| `normal/` CSV 数据（client/proxy/server/dataset_summary） | `datasets/normal_v1/` | COPY | 保留原始 CSV，不改内容 |
| `normal/data.md` | `docs/dataset/normal-v1.md` | COPY | 文档 |
| `crypto/` 代码 | `src/crypto/` | MOVE/COPY | 与 protocol_stego 保持兄弟关系 |
| `crypto/crypto.md` | `docs/crypto/aes-256-gcm.md` | COPY | 需要扩写为更完整说明 |
| `crypto/out/` | `releases/` 或忽略 | COPY/IGNORE | 自检产物和 demo key，**不要提交 key** |
| `protocol_stego/core/proxy/tests/examples/scripts` | `src/protocol_stego/` | MOVE/COPY | 运行代码 |
| `protocol_stego/config.yaml` | `src/protocol_stego/config.yaml` | KEEP | 运行配置 |
| `protocol_stego/docs/*.md` | `docs/...` 对应目录 | COPY | 需要重写为教程型文档 |
| `protocol_stego/dataset/` | 第一阶段 `src/protocol_stego/dataset/` | KEEP | 避免路径改动 |
| `protocol_stego/dataset/` | 第二阶段 `datasets/protocol_stego/` | MOVE | 需同步修改 compose 挂载和默认参数 |
| `baseline_lenmix_v1/` | `datasets/historical/baseline_lenmix_v1/` | COPY | 历史基线数据 |
| Ubuntu `tcp-lab/logs/proxy_a_events.csv` / `proxy_b_events.csv` | `datasets/historical/docker_chain_smoke/raw/` | COPY | 原始保留；另建规范化 early 视图 |
| `dataset_release/` | `releases/dataset_release_v1/` | COPY | 已生成交付包 |
| `dataset_release.zip` | `releases/dataset_release_v1.zip` | COPY | GitHub 可用 Release Asset |
| `picture/` | `docs/assets/pictures/` | COPY | 文档截图 |
| `new_727.md` | `docs/planning/new_727.md` | COPY | 架构参考文档 |
| `new_727.pdf` | `docs/planning/new_727.pdf` | COPY | 可选；PDF 较大可放 Release |
| `Docker_m1.md` | `docs/planning/docker_m1.md` | COPY | 早期环境记录 |
| `newtry97.md` | `docs/experiments/newtry97-v0.2.md` | COPY | 实验记录 |
| `PROJECT_AUDIT.md` | 根目录或 `docs/audit/project-audit.md` | KEEP/COPY | 建议根目录保留入口，docs 保留副本 |

---

# 3. 文档结构

必建文档与内容来源：

| 目标文档 | 内容来源 | 主要依据 |
| --- | --- | --- |
| `README.md` | 新写入口，汇总审计与代码事实 | PROJECT_AUDIT + 代码 |
| `PROJECT_STATUS.md` | 状态表 | PROJECT_AUDIT 最终状态表 |
| `docs/architecture/project-overview.md` | 研究目标、双线结构 | new_727.md + PROJECT_AUDIT |
| `docs/architecture/network-topology.md` | Client/A/B/Server、端口、网络 | compose 文件 + 代码 |
| `docs/architecture/workflow.md` | Normal→Stego→Dataset→CNN→cGAN | new_727.md；标注完成/规划 |
| `docs/crypto/aes-256-gcm.md` | 算法、key、nonce、tag、API | crypto/crypto.py + crypto.md |
| `docs/protocol/protocol-design.md` | 帧格式、异常、重组 | framing.py + protocol.md |
| `docs/steganography/basic-stego.md` | 800/1200 调制、日志、限制 | modulation.py + sender/receiver |
| `docs/dataset/dataset-overview.md` | 所有数据集清单 | dataset_release 文档 + 实际统计 |
| `docs/dataset/dataset-format.md` | JSONL/CSV/NPY 字段 | 实际文件读取结果 |
| `docs/dataset/data-generation.md` | 生成流程、脚本、命令 | session_runner/run_experiment |
| `CHANGELOG.md` | 阶段记录 | 文件时间 + 项目文档（无 Git history） |
| `TEAM_GUIDE.md` | 协作说明 | 运行命令与目录约定 |

文档编写规则：

- 明确区分 “已完成 / 部分完成 / 设计阶段 / 未实现”。
- 不把 new_727.md 的规划写成已完成。
- 所有数据集数字必须重新读取实际文件后填写。

---

# 4. 原样保留（KEEP）

以下文件/目录内容不得改动：

- 所有已有 `.py` 源码的算法逻辑；
- `crypto/crypto.py`、`crypto_tool.py`；
- `protocol_stego/core/framing.py`、`modulation.py`、`bitstream.py`、
  `crc.py`、`reassembly.py`；
- `protocol_stego/proxy/sender_stego.py`、`receiver_stego.py`；
- `newtry97/framing.py` 及 sender/receiver；
- 所有 Dockerfile / compose 的网络与端口定义；
- `protocol_stego/dataset/raw/**` 原始 JSONL 与 metadata；
- `dataset_release/**` 已交付内容；
- `baseline_lenmix_v1/**`；
- 历史 CSV 日志。

允许的仓库整理动作只有：

- 复制；
- 移动（移动后保持文件内容 sha256 不变）；
- 新增文档；
- 新增 `.gitignore` / `.gitattributes`。

---

# 5. 需要复制（COPY）

建议复制进仓库的内容：

1. Ubuntu 独有的 `tcp_lab` 基础链源码。
2. Ubuntu `tcp-lab/logs/` 中早期 Docker Normal 原始 CSV。
3. `baseline_lenmix_v1/` 历史数据。
4. `normal/` 的 CSV 数据与 `dataset_summary.json`。
5. `protocol_stego/dataset/raw/processed/splits/metadata`。
6. `dataset_release/` 和 `dataset_release.zip` 到 `releases/`。
7. `new_727.md`、`Docker_m1.md`、`newtry97.md` 等文档。
8. `picture/` 截图到 `docs/assets/pictures/`。

复制时必须：

- 保持文件字节不变；
- 不使用编辑器重新格式化 JSON/CSV；
- 不改变 timestamp、length、session_id。

---

# 6. 实验产物（Experiment Artifacts）

以下内容属于实验产物，不是核心源码：

| 目录/文件 | 类型 | 是否建议提交 |
| --- | --- | --- |
| `protocol_stego/dataset/raw/**` | 原始实验数据 | 是（LFS 或 Release） |
| `protocol_stego/dataset/processed/**` | 窗口化数据集 | 是（LFS 或 Release） |
| `protocol_stego/dataset/splits/**` | 划分结果 | 是（LFS 或 Release） |
| `dataset_release/**` | 交付包 | 是（Release 优先） |
| `dataset_release.zip` | 交付压缩包 | Release Asset |
| `normal/*.csv` | 实验 CSV | 是 |
| `normal/files/**` | 生成的测试文件 | 可选（可由脚本重建） |
| `newtry97/logs/**` | demo 日志 | 可选 |
| `protocol_stego/logs/**` | 运行日志 | 可选 |
| `protocol_stego/out/**` | demo 输出 | 可选 |
| `crypto/out/**` | 加密自检输出 | 报告可提交，key 不可提交 |
| `baseline_lenmix_v1/**` | 历史数据 | 是 |
| Ubuntu `tcp-lab/logs/**` | 历史 Docker Normal | 是 |

实验产物提交规则建议：

- 小型 CSV/Markdown 直接 Git；
- `*.npz`、`*.npy`、`*.zip`、`*.pcap`、大于 5–10 MB 的二进制用 Git LFS；
- 交付 zip 放 GitHub Releases，仓库中保留 manifest 和 SHA256。

---

# 7. 不应该提交 GitHub 的内容

- `.git/`
- `__pycache__/`
- `*.pyc` / `*.pyo`
- `.venv/` / `venv/` / `env/`
- Docker image 导出文件（`*.tar`, `*.tar.gz` 中的镜像）
- `/tmp` 临时文件
- 编辑器缓存：`.idea/`, `.vscode/`（如需共享配置，单独提交 `settings.json`）
- 操作系统垃圾：`.DS_Store`, `Thumbs.db`
- 密钥和凭据：
  - `*.key`
  - `*.pem`
  - `*.p12`
  - `crypto/out/demo.key`
  - 任何 `session.key`
  - `.env`
  - SSH private key
- 大体积无关文件：
  - 虚拟机磁盘 `*.vmdk`
  - VMware `*.vmem`
  - `*.vmx` 中可能包含本机路径信息（建议不提交）
- `normalTraffic.zip`：当前内容极小，来源和用途未确认，提交前需确认内容；
  建议先放 `datasets/incoming/` 或 release，而不是直接进源码树。

---

# 8. `.gitignore` 建议内容

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Virtual environments
.venv/
venv/
env/

# Docker / local runtime
*.log
docker-compose.override.yml

# Secrets and keys
*.key
*.pem
*.p12
*.crt
.env
.env.*

# Editor / OS
.idea/
.vscode/
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak
*.swp
*~

# VMware / VM disks
*.vmdk
*.vmem
*.vmsn
*.vmss
*.nvram

# Local extracted packages
*.tgz
*.tar.gz

# Generated cache
.cache/

# Local experiment scratch
tmp/
scratch/
```

注意：

- 不要忽略 `dataset_release.zip` 如果已经决定用 Git LFS 管理；
- 不要忽略所有 `logs/`，因为部分日志是项目证据；建议按具体路径忽略临时日志。
- `crypto/out/*.enc` 可以提交作为示例，`crypto/out/*.key` 必须忽略。

---

# 9. `.gitattributes` / Git LFS 建议

如果决定把数据集放进仓库，建议：

```gitattributes
*.npz filter=lfs diff=lfs merge=lfs -text
*.npy filter=lfs diff=lfs merge=lfs -text
*.zip filter=lfs diff=lfs merge=lfs -text
*.bin filter=lfs diff=lfs merge=lfs -text
*.pcap filter=lfs diff=lfs merge=lfs -text
*.csv text eol=lf
*.json text eol=lf
*.jsonl text eol=lf
*.md text eol=lf
*.py text eol=lf
```

如果不使用 LFS，则把 27 MB 级数据集放到 GitHub Releases，
仓库只保留：

- 数据说明；
- SHA256；
- 下载脚本；
- 数据生成脚本。

---

# 10. 迁移阶段建议

## Phase 1（仓库初始化）

- 新建空 GitHub 仓库；
- 复制代码到 `src/`；
- 保留 `protocol_stego/dataset` 原位；
- 新增根 README / STATUS / TEAM_GUIDE；
- 新增 `.gitignore`；
- 不迁移数据集到顶层，避免路径破坏。

## Phase 2（数据与发布）

- 将 `dataset_release/` 放到 `releases/`；
- 把 `dataset_release.zip` 作为 GitHub Release Asset；
- 如需把工作数据集移出 `src/`，改用已有 CLI 参数：
  `--raw-dir/--out-dir`；
- 更新 compose 挂载路径。

## Phase 3（协作规范）

- 建立分支规范与 PR 流程；
- 建立实验命名规范；
- 建立新的实验结果提交模板。

---

# 11. 需要人工确认的问题

1. 数据集是否使用 Git LFS，还是只放 Releases？
2. `protocol_stego/dataset` 是保留在代码目录还是迁到顶层 `datasets/`？
3. `normalTraffic.zip` 的内容和用途是什么？
4. 两类 Normal 数据（historical / protocol）是否分别发布？
5. `newtry97` 是否作为独立历史实验保留，还是只保留一份文档说明？
6. 是否需要把 `dataset_release` 与 `protocol_stego/dataset` 去重？

在得到确认前，不执行大规模移动。

---

# 12. 计划完成后的验证清单

- [ ] 所有 `.py` 文件内容 SHA256 与迁移前一致。
- [ ] Docker compose 配置仍能 `docker compose config` 通过。
- [ ] `protocol_stego` 单元测试仍为 20/20 OK。
- [ ] `X.npy` / `y.npy` shape 仍为 `[138,4,128]` / `[138]`。
- [ ] dataset_release 的 `SHA256SUMS.txt` 可复核。
- [ ] README 不把规划写成已完成。
- [ ] `.gitignore` 未忽略必须提交的实验证据。
- [ ] GitHub 仓库不包含密钥、密码、虚拟磁盘和 cache。
