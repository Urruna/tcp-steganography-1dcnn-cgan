# 基础隐写

## 当前基线策略

```text
比特 0 → 目标 800 字节的应用层写入
比特 1 → 目标 1200 字节的应用层写入
```

配置：`src/protocol_stego/config.yaml`

```yaml
stego:
  low_length: 800
  high_length: 1200
  tolerance: 80
  block_gap_ms: 5
```

允许范围：

```text
LOW： 720–880 字节
HIGH：1120–1280 字节
```

## 数据流

```text
秘密数据
 → AES-256-GCM
 → 密文
 → 帧编码
 → 比特流
 → 比特
 → 选择目标写入长度
 → Proxy-A sendall()
```

## Proxy-A

`src/protocol_stego/proxy/sender_stego.py`

对每个比特：

1. `bit_to_target_length()`；
2. 从 cover 流中精确读取目标字节数；
3. `upstream.sendall(block)`；
4. 记录 `target_length`、`actual_write_length`、`bit`、`frame_id`。

## Proxy-B

`src/protocol_stego/proxy/receiver_stego.py`

1. `_read_modulated_block()` 累积接收字节；
2. `length_to_bit()` 恢复比特；
3. 比特流 → 字节；
4. 帧解码 + CRC；
5. 重组；
6. AES-GCM 解密。

## 日志

JSONL：

```text
sender.jsonl
receiver.jsonl
errors.jsonl
```

## 实际验证结果

基于 233 个 Stego session：

| 项目 | 数值 |
| --- | ---: |
| target 800 / 1200 | 57780 / 48468 |
| bit 0 / 1 | 57780 / 48468 |
| observed 800 / 1200 | 57780 / 48468 |
| actual == target | 1.0 |
| actual == observed | 1.0 |
| BER | 0.0 |
| 帧错误率 | 0.0 |
| CRC 失败率 | 0.0 |

（最初的 23 个 Stego session 上，上述计数为 5654 / 4834，结论相同。）

## 重要边界

代码控制的是**应用层写入长度**。

它并不直接控制 TCP 报文长度；TCP 的分段或合并会改变接收端实际观测到的
数据块大小。

## 局限

- 依赖块边界假设；
- 没有 FEC；
- 没有重传；
- 固定 800/1200 两个长度极易被检测；
- 当前 Normal 数据几乎全是 1024 字节，因此任务相对容易。
