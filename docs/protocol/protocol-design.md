# 协议设计

## 帧格式

```text
Preamble(32 bit)
Version + Reserved(8 bit)
Frame ID(16 bit)
Payload Length(16 bit)
Payload
CRC-16/XMODEM(16 bit)
```

常量：

| 字段 | 取值 / 限制 |
| --- | --- |
| Preamble | `0x6E9797A1` |
| Version | 1（高 4 位），低 4 位保留为 0 |
| Frame ID | 16 位，`0..65535` |
| Payload Length | 16 位，当前代码限制 512 字节 |
| CRC | CRC-16/XMODEM，大端 |

CRC 覆盖范围：Version + Frame ID + Payload Length + Payload
（即 Preamble 之后的全部内容）。

## 实现位置

### newtry97 v0.2

`src/newtry97/framing.py`

- 比特级组帧；
- `FrameDecoder` 滑动搜索 Preamble；
- CRC 失败时记录日志并继续重新同步；
- 单帧恢复演示。

### protocol_stego

`src/protocol_stego/core/framing.py`

- `encode_frame()`；
- `decode_frame()`；
- `FrameStreamDecoder`；
- `split_payload()`；
- 明确的异常类型：
  - `PreambleNotFoundError`
  - `UnsupportedVersionError`
  - `InvalidPayloadLengthError`
  - `IncompleteFrameError`
  - `CRCMismatchError`。

`src/protocol_stego/core/reassembly.py`

- 按 `Frame ID` 重组；
- 检测重复 ID；
- 检测缺失 ID；
- 检测乱序；
- 拼接 payload 还原密文。

## 多帧约定

- 除最后一帧外，所有帧都使用完整的 `max_payload_size`；
- 最后一帧可以更短；
- 如果 payload 长度正好是整数倍，则追加一个长度为 0 的结束帧。

## 比特流

`src/protocol_stego/core/bitstream.py`

- `bytes_to_bits()`
- `bits_to_bytes()`
- 严格处理非 8 倍数的情况，可选择补零。

## 测试

- `src/protocol_stego/tests/test_framing.py`
- `src/protocol_stego/tests/test_reassembly.py`
- `src/protocol_stego/tests/test_bitstream.py`
- `src/protocol_stego/tests/test_crc.py`

## 尚未实现

- FEC；
- 重传；
- 版本协商；
- 协议层密钥交换。
