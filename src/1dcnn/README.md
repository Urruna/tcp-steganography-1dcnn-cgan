 # 1D-CNN 检测模块

这份文件包包含实现、训练、测试、实际实验结果和外部/GAN 对接接口。数据为本次提供的 168 个窗口；输入 `[N,4,128]`，标签 `0=Normal`、`1=Baseline-Stego`。

模型已训练，结果在 `results/`，可以先看结果，再决定是否重新训练。首次使用请先安装依赖。

## 1. 文件清单

| 部分 | 文件 | 用途 |
|---|---|---|
| 实现 | `cnn_model.py` | 两层 1D-CNN 网络 |
| 数据 | `data_utils.py` | 加载数组、维度检查、scaler、数据审计 |
| 训练 | `train.py` | 训练、验证、早停、保存最佳模型 |
| 参数 | `config.json` | 种子、轮数、学习率、目录等 |
| 测试 | `evaluate.py` | 测试 CNN，并运行规则和逻辑回归对照 |
| 指标 | `metrics.py` | 指标计算、预测明细、图表 |
| 一键运行 | `run_all.py` | 检查数据 → 训练 → 测试 → 生成结果报告 |
| 对接 | `detector.py` | 加载模型，提供 `predict_proba`、`predict` |
| GAN 对接 | `gan_interface.py` | 通过 Python 调用或命令行评估外部窗口 |
| 对接说明 | `INTERFACE.md` | 输入格式、调用示例、输出含义 |
| 程序验证 | `tests/test_pipeline.py` | 原始/标准化输入一致性、批量推理等检查 |
| 已训练模型 | `models/best_model.pt` | CNN 权重、阈值、输入配置、scaler 校验值 |
| 对照模型 | `models/logistic_baseline.joblib` | 训练集拟合的逻辑回归流程 |
| 数据文件 | `data/` | 原始提供的 8 个文件及数值形式的 scaler |
| 结果 | `results/result_report.md` | 本次实际运行结果及局限 |
| 人工事项 | `MANUAL_TODO.md` | 需要数据/GAN 队友提供的内容 |
| 环境 | `requirements.txt`、`environment_used.txt` | 安装依赖和本次实际版本 |

## 2. 安装环境

建议 Python 3.10–3.12。电脑 CPU 就能运行这批小数据，不要求 CUDA 或 Docker。

进入解压后的目录，在终端运行：

```bash
python -m venv .venv
```

Windows PowerShell 激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 不允许激活，可直接用虚拟环境解释器，不需要更改系统策略：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe evaluate.py
```

macOS/Linux 激活：

```bash
source .venv/bin/activate
```

激活后安装：

```bash
python -m pip install -r requirements.txt
```

Windows/Linux 若只想安装 CPU 版 PyTorch，可先运行以下命令，再安装 requirements：

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

macOS 直接使用前面的 requirements 命令。默认 `device=cpu`，方便复现；不需要手动设置显卡。

## 3. 直接测试已有模型

```bash
python evaluate.py
```

使用已训练的 `models/best_model.pt`，重新生成 CNN 指标、预测明细和图表；对照模型会重新用训练集拟合。不会修改 CNN 权重。

可运行程序验证：

```bash
python -m unittest discover -s tests -v
```

它验证接口与保存结果的一致性，不替代独立数据上的检测效果评估。

## 4. 从头运行

```bash
python run_all.py
```

执行数组检查、训练、测试和报告生成。会更新 `models/` 与 `results/` 中的文件；若想保留交付时的结果，先复制整个目录。

只训练：

```bash
python train.py
```

只训练后需要再运行 `evaluate.py` 更新测试结果；完整报告由 `run_all.py` 统一生成。默认路径相对于本项目目录，不依赖你的用户名或绝对磁盘路径。

## 5. 看哪些结果

| 文件 | 内容 |
|---|---|
| `results/result_report.md` | 汇总报告，优先看 |
| `results/comparison.csv` | CNN、逻辑回归、规则检测对比，Excel 可打开 |
| `results/cnn_metrics.json` | 训练/验证/测试完整指标 |
| `results/cnn_test_predictions.csv` | 每个测试样本的真实标签、预测、隐写分数 |
| `results/training_curves.png` | 训练与验证的 loss/F1 曲线 |
| `results/confusion_matrix.png` | 正常/隐写的正确、误报和漏检数量 |
| `results/roc_curve.png` | 测试集 ROC 曲线 |
| `results/history.csv` | 每轮训练记录 |
| `results/training_summary.json` | 参数、最佳轮次、环境信息 |
| `results/data_check.json` | 样本数、重复检查、输入文件校验值 |
| `results/run.log` | 本次运行日志 |
| `results/software_tests.txt` | 交付前程序验证记录 |

## 6. 给其他模块的文件

把整个文件包交给 GAN 队友，让其看 `INTERFACE.md`。

如果只交推理部分，需要：`cnn_model.py`、`data_utils.py`、`detector.py`、`models/best_model.pt`、`data/scaler_params.npz`。命令行 GAN 评估还需要 `gan_interface.py`、`metrics.py` 和依赖。

GAN 内部判别器与这里的独立 CNN 检测器是不同角色；此接口用于固定检测器的离线评估，不实现 GAN 的生成器、判别器或代理调度。

## 7. 数据与实验约定

- 本批 X 已标准化，训练和直接测试时不要再次标准化。
- `scaler_params.npz` 从原 `real_scaler.pkl` 提取数值参数；本包推理无需加载旧版本 pickle。
- 标准化方法：按 C 顺序将 `[4,128]` 展平为 512 维，逐位置变换，再还原形状。
- 训练使用类别加权损失；模型选择按验证集 loss；阈值预先固定为 0.5。
- 测试结果没有用于调参。固定种子可帮助复现，但不同 PyTorch 版本和硬件不保证逐位一致。
- 25 个测试窗口只支持当前数据上的初步结论。会话隔离未核验，不把当前指标写成已验证的跨会话泛化能力。
- 更换数据时不能只替换部分文件：应提供一致的三个划分及相匹配的 scaler，并重新训练。新 scaler 的导出与验证应沿用数据生成流程。

## 8. 参考方案

- 项目仓库：<https://github.com/Urruna/tcp-steganography-1dcnn-cgan>。

本文件包为独立新增模块，没有更改远程仓库、代理代码或原始数据。
