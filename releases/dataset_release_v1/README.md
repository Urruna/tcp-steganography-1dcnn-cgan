# 数据集发布包：TCP 代理流量（Normal / Stego）

本发布包包含三个流量数据来源：

1. 历史 Docker Normal 数据集
2. 当前 Protocol-Stego 的 Normal 数据集
3. 当前 Protocol-Stego 数据集

它们被有意放在不同目录中，没有明确的实验设计时**不得混用**。

## 来源对应关系

```text
历史 Normal
        ↓
早期 Docker 通信基线

Protocol Normal
        ↓
当前实验对照组

Protocol Stego
        ↓
当前实验组
        ↓
800/1200 应用层长度调制
```

## 可直接用于机器学习的数据

```text
X = [N, 4, 128]
y = [N]
```

- `N` = 窗口数量
- `4` = 特征数
- `128` = 每个窗口的事件数

特征顺序：

```text
0 = direction
1 = length
2 = inter_arrival_time
3 = cumulative_bytes
```

标签：

```text
0 = Normal
1 = Stego
```

本发布包中的 Stego 标签特指：

> 携带当前 800/1200 应用层长度调制的流量。

它**不**代表「所有可能的隐写流量」。

## 最简加载示例

```python
import numpy as np

X = np.load("dataset_release/protocol_stego/processed/X.npy")
y = np.load("dataset_release/protocol_stego/processed/y.npy")

print(X.shape)   # [138, 4, 128]
print(y.shape)   # [138]
print(np.unique(y, return_counts=True))
```

给 CNN 方向同学的重要提醒：

1. 不要改变特征顺序。
2. 不要随机重划分窗口，请使用提供的 session 级划分。
3. 当前数据中 `direction` 恒为 +1，因为只记录了 Client → Server 方向。
4. Normal 事件大多是 1024 字节，Stego 事件是 800/1200 字节。
   这意味着当前的 CNN 任务主要是在测「能否识别 800/1200 调制签名」，
   而不是一般意义上的隐写检测。

## 建议的实验

### 实验 A（严格的当前对比）

```text
Protocol Normal vs Protocol Stego
```

这是最可控的对比，因为两边都由当前 protocol_stego 实验产生。

### 实验 B（补充对比）

```text
Historical Normal vs Protocol Stego
```

这是额外对比；历史数据并不来自当前的 protocol_stego 对照组。

## 包内结构

```text
dataset_release/
├── README.md
├── DATASET_CARD.md
├── DATA_DICTIONARY.md
├── DATASET_INTEGRITY.md
├── LICENSE_OR_USAGE.md
├── historical_normal/
│   ├── README.md
│   ├── raw/
│   └── processed/
├── protocol_stego/
│   ├── README.md
│   ├── raw/
│   ├── processed/
│   ├── splits/
│   └── metadata/
└── checksums/
    └── SHA256SUMS.txt
```

## 完整性

见：

- `DATASET_INTEGRITY.md`
- `checksums/SHA256SUMS.txt`

## 当前 protocol_stego 概况

> 注意：本发布包是 v1 快照，对应扩容前的 46 个 session。
> 工作数据集此后已扩容到 466 个 session（1398 窗口），
> 见 `docs/experiments/dataset-scaleup-20260926.md`。

| 项目 | 数值 |
| --- | ---: |
| Normal session | 23 |
| Stego session | 23 |
| 成功 session | 46 / 46 |
| Normal 事件 | 10258 |
| Stego 事件 | 10488 |
| 窗口 | 138 |
| Normal 窗口 | 69 |
| Stego 窗口 | 69 |
| `X.shape` | `[138, 4, 128]` |
| `y.shape` | `[138]` |
| BER | 0.0 |
| 帧错误率 | 0.0 |
| CRC 失败率 | 0.0 |
