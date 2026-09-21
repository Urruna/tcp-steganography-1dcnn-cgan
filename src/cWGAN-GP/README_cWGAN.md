# cWGAN-GP：条件 Wasserstein GAN 用于隐写长度策略生成

本模块实现了一个 **条件 Wasserstein GAN with Gradient Penalty（cWGAN-GP）**，用于为 TCP 流量隐写生成**受约束的长度策略**。生成器为每个编码单元输出连续值，经投影映射到两个不重叠的长度区间，代理可直接执行，从而在保持解码可靠性的同时降低流量被检测的概率。

---

## ⚠️ 数据量要求（务必先读）

**本模块需要至少 1000 个训练窗口。**

当前 `datasets/protocol_stego/` 只有约 114 个训练窗口（46 个 session，每 session 约 3 个窗口），**远远不足以训练本 cWGAN-GP**。

实测证据（114 个窗口时的训练曲线）：

```text
Epoch    1/500 | Critic: -50.5     | Generator: 20.3
Epoch   20/500 | Critic: -6452.5   | Generator: 2792.9
Epoch   50/500 | Critic: -50489.5  | Generator: 23294.0
Epoch  130/500 | Critic: -400434.0 | Generator: 205152.5
```

`Critic` 与 `Generator` 两个 loss 都单调爆炸，这是**样本量不足的典型症状**：Critic 在少量真实样本上过拟合，真假分数差距被无限拉大，生成器无法追上。

### 目标数据规模

> **至少 167 个 Normal session + 167 个 Stego session，合计 334 个 session，可切出至少 1000 个窗口。**

按每个 session 约 3 个窗口估算：

```text
334 个 session × 3 个窗口/session ≈ 1000 个窗口
```

### 数据量对照表

| 训练窗口数 | cWGAN-GP 表现 |
|---|---|
| 100 ~ 200 | 必炸，即使模型缩到极小也难稳定 |
| 300 ~ 500 | 缩小模型后能稳定，生成质量一般 |
| **1000 ~ 2000** | **推荐规模，正常训练，生成质量可用** |
| 5000+ | 训练充分，生成质量好 |

**在扩充到至少 1000 个窗口之前，请勿直接运行本模块的默认配置。**

---

## 一、设计动机

代理（Proxy-A）在转发过程中，**真正能控制的只有应用层数据块的写入长度**。其他特征（方向、发送间隔、累积字节数变化）由业务请求和 TCP 行为决定，代理无法自由操控。

因此本模块：

- ❌ **不生成完整的 `[4, 128]` 窗口**
  - 输出维度 512，代理无法执行；
  - 投影损失大；
  - 小样本训不动；
  - 评估链条断裂（生成的和代理执行的并不一致）。

- ✅ **只生成 `[128]` 长度策略**
  - 输出维度 128，代理可直接执行；
  - 投影简单；
  - 评估链条完整：cGAN → 代理 → GAN-Stego → 1D-CNN。

---

## 二、生成机制

### 2.1 输出形式

```text
Generator: 噪声 + 标签 → [B, 128] 连续值 ∈ [0, 1]
    ↓ 投影
[0, 0.5)  → 比特 0 对应的长度区间 BIT0_RANGE
[0.5, 1]  → 比特 1 对应的长度区间 BIT1_RANGE
```

生成器输出每个编码单元一个连续值，投影后落到两个**不重叠的长度带**。

### 2.2 归一化长度空间中的默认区间

```python
BIT0_RANGE = (-1.5, -0.5)   # 比特 0 → 较低长度带
BIT1_RANGE = ( 0.5,  1.5)   # 比特 1 → 较高长度带
```

> 如果数据未按通道标准化，长度通道是原始字节数（例如 `780 ~ 820` / `1180 ~ 1220`），请修改 `cWGAN-GP.py` 顶部的这两个常量。

解码时 Proxy-B 只需一个阈值（如 1000 字节）即可判定比特，无需复杂计算。

### 2.3 为什么用两个“宽区间”而不是两个“固定值”

| 方案 | 长度形式 | 检测难度 |
|---|---|---|
| 固定 800 / 1200 | 两个整数尖峰 | 极易被检测 |
| 两个窄区间（±5） | 窄峰，仍接近尖峰 | 较易被检测 |
| **本方案：两个宽区间** | **区间内连续变化** | **最难被检测** |

- **比特信息保留**：两个区间不重叠，Proxy-B 用阈值即可可靠解码。
- **分布自然**：区间内连续变化，长度直方图呈现“宽峰”而非“尖峰”，规避基于直方图的简单检测器。
- **代理可执行**：Proxy-A 拿到连续值即可计算实际写入长度。
- **小样本可训**：输出维度仅 128，无需学习 512 维联合分布。

---

## 三、模型结构

### 3.1 Generator

```text
输入: 噪声 z [B, z_dim]  +  标签 [B]
  ↓ 标签嵌入 Embedding(2, 16)
  ↓ 拼接 [B, z_dim + 16]
  ↓ Linear(z_dim+16 → 256) + ReLU
  ↓ Linear(256 → 256) + ReLU
  ↓ Linear(256 → 128) + Sigmoid
输出: [B, 128] 连续值 ∈ [0, 1]
```

### 3.2 Critic

```text
输入: 长度序列 [B, 128]  +  标签 [B]
  ↓ 标签嵌入 Embedding(2, 16)
  ↓ 拼接 [B, 128 + 16]
  ↓ Linear(128+16 → 256) + LeakyReLU(0.2)
  ↓ Linear(256 → 256) + LeakyReLU(0.2)
  ↓ Linear(256 → 1)
输出: [B, 1] Wasserstein 分数（无 Sigmoid）
```

### 3.3 参数量

| 组件 | 参数量 |
|---|---|
| Generator | 约 18 万 |
| Critic | 约 10 万 |
| **合计** | **约 28 万** |

适合 **300 ~ 2000** 个训练窗口。

---

## 四、训练算法

### 4.1 损失函数（WGAN-GP）

```text
Critic loss    = E[D(fake)] - E[D(real)] + λ · GP
Generator loss = -E[D(fake)]
```

其中梯度惩罚：

```text
GP = E[( ||∇_x D(x_hat)||_2 - 1 )^2]
x_hat = α · real + (1-α) · fake,  α ~ U(0, 1)
```

- 默认 `λ = 10.0`
- Critic 输出为实数分数，不使用 Sigmoid，不使用 BCE。

### 4.2 类别平衡

训练时使用 `WeightedRandomSampler`，按类别频率反比加权，自动处理类别不均衡。

### 4.3 推荐超参

| 训练窗口数 | batch_size | z_dim | critic_steps | lr |
|---|---|---|---|---|
| 100 ~ 200 | 8 | 16 | 1 | 2e-5 |
| 300 ~ 600 | 32 | 32 | 2 | 1e-4 |
| **600 ~ 1500** | **64** | **32** | **3** | **1e-4** |
| 1500+ | 64 | 64 | 5 | 1e-4 |

---

## 五、数据格式

本模块从 `--data-dir` 目录读取两个文件：

```text
<data-dir>/
├── real_train_X.npy   # [N, 4, 128], float32
└── real_train_y.npy   # [N], int64, 取值 {0, 1}
```

- `X` 的 4 个通道依次为：`[方向, 数据块长度, 相邻发送间隔, 累积字节数变化]`
- 本模块**只使用第 1 通道（索引 1）——数据块长度**。
- 标签：`0 = Normal`，`1 = Stego`。
- 数据应已按通道标准化（长度通道 mean ≈ 0，std ≈ 1）。

若数据未标准化，请修改代码顶部的：

```python
BIT0_RANGE = (-1.5, -0.5)
BIT1_RANGE = ( 0.5,  1.5)
```

为实际的字节数区间，例如：

```python
BIT0_RANGE = (780.0, 820.0)
BIT1_RANGE = (1180.0, 1220.0)
```

---

## 六、使用方法

### 6.1 环境依赖

```bash
pip install numpy torch
```

### 6.2 训练

**先跑 50 轮验证流程：**

```bash
python cWGAN-GP.py \
  --data-dir datasets/protocol_stego \
  --checkpoint models/cgan_protocol.pth \
  --output-dir models/generated_protocol \
  --epochs 50 \
  --batch-size 32
```

**稳定后跑 500 轮正式训练：**

```bash
python cWGAN-GP.py \
  --data-dir datasets/protocol_stego \
  --checkpoint models/cgan_protocol.pth \
  --output-dir models/generated_protocol \
  --epochs 500 \
  --batch-size 32
```

**期望输出：**

```text
Loaded 1000 windows | labels: [500, 500]
Length channel stats: min=..., max=..., mean=..., std=...
Generator params: 182,xxx | Critic params: 101,xxx
Epoch    1/500 | Critic: -0.42 | Generator:  0.31
Epoch   10/500 | Critic: -1.85 | Generator:  1.42
Epoch   20/500 | Critic: -2.10 | Generator:  1.98
...
```

**关键检查点：**

| 检查项 | 期望 |
|---|---|
| `Loaded N windows` | N ≥ 1000 |
| `Generator params` | 约 18 万 |
| `Critic params` | 约 10 万 |
| `Critic` loss | 在 ±5 内波动，不单调爆炸 |
| `Generator` loss | 在 ±5 内波动，不单调爆炸 |

**如果 loss 仍然爆炸：**

1. 确认训练窗口数 ≥ 1000；
2. 若仍不足，先把 `z_dim` 降为 16，`lr` 降为 2e-5，`critic_steps` 降为 1；
3. 若仍不稳定，把 Generator / Critic 的隐藏层从 256 降到 128。

### 6.3 生成合成数据

```bash
python cWGAN-GP.py \
  --generate-only \
  --checkpoint models/cgan_protocol.pth \
  --output-dir models/generated_protocol \
  --count-per-class 300
```

输出：

```text
models/generated_protocol/
├── synthetic_lengths.npy   # [600, 128] 归一化长度序列
└── synthetic_y.npy         # [600] 标签
```

### 6.4 组装成完整 GAN-Stego 窗口

生成器只输出长度通道。要得到 `[N, 4, 128]` 的完整窗口，需从真实窗口中取其余三个通道，并用生成的长度替换第 1 通道：

```python
import numpy as np
from pathlib import Path

base = Path("datasets/protocol_stego")
out  = Path("models/generated_protocol")

X_real = np.load(base / "real_train_X.npy")        # [N, 4, 128]
L_syn  = np.load(out / "synthetic_lengths.npy")    # [600, 128]
y_syn  = np.load(out / "synthetic_y.npy")          # [600]

idx = np.random.choice(len(X_real), len(L_syn), replace=True)
X_syn = X_real[idx].copy()
X_syn[:, 1, :] = L_syn.astype(np.float32)          # 只替换长度通道

np.save(out / "synthetic_X.npy", X_syn.astype(np.float32))
np.save(out / "synthetic_y.npy", y_syn)
print("synthetic_X:", X_syn.shape, "synthetic_y:", y_syn.shape)
```

得到：

```text
models/generated_protocol/
├── synthetic_X.npy   # [600, 4, 128]  GAN-Stego 窗口
└── synthetic_y.npy   # [600]
```

---

## 七、参数说明

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--data-dir` | `datasets/protocol_stego` | 数据目录，需含 `real_train_X.npy` / `real_train_y.npy` |
| `--checkpoint` | `models/cgan_protocol.pth` | 生成器权重保存路径 |
| `--output-dir` | `models/generated_protocol` | 合成数据输出目录 |
| `--epochs` | 500 | 训练轮数 |
| `--batch-size` | 32 | 批大小 |
| `--count-per-class` | 300 | 每类生成样本数 |
| `--generate-only` | False | 只生成，不训练 |

---

## 八、checkpoint 内容

训练结束后保存的 `.pth` 文件包含：

```python
{
    "generator_state_dict": ...,     # 生成器权重
    "z_dim": 32,                     # 噪声维度
    "num_classes": 2,                # 类别数
    "length_shape": [128],           # 输出长度
    "bit0_range": [-1.5, -0.5],      # 比特 0 长度区间
    "bit1_range": [0.5, 1.5],        # 比特 1 长度区间
    "history": {"critic": [...], "generator": [...]},  # 训练曲线
}
```

> ⚠️ 只保存生成器，不保存 Critic 与优化器状态。该 checkpoint 用于生成数据，不适合断点续训。

---

## 九、在评估链条中的位置

```text
Normal / Baseline-Stego 窗口
        ↓
   训练 cWGAN-GP
        ↓
生成 GAN-Stego 长度策略
        ↓
    组装完整窗口
        ↓
   1D-CNN 检测评估
        ↓
比较 Normal vs Baseline-Stego vs GAN-Stego 的
Accuracy / Precision / Recall / F1 / ROC-AUC
```

**评估目的：** 验证 GAN-Stego 在保持相近可靠性和性能代价的前提下，是否比 Baseline-Stego 更难被 1D-CNN 检测。

---

## 十、与 1D-CNN 数据集的关系

cWGAN-GP 与 1D-CNN **使用同一套 `datasets/protocol_stego/` 数据**，只是各自取用的通道不同：

| 模块 | 使用的数据 | 使用的通道 |
|---|---|---|
| 1D-CNN | `datasets/protocol_stego/real_train_X.npy` | 全部 4 通道 `[4, 128]` |
| cWGAN-GP | `datasets/protocol_stego/real_train_X.npy` | 仅第 1 通道（长度）`[128]` |

### ⚠️ 不要混用的数据集

以下数据集与本模块**不兼容**，禁止静默合并：

- `src/1dcnn/data/` —— 1D-CNN 模块自带的 **168-window** 数据集，与 `protocol_stego` 无精确重叠，窗口长度也不一致。
- `datasets/historical/` —— 历史实验数据集，与当前协议定义不同。
- `datasets/normal_v1/` —— 仅含 Normal 类，缺少 Stego 正类。

**统一使用 `datasets/protocol_stego/` 的 `[N, 4, 128]` 数据，两边各取所需。**

---

## 十一、常见问题

### Q1：为什么 loss 一直爆炸？

**样本量不足。** 当前 114 个窗口远低于 cWGAN-GP 的最低要求。请扩充到至少 1000 个窗口（167 Normal + 167 Stego session）。

如果暂时无法扩充，可临时把模型缩到 5 万参数以内、`z_dim=16`、`lr=2e-5`、`critic_steps=1`，但生成质量会明显下降，仅作流程验证。

### Q2：为什么不直接生成 `[4, 128]`？

因为代理只能控制长度通道。生成完整窗口会导致投影损失大、评估链条断裂、小样本训不动。详见第一节。

### Q3：`BIT0_RANGE` / `BIT1_RANGE` 怎么设？

- 如果数据已标准化：用默认 `(-1.5, -0.5)` 和 `(0.5, 1.5)`。
- 如果数据是原始字节数：改成 `(780, 820)` 和 `(1180, 1220)`。
- 通用原则：**两个区间不能重叠**，中间留足安全距离供 Proxy-B 用阈值解码。

### Q4：生成的 `synthetic_lengths.npy` 怎么用？

它是归一化长度序列，只包含长度通道。需要和真实窗口的其他三个通道拼接，才能得到 `[N, 4, 128]` 的 GAN-Stego 数据。见 6.4 节。

### Q5：生成质量怎么评估？

**不只看 loss。** 关键指标是：

1. 长度分布是否自然（直方图有没有尖峰）；
2. 生成的长度是否能被 Proxy-B 正确解码（BER）；
3. GAN-Stego 在 1D-CNN 上的 AUC 是否低于 Baseline-Stego。

### Q6：1D-CNN 和 cWGAN-GP 能用同一个数据集吗？

**可以，而且应该用同一个。** 统一使用 `datasets/protocol_stego/` 的 `[N, 4, 128]`：

- 1D-CNN 用全部 4 通道；
- cWGAN-GP 只用长度通道（索引 1）。

**不能用的是不同来源、不同窗口长度、不同预处理的数据集**，例如 `src/1dcnn/data/` 的 168-window 数据。

---

## 十二、注意事项

1. **样本量是硬门槛。** 1000 个窗口是推荐起点，114 个窗口必炸。
2. **只生成长度通道。** 其余通道由真实数据提供。
3. **生成后必须经过代理实际执行验证。** 代理执行不了的长度策略没有意义。
4. **数据格式必须匹配。** `real_train_X.npy` 必须是 `[N, 4, 128]`，`real_train_y.npy` 必须是 `[N]`，标签为 0/1。
5. **不要与 1D-CNN 的 168-window 数据集混用。** 二者无精确重叠，窗口长度也不一致。

---

