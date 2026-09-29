# cWGAN-GP 现状报告

报告日期：2026-09-26

模块本身的说明以 `src/cWGAN-GP/README_cWGAN.md` 为准。
本报告只记录**仓库里实际存在的东西**，不写计划。

## 1. 目前有什么

| 项目 | 状态 | 位置 |
| --- | --- | --- |
| 条件 WGAN-GP 实现 | 存在 | `src/cWGAN-GP/cWGAN-GP.py`（343 行） |
| 模块文档 | 存在 | `src/cWGAN-GP/README_cWGAN.md` |
| 已训练的生成器权重 | **不存在** | – |
| 生成的合成长度策略 | **不存在** | – |
| GAN-Stego 数据集 | **不存在** | – |
| GAN-Stego 检测结果 | **不存在** | – |

该模块由提交 `6840169`（"Add cWGAN-GP module and README"，2026-09-21）
引入。仓库中目前还没有任何代码引用它。

## 2. 代码做了什么

```text
噪声 z + 标签
   → Generator → [B, 128] 的 [0, 1] 连续值
   → 投影到两个互不重叠的长度区间
        比特 0 → BIT0_RANGE = (-1.5, -0.5)
        比特 1 → BIT1_RANGE = ( 0.5,  1.5)
```

- Critic 只接收长度序列，并带有标签嵌入。
- 损失函数：WGAN-GP（`Critic = E[D(fake)] - E[D(real)] + λ·GP`，
  `Generator = -E[D(fake)]`，`λ = 10.0`）。
- 用 `WeightedRandomSampler` 做类别平衡。
- 只保存生成器，不保存 Critic 与优化器状态，因此该 checkpoint
  无法用于断点续训。

模块 README 中记录的设计动机：代理真正能控制的只有**应用层写入长度**，
因此生成完整的 `[4, 128]` 窗口会得到代理无法执行的策略。固定的
800/1200 是长度直方图上的两个尖峰；改成两个宽区间后，比特仍然可解
（区间不重叠，Proxy-B 用一个阈值即可判定），同时把尖峰摊平成宽峰。

## 3. 训练数据量

模块 README 写明硬性要求：**至少 1000 个训练窗口**，并记录了在当时的
规模下观察到的失败现象：

```text
Epoch    1/500 | Critic: -50.5     | Generator: 20.3
Epoch   20/500 | Critic: -6452.5   | Generator: 2792.9
Epoch   50/500 | Critic: -50489.5  | Generator: 23294.0
Epoch  130/500 | Critic: -400434.0 | Generator: 205152.5
```

两个 loss 同时单调发散，正是样本量不足的典型症状。

当前的数据量：

| 数据集 | 训练窗口数 | 是否满足要求 |
| --- | ---: | --- |
| `datasets/protocol_stego/` | 1122（train split） | 满足（2026-09-26 起） |
| `src/1dcnn/data/` | 117（train split） | 不满足 |

数据集在 2026-09-26 从 46 个 session 扩到 466 个 session，正是为了越过
这道门槛（见 `docs/experiments/dataset-scaleup-20260926.md`）：train split
现有 1122 个窗口，总体 699 Normal / 699 Stego。

**但训练目前仍未跑通，所以依然没有任何 cWGAN-GP 结果。** 剩下的障碍是
第 4 节列出的数据接口问题，不再是样本数量。

## 4. 数据接口不一致（训练前必须解决）

以下结论都是通过读代码和检查仓库内容核实过的。

| # | 问题 | 证据 |
| --- | --- | --- |
| 1 | 默认 `--data-dir` 要求 `real_train_X.npy` / `real_train_y.npy` **直接放在** `datasets/protocol_stego/` 下 | `cWGAN-GP.py` 第 147–148 行与 `--data-dir` 默认值 |
| 2 | 仓库只有 `datasets/protocol_stego/processed/windows.npz`；那两个 `.npy` 只出现在 `releases/dataset_release_v1/.../processed/` 与 `src/1dcnn/data/` 中 | 目录清单 |
| 3 | 代码假定长度通道已经按通道标准化（mean ≈ 0，std ≈ 1） | `cWGAN-GP.py` 第 46–49 行 |
| 4 | 协议数据集存的是原始值（Normal 恒为 1024，Stego 为 800/1200）；没有找到针对它的共享 scaler | `datasets/protocol_stego/processed/stats.json` |
| 5 | `README_cWGAN.md` §10 写「1D-CNN 使用 `datasets/protocol_stego`」 | 1D-CNN 实际使用的是 `src/1dcnn/data/real_train_X.npy`（168 窗口） |

由 (3) + (4) 可推出：如果用默认的 `BIT0_RANGE` / `BIT1_RANGE` 去套未标准化
的字节长度，投影结果没有意义。要么把长度通道标准化后保留默认区间，
要么按模块 README 的建议把区间改成真实的字节带
（例如 `(780, 820)` / `(1180, 1220)`）。

## 5. 还需要做什么

1. ~~完成 P0 的数据扩容（≥167 + 167 个 session），让 1000 窗口要求成立。~~
   **已于 2026-09-26 完成**：train split 现有 1122 个窗口
   （见 `dataset-scaleup-20260926.md`）。
2. 对齐数据接口：把 `real_train_X.npy` / `real_train_y.npy` 导出到
   `datasets/protocol_stego/`，或把加载器改为读取
   `processed/windows.npz`；随后把区间常量改成与真实长度尺度一致。
3. 训练并记录 loss 曲线；按模块 README 的验收标准，两个 loss 应在
   约 ±5 内波动，而不是持续发散。
4. 生成合成的长度策略，并组装成 `[N, 4, 128]` 的窗口
   （用生成的长度替换第 1 通道，其余三通道取自真实窗口）。
5. 把生成的策略真正交给 Proxy-A 执行，重新采集流量，
   然后用同一个 1D-CNN 和同一套 session 级划分，评估
   Normal / Baseline-Stego / GAN-Stego 三者。

## 6. 诚实的现状总结

```text
cGAN 实现        ：存在
cGAN 训练        ：未运行（接口不一致），没有成功记录
cGAN 权重        ：无
GAN-Stego 数据   ：无
GAN-Stego 评估   ：无
```

因此 `PROJECT_STATUS.md` 中 cGAN 记为**部分完成**，既不是已完成，
也不是仅仅处于设计阶段。
