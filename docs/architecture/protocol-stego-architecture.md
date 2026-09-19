# 架构说明

## 1 节点

```text
Client ──> Proxy-A ──> Proxy-B ──> Server
  cover      调制        恢复/解密     正常业务
```

- Client：发送正常 cover 字节流；
- Proxy-A：透明转发 + 根据 secret bit 决定 write 块长度；
- Proxy-B：观察 application-layer block length，恢复 bit、解帧、重组、解密；
- Server：普通业务接收端，不感知秘密数据。

## 2 数据面

```text
Encryption
 → Framing
 → Bitstream
 → Modulation
 → TCP
 → Length Recovery
 → Bitstream
 → Frame Decoder
 → Reassembly
 → Decryption
```

## 3 application-layer write length vs TCP packet length

本文档和代码严格区分：

- `application-layer write length`：Proxy-A 调用一次 `sendall()` 的字节数；
- `TCP packet length`：TCP/IP 栈实际发到网络上的 segment size。

本模块只调制前者。TCP 仍可能：

- segmentation：一个 write 被拆成多个 segment；
- coalescing：多个 write 被合并到一次接收；
- buffering：接收端一次 `recv()` 读到不同大小的数据块。

因此 Proxy-B 的 `observed_length` 记录的是自己看到的 application-layer
block length，而不是抓包层面的 packet length。

## 4 代码边界

- `core/`：协议、比特、CRC、调制、重组，不依赖 socket；
- `proxy/`：socket 与日志，调用 core；
- `examples/`：端到端 Demo；
- `crypto/`：已有 AES-256-GCM，通过 `core/crypto_adapter.py` 复用。

## 5 日志

JSONL：

- `logs/sender.jsonl`：target_length、actual_write_length、bit、frame_id；
- `logs/receiver.jsonl`：observed_length、recovered_bit、frame_id、crc_status；
- `logs/errors.jsonl`：长度越界、CRC 错误、解密失败等。

这些日志能直接进入后续 `dataset_builder.py`。
