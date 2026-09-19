# protocol_stego

授权实验环境下的“秘密数据传输协议 + 基础隐写调制”模块。

本模块复用已有资产：

- Docker 实验链：`Client → Proxy-A → Proxy-B → Server`；
- `newtry97` v0.2 帧格式常量（Preamble/Version/Frame ID/Length/CRC）；
- `crypto/` 中的 AES-256-GCM（不重新实现密码算法）。

本次新增：

- ciphertext → frame → bitstream → 基础长度调制；
- Proxy-A 按 bit 选择约 800/1200 字节的 application-layer write；
- Proxy-B 按实际 `recv()` 长度恢复 bit，解帧、重组、CRC 校验、AES 解密；
- 单元测试、最小端到端 Demo、JSONL 结构化日志。

## 目录

```text
protocol_stego/
├── README.md
├── IMPLEMENTATION_PLAN.md
├── protocol.md
├── architecture.md
├── experiment.md
├── config.yaml
├── requirements.txt
├── Dockerfile
├── compose.yaml
├── core/
│   ├── crc.py
│   ├── bitstream.py
│   ├── framing.py
│   ├── reassembly.py
│   ├── modulation.py
│   ├── config.py
│   └── crypto_adapter.py
├── proxy/
│   ├── sender_stego.py
│   ├── receiver_stego.py
│   └── jsonl_log.py
├── tests/
├── examples/
└── logs/, out/, data/
```

## 安装依赖

不需要在宿主机安装依赖，直接使用 Docker 镜像：

```bash
cd /home/urruna/docker/tcp-lab/protocol_stego
docker compose build
```

镜像内会安装 `cryptography` 与 `PyYAML`。

## 运行测试

```bash
docker compose run --rm tests python -m unittest discover -s tests -v
```

包含：

- Test 1：bitstream 往返；
- Test 2：单帧 `HELLO` 编解码；
- Test 3：超长数据多帧拆分/重组；
- Test 4：`10101` 长度调制与反解；
- Test 5：篡改字节后 CRC 必须失败；
- 端到端 Demo 测试。

## 运行 Demo

```bash
docker compose run --rm tests python examples/demo_secret_transfer.py
```

预期输出：

```text
PASS=True
total_bits=...
bit_error_count=0
ber=0.0
frame_count=...
received_frame_count=...
crc_failure_count=0
frame_error_rate=0.0
...
```

Demo 会在 `data/` 写入 `secret.txt`，在 `out/` 写入：

- `recovered_secret.txt`
- `experiment_summary.json`
- `sender_result.json` / `receiver_result.json` / `server_result.json`

## 本次验证结果

测试环境：Ubuntu6.21 + Docker Compose v2.27.1，
镜像 `protocol-stego:1`（Python 3.11 + cryptography + PyYAML）。

```text
20/20 unit tests: OK
end-to-end demo: PASS=True
secret_size=64
ciphertext_bytes=94
frame_count=1
total_bits=840
bit_error_count=0
ber=0.0
crc_failure_count=0
frame_error_rate=0.0
cover_bytes=825600
duration_ms≈9752
```

说明：Demo 中 `block_gap_ms=10`，目的是降低 TCP 把相邻 write 合并到一次
`recv()` 的概率；`length_out_of_range` 仍会被记录到 `errors.jsonl`，但不会静默
当作合法 bit。

## 实现注意

- Demo 侧与 Proxy-A 各自执行一次 AES-GCM，nonce 随机会使两边 bit 计划不同；
  Demo 因此多发送一段 cover 余量，并以 Proxy-A 实际发送的 bit 与字节数为准。
- Proxy-B 不假设“一次 recv = 一个 write”：先按 LOW/HIGH 范围积累，LOW 范围内
  再等待一个短 grace，以区分被 TCP 分段的 HIGH 块。
- 所有这些都只针对 application-layer write length，不是 TCP packet length。

## 数据集生成平台

新增目录：

```text
dataset/          # raw / processed / splits
scripts/          # run_experiment / dataset_builder / split_dataset / dataset_stats
docs/DATASET.md   # 数据集说明
```

使用方式：

```bash
docker compose run --rm tests python scripts/run_experiment.py \
  --mode both --normal 3 --stego 3 \
  --seed 42 --secret-size 16 --block-gap-ms 20 --window-size 128

docker compose run --rm tests python scripts/dataset_builder.py --window-size 128
docker compose run --rm tests python scripts/split_dataset.py --val-ratio 0.1 --test-ratio 0.1 --seed 42
docker compose run --rm tests python scripts/dataset_stats.py
```

本次 smoke test（3 normal + 3 stego）结果：

```text
sessions requested: normal=3, stego=3
sessions completed: normal=3, stego=3
sessions success:   normal=3, stego=3
X.shape = [18, 4, 128]
y.shape = [18]
class distribution: normal=9 windows, stego=9 windows
train/val/test sessions: 2 / 2 / 2
session overlap: none
NaN/Inf: false
BER=0.0, frame_error_rate=0.0, CRC failures=0
```

详细说明见 `docs/DATASET.md`。

## 常见错误

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `length outside LOW/HIGH` | TCP 合并/粘包，或 block_gap 太小 | 调大 `stego.block_gap_ms`，重跑 |
| `CRCMismatchError` | bit 恢复错误或帧损坏 | 检查调制边界与日志 `errors.jsonl` |
| `AES module not found` | 未挂载/复制 `crypto/` | 使用 compose 构建，或设置 `CRYPTO_MODULE` |
| `PreambleNotFoundError` | 帧起点丢失 | 检查 bit 数与 frame 编码长度 |

## 已知限制

- 第一版只实现长度调制，不实现 FEC、重传和错误纠正；
- Proxy-B 假设每个 application-layer 数据块可以被单独观察到；真实网络中 TCP 可能
  合并/分割，导致 `length_out_of_range`；
- 不控制 TCP packet length；
- 不实现 1D-CNN 或 cGAN。
