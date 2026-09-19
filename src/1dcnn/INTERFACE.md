# 与 GAN / 外部流量模块对接

## 输入输出约定

| 项目 | 约定 |
|---|---|
| 特征数组 | NumPy 数组 `[N,4,128]`，有限数值 |
| 通道顺序 | `direction, write_len, interval, cum_bytes` |
| 样本含义 | 一个窗口内连续 128 个应用层事件 |
| 标签 | `0=Normal`、`1=Stego`；GAN-Stego 仍记作 1，不额外变成类别 2 |
| 输入空间 | 必须显式指定 `raw` 或 `standardized` |
| `raw` | 原数据流水线提取的未标准化特征；接口使用配套 scaler 处理 |
| `standardized` | 已用本包同一 scaler 处理的窗口，不能是 GAN 自己的另一套归一化结果 |
| 概率输出 | `[N,2]`，第 0 列为正常分数，第 1 列为隐写分数；Softmax 输出不代表已做概率校准 |
| 类别输出 | `[N]`，隐写分数 `>=0.5` 判为 1 |

原始数据里的方向使用 0/1，但两者语义需队友确认；interval 的单位和 cum_bytes 的计算公式也必须与原数据流水线一致。不能自行把方向改为 ±1，不能把 cum_bytes 替换成另一种累计方式。若 GAN 输出采用自身的 [-1,1] 或其他缩放，应先还原到原始特征空间，再用 `input_space="raw"`。

## 1. Python 调用

从项目目录运行：

```python
import numpy as np
from detector import Detector

detector = Detector()
X = np.load("data/real_test_X.npy", allow_pickle=False)

# 本包数据已经标准化。
probabilities = detector.predict_proba(X, input_space="standardized")
labels = detector.predict(X, input_space="standardized")
print(probabilities[:, 1])
print(labels)
```

GAN 队友得到原始特征窗口后：

```python
from gan_interface import evaluate_windows

# gan_windows 必须已经按约定形成 [N,4,128] 的原始特征。
result = evaluate_windows(gan_windows, input_space="raw", detector=detector)
scores = result["prob_stego"]
predicted_labels = result["labels"]
```

如果上游是 PyTorch Tensor，先使用 `tensor.detach().cpu().numpy()`。本接口是冻结检测器的评估调用，不提供 GAN 的反向传播训练环节。

如果有真实标签，可传 `y=labels_array`，返回值会多出 `metrics`。没有真实标签时只输出预测结果，不会给出虚构的准确率。

## 2. 命令行调用

先用已有测试数据验证接口：

```bash
python gan_interface.py --x data/real_test_X.npy --y data/real_test_y.npy --input-space standardized --out results/interface_demo
```

上述命令是用已有数据做接口演示，不能称为 GAN 实验。输出目录包含 `predictions.csv`、`probabilities.npy`、`summary.json`，有标签时还会生成混淆矩阵，包含两类标签时生成 ROC。

收到 GAN 队友的数据后，将文件放在 `data/`，例如：

```bash
python gan_interface.py --x data/gan_test_X.npy --y data/gan_test_y.npy --input-space raw --out results/gan_test
```

本包没有提供 `gan_test_X.npy`、`gan_test_y.npy`，因为尚未收到实际 GAN 数据。不要用本包的测试数据改名冒充 GAN 数据。

## 3. 真实标签怎么提供

- 若只评估 GAN-Stego，`y` 全为 1，可以报告这批样本的检出率/漏检率；不能计算正常流量误报率，也不能计算 ROC-AUC。
- 若要报告 ROC-AUC，评估集需要同时包含真实正常窗口与 GAN-Stego 窗口，标签分别为 0 和 1。
- 不要根据 CNN 预测结果生成“真实标签”。
- 不要在对比前后使用不同的 scaler、特征顺序或随意更改分类阈值。

## 4. 与代理、GAN 队友的边界

1. GAN 队友生成候选特征或调度策略。
2. 代理队友执行策略并重新采集应用层事件。
3. 数据流水线生成与本包定义一致的 `[N,4,128]` 特征。
4. 调用本包的固定检测器，得到分数和指标。

直接测试生成器输出只能算候选特征评估；要报告实际通信效果，应使用代理执行后重新采集的数据。传输误码率、CRC、业务时延由通信实验负责，本包只输出可检测性指标。

现有 CNN 若用于指导 GAN 反复选择方案，其测试分数不能单独作为最终泛化结论。最终评估应另留独立会话和未参与调优的检测器。当前交付不包含 GAN 实际性能结果。
