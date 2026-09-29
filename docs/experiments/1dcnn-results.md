# 1D-CNN 实验结果

## 模块位置

```text
src/1dcnn/
```

模块包含：

- 两层 1D-CNN（`cnn_model.py`）；
- 训练 / 评估流程（`train.py`、`evaluate.py`、`run_all.py`）；
- 冻结的推理接口（`detector.py`、`gan_interface.py`）；
- 逻辑回归与 800/1200 规则基线；
- 已训练权重（`models/best_model.pt`）；
- 结果报告与图表（`results/`）；
- 流程测试（`tests/test_pipeline.py`）。

## 本模块使用的数据

模块自带一套数据集：

```text
data/real_{train,val,test}_{X,y}.npy
data/scaler_params.npz
```

规模与标签：

| 划分 | 样本数 | Normal | Stego |
| --- | ---: | ---: | ---: |
| train | 117 | 32 | 85 |
| val | 26 | 6 | 20 |
| test | 25 | 10 | 15 |

输入形式：

```text
X = [N, 4, 128]
特征 = direction, write_len, interval, cum_bytes
标签 = 0 Normal，1 Baseline-Stego
```

数据集说明中记录的窗口配置是 `window=128`、`step=64`，并且**没有
session 索引**。

## 与仓库数据集的关系

仓库当前的 `datasets/protocol_stego/processed/windows.npz` 含 1398 个窗口
（`window=128`，互不重叠），类别均衡（699 Normal / 699 Stego）。

1D-CNN 模块的 168 个窗口与这 1398 个窗口**精确重叠为 0**。在确认它们的
生成方式和到 session 的映射之前，必须把它们当作一套独立数据。

## 模型

```text
Conv1d(4, 32, kernel=5, padding=2)
→ BatchNorm → ReLU → MaxPool(2)
→ Conv1d(32, 64, kernel=5, padding=2)
→ BatchNorm → ReLU → GlobalAveragePooling
→ Dropout(0.3)
→ Linear(64, 2)
```

训练配置：

| 项目 | 取值 |
| --- | --- |
| 随机种子 | 42 |
| 轮数 | 100 |
| batch size | 32 |
| 学习率 | 0.001 |
| weight decay | 0.0001 |
| Dropout | 0.3 |
| 类别加权 | 开启 |
| 判定阈值 | 0.5，训练前固定 |
| 设备 | CPU |

训练过程没有读取测试集。

## 已报告的测试结果

| 模型 | Accuracy | Precision | Recall | F1 | ROC-AUC | TN/FP/FN/TP |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| CNN | 0.9200 | 0.8824 | 1.0000 | 0.9375 | 0.9867 | 8/2/0/15 |
| 逻辑回归 | 0.8800 | 1.0000 | 0.8000 | 0.8889 | 1.0000 | 10/0/3/12 |
| Rule8001200 | 0.8800 | 1.0000 | 0.8000 | 0.8889 | — | 10/0/3/12 |

已记录的软件测试：

```text
6 tests OK
```

## 运行方式

```bash
cd src/1dcnn
python -m pip install -r requirements.txt

# 评估已保存的模型
python evaluate.py

# 运行流程 / 接口测试
python -m unittest discover -s tests -v

# 从头重新训练（会覆盖 models/ 与 results/）
python run_all.py
```

如果需要保留已交付的结果文件，请先复制一份目录再重训。

## 已知局限

1. **session 隔离未经验证。**
   `results/data_check.json` 明确记录 `session_split_verified: false`，
   且没有提供窗口到 session 的映射。

2. **与 `datasets/protocol_stego` 不是同一套数据。**
   本模块用的是 168 个 `step=64`（近似重叠）的窗口，仓库数据集用的是
   1398 个互不重叠的窗口，精确重叠为 0。

3. **测试集太小。**
   测试集只有 25 个窗口，多对一个就相当于准确率变化 4 个百分点。

4. **类别不均衡。**
   模块数据集不均衡（例如 train 为 32 Normal / 85 Stego）。

5. **没有 GAN-Stego 数据。**
   GAN 接口存在，但没有评估过任何真实 GAN 生成的窗口。不要把接口演示
   结果当作 GAN 结果。

6. **只有应用层特征。**
   这些结果不是抓包层面、也不是真实网络环境下的检测结果。

## 建议的下一步

在把这个模型当作正式的跨 session 检测器之前：

1. 拿到 168 窗口数据集的生成脚本与 session ID；
2. 按 session 重新划分 train/val/test；
3. 只在训练集上重新拟合 scaler；
4. 重新训练并记录新的指标；
5. 现有结果仅作为「流程跑通」的初步结果保留。
