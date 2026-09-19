# IMPLEMENTATION_PLAN

日期：2026-09-19

## 1 现有资产检查

当前虚拟机 `/home/urruna/docker/tcp-lab/` 下已有：

| 资产 | 位置 | 可复用内容 |
| --- | --- | --- |
| 正常 Docker 实验链 | `normal/` | Client → Proxy-A → Proxy-B → Server 的容器编排、健康检查、普通代理日志 |
| v0.2 帧协议 | `newtry97/framing.py` | 32 bit Preamble `0x6E9797A1`、Version、Frame ID、Payload Length、CRC-16/XMODEM、滑窗同步 |
| v0.2 比特/调制参考 | `newtry97/` | `bytes_to_bits`、`bits_to_bytes`、Proxy-A/B 结构 |
| AES-256-GCM | `crypto/` | `encrypt()` / `decrypt()`、固定 30 B 开销、`pad_to` 固定长度模式 |

本任务不重做 Docker 网络，不重写 AES-256-GCM。

## 2 本次实现范围

新增独立目录（与 `normal/`、`crypto/` 同层级）：

```text
protocol_stego/
```

实现：

1. `core/`：CRC、bitstream、frame 编解码、Frame 重组、长度调制、配置、crypto 适配；
2. `proxy/`：`sender_stego.py`（Proxy-A）与 `receiver_stego.py`（Proxy-B）；
3. `tests/`：Bitstream、Frame、CRC、Modulation、端到端测试；
4. `examples/demo_secret_transfer.py`：最小端到端 Demo；
5. `config.yaml`：协议、调制、日志参数；
6. JSONL 结构化日志：`logs/sender.jsonl`、`logs/receiver.jsonl`、`logs/errors.jsonl`；
7. 文档：`README.md`、`protocol.md`、`architecture.md`、`experiment.md`。

## 3 协议决策（复用 v0.2）

帧格式沿用 `newtry97` v0.2 定义：

```text
| Preamble(4B) | Version+Reserved(1B) | Frame ID(2B) |
| Payload Length(2B) | Payload | CRC-16(2B) |
```

- Preamble：`0x6E9797A1`（big-endian 写入）；
- Version：`1`（高 4 bit，低 4 bit 保留为 0）；
- Frame ID：16 bit 无符号，范围 `0..65535`；
- Payload Length：16 bit 无符号，最大由 `config.yaml` 配置；
- CRC：CRC-16/XMODEM，覆盖 Preamble 之后的 Version/Frame ID/Length/Payload；
- 多帧结束约定：除最后一帧外 payload 均为 `max_payload_size`；如果密文长度刚好整除，
  发送端追加一个 payload 为 0 的终止帧。

## 4 隐写调制决策

第一版只实现 application-layer write length 调制：

```yaml
stego:
  low_length: 800
  high_length: 1200
  tolerance: 80
```

- 0 → `[720, 880]`；
- 1 → `[1120, 1280]`；
- 两个范围不重叠，否则启动时报错；
- 调制只改变 Proxy-A 的 `sendall()` 分块长度；
- 不假设它等于 TCP packet length；
- Proxy-B 通过实际 `recv()` 长度落在哪个范围恢复 bit，范围外记录 error。

## 5 端到端流程

```text
secret.txt
 → AES-256-GCM
 → ciphertext
 → split frames
 → encode frames
 → bitstream
 → Proxy-A 按 bit 选择 800/1200 B 写块
 → TCP
 → Proxy-B 根据 recv 长度恢复 bit
 → byte stream
 → frame decode
 → reassemble
 → AES-256-GCM decrypt
 → recovered_secret.txt
```

Client/Server 仍只处理正常 cover 字节，业务字节不被修改。

## 6 验证步骤

1. Test 1：`10101010` 的 bits → bytes → bits 往返；
2. Test 2：`b"HELLO"` 的 encode → decode → CRC PASS；
3. Test 3：超长 ciphertext 的 split → encode → decode → reassemble；
4. Test 4：`10101` 的长度调制与反解；
5. Test 5：篡改一字节后必须 CRC FAIL；
6. 端到端 Demo：比较原 secret 与 recovered_secret，输出
   bit 数、BER、Frame 数、CRC failure、FER、耗时、吞吐量。

## 7 运行方式

测试与 Demo 统一在 Docker 容器中运行，容器内复用
`crypto/` 与 `protocol_stego/`：

```bash
cd /home/urruna/docker/tcp-lab/protocol_stego
docker compose build
docker compose run --rm tests python -m unittest discover -s tests -v
docker compose run --rm tests python examples/demo_secret_transfer.py
```

## 8 明确不做的内容

- 不实现 1D-CNN；
- 不实现 cGAN；
- 不实现 FEC/重传；
- 不直接控制 TCP segment size；
- 不修改已有正常 Docker 网络的业务逻辑。
