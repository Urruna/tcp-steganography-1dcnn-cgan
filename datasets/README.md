# 数据集目录

本目录按来源区分数据集。

```text
datasets/
├── historical/
│   ├── docker_chain_smoke/
│   └── baseline_lenmix_v1/
├── normal_v1/
└── protocol_stego/
```

注意事项：

- 历史 Normal 数据与 protocol_stego 的 Normal 是两类不同实验；
- 没有明确的实验设计，不要把它们混用；
- 原始数据不得修改、重排或重新编码；
- 当前 protocol_stego 的工作数据集放在 `datasets/protocol_stego/`；
- 发布副本放在 `releases/dataset_release_v1/`；
- `src/1dcnn/` 目前自带一套独立的 168 窗口数据集（`src/1dcnn/data/`），
  它与 `datasets/protocol_stego/` 没有精确重叠，**不要静默合并**。
