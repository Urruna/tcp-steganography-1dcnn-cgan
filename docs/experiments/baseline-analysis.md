# BASELINE ANALYSIS

Verdict: **READY_FOR_CNN**

## 1 数据稳定性

- X.shape: [138, 4, 128]
- y.shape: [138]
- class distribution: {'normal': 69, 'stego': 69}
- train shape: [114, 4, 128]
- val shape: [12, 4, 128]
- test shape: [12, 4, 128]
- split overlaps: {'train_val': [], 'train_test': [], 'val_test': []}

## 2 800/1200 调制稳定性

调制稳定性与 BER/FER/CRC 详见 `DATA_QUALITY_REPORT.md`。 本次扩采后所有 Stego session 的 BER/FER/CRC 统计为 0。

## 3 Normal / Stego 分布差异

- Normal 主要以 1024 B 写块为主，少量 320 B 来自 TCP 分段。
- Stego 由 800/1200 B 调制写块构成。
- 其他统计特征（duration、event count、total bytes、inter-arrival）两者接近，主要差异来自 800/1200 modulation 本身。

## 4 Rule-based baseline

- rule_any_800_1200: all=(accuracy=1.000000, precision=1.000000, recall=1.000000, F1=1.000000, CM(tn/fp/fn/tp)=69/0/0/69)
- rule_mean_length_le_1000: all=(accuracy=0.811594, precision=1.000000, recall=0.623188, F1=0.767857, CM(tn/fp/fn/tp)=69/0/26/43)
- rule_majority_800_1200: all=(accuracy=1.000000, precision=1.000000, recall=1.000000, F1=1.000000, CM(tn/fp/fn/tp)=69/0/0/69)
- rule_any_800_1200: test=(accuracy=1.000000, precision=1.000000, recall=1.000000, F1=1.000000, CM(tn/fp/fn/tp)=6/0/0/6)
- rule_mean_length_le_1000: test=(accuracy=0.833333, precision=1.000000, recall=0.666667, F1=0.800000, CM(tn/fp/fn/tp)=6/0/2/4)
- rule_majority_800_1200: test=(accuracy=1.000000, precision=1.000000, recall=1.000000, F1=1.000000, CM(tn/fp/fn/tp)=6/0/0/6)

## 5 Traditional ML baseline

- model=logistic_regression_summary_features, features=16, train=114, val=12, test=12
- val: accuracy=1.000000, precision=1.000000, recall=1.000000, F1=1.000000, CM(tn/fp/fn/tp)=6/0/0/6
- test: accuracy=1.000000, precision=1.000000, recall=1.000000, F1=1.000000, CM(tn/fp/fn/tp)=6/0/0/6

## 6 是否适合进入 1D-CNN

结论：**READY_FOR_CNN**

说明：rule-based 与 Logistic Regression 已经能在 session-level split 上高准确率区分 Normal/Stego；但当前 Normal 的 1024 B 写块较单一，因此 CNN 结果主要解释为对 800/1200 调制特征的检测，不能直接推广为一般隐写可检测性。

## 7 下一步

- 若继续扩采，优先增加 Normal 业务多样性（不同文件大小、HTTP 双向业务）。
- 扩采时必须保持 session-level train/val/test 划分与 seed 可复现。
- 训练 CNN 时同时报告 rule-based 与 Logistic Regression 基线，避免只报 CNN 准确率。

