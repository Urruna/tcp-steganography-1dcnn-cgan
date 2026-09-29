# protocol_stego 数据集

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

当前规模（2026-09-26 扩容后）：

```text
Normal session：233，全部成功
Stego session： 233，全部成功
事件总数：      210165
窗口总数：      1398（699 Normal / 699 Stego）
X.shape = [1398, 4, 128]
y.shape = [1398]

train：374 session / 1122 窗口
val：   46 session /  138 窗口
test：  46 session /  138 窗口
```

独立交付副本位于：

```text
releases/dataset_release_v1/protocol_stego/
```

注意：该发布副本目前仍是 46 个 session 的旧快照，尚未随扩容重新生成。

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

扩容过程中失败的 8 个 Stego session 存放在虚拟机的
`protocol_stego/raw_failed/stego/`，不在本数据集内。

详见 `docs/experiments/dataset-scaleup-20260926.md` 与
`src/protocol_stego/docs/DATASET.md`。
