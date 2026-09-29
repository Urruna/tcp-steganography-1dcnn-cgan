# Protocol-Stego 数据集（发布副本）

这是 protocol_stego 的数据集发布副本，由当时的实验代码生成，
并由 `DATA_QUALITY_REPORT.md` 与 `BASELINE_ANALYSIS.md` 验证。

> 说明：本副本是 v1 快照，对应 23 + 23 个 session。工作数据集此后
> 已扩容到 233 + 233 个 session（1398 窗口），本目录尚未重新生成。

## raw

`raw/normal/` 与 `raw/stego/` 各含 23 个 session。

每个 session 保留：

```text
metadata.json
session_config.json
sender.jsonl
receiver.jsonl
errors.jsonl
sender_result.json
receiver_result.json
```

原始 JSONL 文件未做任何修改。

## processed

```text
processed/X.npy          # [138, 4, 128], float32
processed/y.npy          # [138], int64
processed/windows.npz    # X 与 y 的 npz 形式
processed/index.jsonl    # session_id、window_id、label、起止事件
processed/build_summary.json
processed/stats.json
processed/data_quality_report.json
processed/baseline_analysis.json
```

特征顺序：

```text
0 direction
1 length
2 inter_arrival_time
3 cumulative_bytes
```

## splits

```text
splits/train.npz / train_index.jsonl
splits/val.npz   / val_index.jsonl
splits/test.npz  / test_index.jsonl
splits/split_manifest.json
```

这些是已经校验过的 session 级划分。不要随机重划分窗口。

当时的划分：

```text
train：38 个 session，114 个窗口
val：   4 个 session， 12 个窗口
test：  4 个 session， 12 个窗口
```

## 标签与注意事项

```text
0 = Normal
1 = Stego = 当前的 800/1200 应用层长度调制
```

需要注意：

- `direction` 恒为 +1，因为只记录了 Client → Server 方向；
- Normal 长度基本是 1024 字节；
- Stego 长度是 800/1200 字节；
- 当前任务主要测的是「800/1200 调制签名」能否被检测，
  而不是一般意义上的隐写检测。
