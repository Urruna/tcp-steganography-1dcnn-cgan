# 数据集扩容记录（2026-09-26）

## 目的

把 `datasets/protocol_stego/` 扩到 `src/cWGAN-GP/` 要求的规模
（至少 1000 个训练窗口），同时**不改变**协议、800/1200 调制、
session 参数和 Docker 定义。

扩容前数据集为 23 个 Normal + 23 个 Stego session、138 个窗口。

## 环境

| 项目 | 取值 |
| --- | --- |
| 宿主机 | Ubuntu6.21 虚拟机，用户 `urruna` |
| 项目路径 | `/home/urruna/docker/tcp-lab/protocol_stego` |
| 采集运行环境 | 系统 Python 3.8.10、numpy 1.24.4、PyYAML 5.3.1 |
| 管线运行环境 | 项目镜像 `protocol-stego:1`，通过 Docker Compose 2.27.1 |

## 执行命令

采集。两个进程并行运行，各自负责一种 mode，这样 `_next_index()`
的目录扫描不会把同一个 session 序号分配给两个进程：

```bash
python3 -m scripts.run_experiment --mode normal --normal 210 \
  --seed 42 --secret-size 16 --block-gap-ms 20 --window-size 128

python3 -m scripts.run_experiment --mode stego --stego 210 \
  --seed 42 --secret-size 16 --block-gap-ms 20 --window-size 128
```

所有参数都与最初的 23 + 23 个 session 一致（`seed=42`、
`secret_size=16`、`block_gap_ms=20`、`window_size=128`），因此新旧 session
可以直接比较。

> 调用方式注意：必须用模块方式运行
> （`python3 -m scripts.run_experiment`）。用文件方式运行
> （`python3 scripts/run_experiment.py`）会报
> `ModuleNotFoundError: No module named 'scripts'`，
> 因为 Python 放进 `sys.path` 的是 `scripts/` 而不是项目根目录。

后处理，顺序与仓库 README 中记录的一致：

```bash
docker compose run --rm tests python -m scripts.dataset_builder --window-size 128
docker compose run --rm tests python -m scripts.split_dataset \
  --val-ratio 0.1 --test-ratio 0.1 --seed 42
docker compose run --rm tests python -m scripts.dataset_stats
docker compose run --rm tests python -m scripts.data_quality_report
docker compose run --rm tests python -m scripts.baseline_analysis
```

## 结果

| 项目 | 扩容前 | 扩容后 |
| --- | ---: | ---: |
| Normal session | 23 | 233 |
| Stego session | 23 | 233 |
| `raw/` 中失败的 session | 0 | 0 |
| 事件总数（两类合计） | 20 746 | 210 165 |
| 窗口数 | 138 | 1 398 |
| Normal / Stego 窗口 | 69 / 69 | 699 / 699 |
| X 形状 | `[138, 4, 128]` | `[1398, 4, 128]` |
| train / val / test（session） | 38 / 4 / 4 | 374 / 46 / 46 |
| train / val / test（窗口） | 114 / 12 / 12 | 1122 / 138 / 138 |

训练集现在有 **1122 个窗口**，已经越过 cWGAN-GP 模块文档中的
`>= 1000` 门槛。

## 失败的 session 与处理方式

最初的 210 个 Stego session 中有 7 个失败，补采的 7 个中又有 1 个失败，
报的都是此前已记录过的错误：

```text
length_out_of_range: length 1600 / 2000 outside LOW(720, 880) / HIGH(1120, 1280)
```

根因：接收端偶尔会把两次连续的代理写入合并成一次读取，于是 800/1200
两个写入被观测成 1600/2000。正常情况下 20 ms 的 `block_gap_ms` 可以
避免这种情况，所以这是时序竞争，而不是协议缺陷。失败率约为 3%。

处理方式：

1. 把这些失败的 session 目录从 `dataset/raw/stego/` 移到
   `protocol_stego/raw_failed/stego/`（**没有删除**；
   数据集构建脚本只扫描 `raw/normal` 与 `raw/stego`，
   因此它们不会进入数据集）；
2. 补采新的 session，直到 233 个 Stego session 全部 `success: true`。

被隔离的 session id：

```text
stego_000108  stego_000112  stego_000159  stego_000168
stego_000175  stego_000206  stego_000226  stego_000238
```

需要注意的后果：由于是追加补采，`raw/stego/` 中的 Stego session id 是
`000001`–`000237` 加上 `000239`–`000241`，被隔离的 id 缺号，但总数仍是
233。session id 只是标识符而不是下标，这是正常现象。

## `run_summary.json`

两个采集进程都会在各自结束时写 `dataset/raw/run_summary.json`，
所以这个文件无法描述一次合并后的运行。因此改为按每个 session 的
`metadata.json`（真正权威的逐 session 记录）聚合重建，
保持原有 JSON 结构不变，并额外增加一个 `note` 字段说明这一点。
没有修改任何 session 记录。

## 已核实的数据质量

来自重新生成的 `DATA_QUALITY_REPORT.md`：

| 检查项 | 结果 |
| --- | --- |
| Normal session | 233，全部 `success: true` |
| Stego session | 233，全部 `success: true` |
| X / y 形状 | `[1398, 4, 128]` / `[1398]`，float32 / int64 |
| NaN / Inf | 0 / 0 |
| train ∩ val、train ∩ test、val ∩ test | 均为空 |
| 重复样本 | 0 |
| BER | 0.0 |
| 帧错误率 | 0.0 |
| CRC 失败率 | 0.0 |
| Stego 的 target / actual / observed 计数 | 800: 57780，1200: 48468，三者完全一致；越界的观测值 0 个 |
| 可比性（Normal 与 Stego 均值之比） | 时长 1.015、事件数 1.022、总字节数 1.018 |

报告给出的总体结论是：**READY_FOR_CNN**。

## 本次运行记录的局限

1. **Normal 流量仍是固定 1024 字节写入。** 特征统计显示 Normal 的
   `length` 每个事件都恰好是 1024，而 Stego 恰好是 800/1200。
   因此在这个数据对上训练的检测器学到的是 800/1200 签名，
   而不是「是否存在隐蔽信道」。报告中也重复了这一点，
   任何引用 CNN 指标的论文或汇报都必须一并说明。
2. **`direction` 通道在两个类别上都恒为 1**（当前窗口提取只用正向事件），
   对检测器没有任何信息量。
3. `dataset/processed/data_quality_report.json` 现在约 199 MB，
   仍被 `.gitignore` 排除在外。
4. `releases/dataset_release_v1/` 仍描述扩容前 46 个 session 的快照，
   本次**没有**重新生成。
