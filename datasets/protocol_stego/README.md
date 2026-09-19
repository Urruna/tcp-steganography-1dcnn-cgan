# protocol_stego Dataset

本目录是 protocol_stego 的正式工作数据集目录，保存原始数据、处理后数据和
数据集划分。

```text
datasets/protocol_stego/
├── experiment_config.json
├── raw/
│   ├── normal/     # 正常代理转发 session
│   └── stego/      # 800/1200 长度调制 session
├── processed/      # 窗口化数据集
├── splits/         # session 级别的 train/val/test
└── README.md
```

`src/protocol_stego/compose.yaml` 会把本目录挂载到容器内的
`/work/protocol_stego/dataset`，因此容器内脚本的运行路径保持不变。

当前规模：

```text
Normal sessions: 23
Stego sessions:  23
events: 10258 Normal / 10488 Stego
X.shape = [138, 4, 128]
y.shape = [138]
```

独立交付副本位于：

```text
releases/dataset_release_v1/protocol_stego/
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
