# newtry97

独立的 v0.2 帧协议与写拆分（write-splitting）隐写演示。

帧格式：

```text
Preamble(32 bit) | Version+Reserved(8 bit)
| Frame ID(16 bit) | Payload Length(16 bit)
| Payload | CRC-16(16 bit)
```

隐写策略：

```text
比特 0 → 一次写入
比特 1 → 拆成两次写入
```

它与 `src/protocol_stego/` 的 800/1200 长度调制不是同一种策略。

运行：

```bash
python3 run_demo.py
```

更早那次容器运行的演示日志在 `logs/docker917/` 下。
