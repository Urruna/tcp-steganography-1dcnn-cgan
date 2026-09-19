# 协议说明

## 1 流程

```text
plaintext
 → AES-256-GCM
 → ciphertext
 → Frame Encoder
 → bytes
 → bitstream
 → 0/1 长度调制
 → Proxy-A application-layer write
 → Proxy-B length recovery
 → bitstream → bytes
 → Frame Decoder
 → CRC
 → Frame Reassembly
 → ciphertext
 → AES-256-GCM Decrypt
 → plaintext
```

## 2 帧格式

本项目实现约定：复用 `newtry97` v0.2 的字段布局与常量。

| Field | Size | Description |
| --- | ---: | --- |
| Preamble | 4 B | 固定 `0x6E9797A1`，big-endian，用于帧同步 |
| Version + Reserved | 1 B | 高 4 bit 为 Version=1，低 4 bit 保留为 0 |
| Frame ID | 2 B | 帧序号，big-endian，范围 0..65535 |
| Payload Length | 2 B | Payload 字节数，big-endian，最大值由 config 配置 |
| Payload | variable | AES-256-GCM 密文分片 |
| CRC | 2 B | CRC-16/XMODEM，big-endian |

固定额外开销：`4 + 1 + 2 + 2 + 2 = 11` 字节。

## 3 CRC

- 算法：CRC-16/XMODEM，多项式 `0x1021`，初始值 `0x0000`；
- 覆盖范围：Preamble 之后的 Version/Frame ID/Payload Length/Payload；
- 字节序：big-endian 写入 2 字节；
- CRC 与 AES-GCM Tag 不是同一种机制：CRC 只做传输错误检测；
  抗篡改由 AES-GCM Tag 负责。

## 4 Frame ID 与 Payload Length

- Frame ID 从 0 开始递增；
- 除最后一帧外，Payload Length 均为 `max_payload_size`；
- 最后一帧 Payload Length 小于 `max_payload_size`；
- 若密文长度刚好是 `max_payload_size` 的整数倍，发送端追加一个
  Payload Length = 0 的终止帧，方便接收端判断帧序列结束。

## 5 错误处理

`decode_frame()` 明确抛出：

| 异常 | 触发条件 |
| --- | --- |
| `PreambleNotFoundError` | 找不到 Preamble |
| `UnsupportedVersionError` | Version 不支持，或 Reserved 非 0 |
| `InvalidPayloadLengthError` | Payload Length 超出配置上限 |
| `IncompleteFrameError` | 字节数不足，帧不完整 |
| `CRCMismatchError` | CRC 校验失败 |

`FrameStreamDecoder` 在 CRC 失败或字段非法时记录错误，并向后移动一个字节继续
重同步；不会把非法帧当作合法帧返回。

## 6 重组

`reassemble_frames()` 按 Frame ID 排序并拼接 Payload，检查：

- Frame ID 重复；
- Frame ID 缺失；
- 帧顺序异常。

第一版不做 FEC/重传；发现错误时写入 `logs/errors.jsonl`，并由
`experiment_summary.json` 统计。

## 7 本项目实现约定

- CRC 使用 CRC-16/XMODEM；
- Version 当前为 1；
- Preamble 为 `0x6E9797A1`；
- 调制只针对 application-layer write length；
- 800/1200 是目标写块长度，不代表 TCP packet length。
