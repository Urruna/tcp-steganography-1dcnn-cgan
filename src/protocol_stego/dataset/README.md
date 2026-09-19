# dataset 目录

本目录保存秘密传输协议实验的原始数据、处理后数据和数据集划分。

```text
dataset/
├── raw/
│   ├── normal/     # 正常代理转发 session
│   └── stego/      # 800/1200 长度调制 session
├── processed/      # 窗口化数据集
├── splits/         # session 级别的 train/val/test
├── experiment_config.json
└── README.md
```

每个 session 的原始目录（见 `docs/DATASET.md`）：

```text
raw/stego/stego_000001/
├── metadata.json
├── session_config.json
├── sender.jsonl
├── receiver.jsonl
├── errors.jsonl
├── sender_result.json
└── receiver_result.json
```

- `label=0`：normal
- `label=1`：stego

详见 `../docs/DATASET.md`。
