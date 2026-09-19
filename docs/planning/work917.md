# work917 实施记录：容器化 A/B 通信链

日期：2026-09-17

## 0 项目目标重述

本项目研究的是：在**封闭、授权的实验环境**中，利用代理转发时的
**应用层写入分块与时间节奏**携带秘密信息，并用 1D-CNN/cGAN 评估这种
隐蔽信道的可靠性与可检测性。

最终目标不是只让一条消息穿过代理，而是建立一套可重复的工程平台：

- 固定拓扑：`Client → Proxy-A → Proxy-B → Server`；
- 业务字节不变，只调制应用层 write 的分块/间隔；
- Proxy-B 能从事件流中恢复帧，支持滑窗同步、Frame ID、CRC 与重同步；
- 每个节点输出结构化 CSV 日志，供后续特征提取与模型训练；
- 支持 Normal / Baseline-Stego / GAN-Stego 三组对照实验；
- 用 BER、FER、时延、吞吐、检测 AUC/F1 等指标做权衡分析。

此前 v0.2 已实现：32 bit Preamble、Version/Frame ID/Length/CRC、
滑窗解码、CRC 失败重同步，以及 Proxy-A/B 结构化日志。

本日工作目标：把单机多进程 demo 改造成**多容器 A/B 通信链**，
为后续容器化实验、抓包与数据采集做准备。

## 1 步骤 1：确认并补齐 Docker 环境

环境：Ubuntu6.21（VMware），Ubuntu 20.04.6 LTS，内核 5.15.0-140。

检查结果：

- `docker.io 26.1.3` 已安装，`docker` 服务 `active`、开机自启 `enabled`；
- 用户 `urruna` 已在 `docker` 组，可免 sudo 执行 Docker；
- 原有 `docker-compose 1.25.0` 可用，但没有 `docker compose` 插件。

补装：

```bash
sudo apt-get update
sudo apt-get install -y docker-compose-v2 docker-buildx
```

结果：

- `Docker Compose version 2.27.1`
- `docker buildx 0.14.1`

Docker Hub 直连超时，因此在 `/etc/docker/daemon.json` 中加入镜像加速：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://docker.1panel.live"
  ],
  "log-driver": "json-file",
  "log-opts": {"max-size": "10m", "max-file": "3"}
}
```

原配置备份为 `/etc/docker/daemon.json.bak-20260917`。
重启 Docker 后验证：

- `docker pull hello-world` 成功；
- `docker run --rm hello-world` 成功；
- 原有 `tcp-lab/docker-compose.yml` 可被 `docker compose config` 解析，
  且 `docker compose build` 成功；
- 短暂 `up` 后 client 输出 `PASS: returned payload matches sent payload`，
  随后 `down` 清理容器与网络。

## 2 步骤 2：容器化设计

容器拓扑沿用现有实验链：

```text
client ──client_net──> proxy_a ──backbone_net──> proxy_b ──server_net──> server
```

- `client_net`、`backbone_net`、`server_net` 均设为 `internal: true`；
- 每个节点一个容器，使用同一个 `newtry97-node:917` 镜像；
- Proxy-A/B 通过同一个宿主机目录 `newtry97/logs/docker917` 写日志；
- 容器内使用服务名寻址：`proxy_a`、`proxy_b`、`server`；
- 默认秘密消息仍为 `Hello from A to B (newtry97)`，Frame ID 改为 `917`。

## 3 步骤 3：新增容器化文件

- `Dockerfile`：`python:3.11-slim` + 项目代码；
- `compose.yaml`：定义 server / proxy_a / proxy_b / client 四个服务；
- `container_client.py`：容器化客户端入口，等待 Proxy-A 就绪并自动计算
  cover 行数（当前默认：16 + 312 + 16 = 344 行）；
- `.dockerignore`：排除日志、缓存和打包文件。

## 4 步骤 4：构建与运行

执行命令：

```bash
cd /home/urruna/docker/tcp-lab/newtry97
docker compose build
docker compose up -d
# 等待 client 容器退出
docker compose logs client
docker compose logs proxy_a proxy_b server
docker compose down
```

实际结果：

- `docker compose build`：成功，镜像 `newtry97-node:917`；
- `docker compose up -d`：四个容器全部创建并启动；
- client 容器退出码 0，输出：

```text
[container_client] frame_bits=312 lines=344 echo=344/344
```

- Proxy-B 输出：

```text
[proxy_b] RECOVERED 312 bits | frame_id=917 | payload='Hello from A to B (newtry97)' | crc=ok
```

- `docker compose down`：成功，容器与本次创建的网络已清理，镜像保留。

运行中修复的两个问题：

1. compose 的 client 服务最初没有指定 `command`，会落到镜像默认的
   `run_demo.py`；已改为 `python container_client.py`。
2. `sender_proxy.py` 构造帧时最初没有把 `--frame-id` 传给
   `build_frame()`，导致恢复端看到 `frame_id=0`；已改为
   `build_frame(message, frame_id=frame_id)`。

## 5 步骤 5：日志与数据校验

容器内代理日志通过 volume 写到虚拟机：

```text
/home/urruna/docker/tcp-lab/newtry97/logs/docker917/
├── proxy_a_events.csv
├── proxy_b_events.csv
└── recovered.txt
```

本次容器链结果：

| 项目 | 结果 |
| --- | --- |
| 帧 ID | `917` |
| 秘密消息 | `Hello from A to B (newtry97)` |
| 帧比特数 | 312 bit |
| client cover 行数 | 344 行（16 普通 + 312 编码 + 16 普通） |
| client Echo 校验 | 344/344 |
| CRC-16 | 通过 |
| Proxy-A 日志 | 822 行（forward 478、reverse 344） |
| Proxy-B 日志 | 822 行（forward 478、reverse 344） |
| 从 CSV 反解结果 | Proxy-A/Proxy-B 均恢复出 `frame_id=917` 与正确 payload |

## 6 当前状态与下一步

当前已经完成：Docker 环境、Compose v2、buildx、镜像加速、单镜像四节点
容器链、共享日志目录与一次完整端到端验证。

下一步建议：

1. 把 Proxy-A 的固定中间拆分/固定间隔抽成 scheduler，支持随机拆分点与
   随机间隔；
2. 增加 Normal（不编码）与 Baseline-Stego 两个 compose profile 或
   环境变量开关，用于批量采集对照数据；
3. 在容器网络中接入 tcpdump/capture 容器，验证网络层可观测性与
   应用层日志的一致性；
4. 基于 `logs/docker917` 的 CSV 写数据集构建脚本，切 64/128 事件窗口，
   为 1D-CNN/cGAN 训练做准备。
