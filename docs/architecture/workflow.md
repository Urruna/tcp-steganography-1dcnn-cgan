# 工作流

## 目标工作流（来自 `new_727.md`）

```text
Normal Traffic
      ↓
Basic Stego
      ↓
Dataset
      ↓
1D-CNN
      ↓
cGAN
      ↓
GAN-Stego
      ↓
Evaluation
```

## 当前完成度

| 阶段 | 状态 | 证据 |
| --- | --- | --- |
| Normal Traffic | 部分完成 | 历史 Docker normal、`normal_v1`、protocol_stego 的 233 个 Normal session |
| Basic Stego | 已完成 | 800/1200 长度调制，233 个 Stego session，BER = 0 |
| Dataset | 部分完成 | 466 个 session、1398 个窗口、session 级划分、质量报告 |
| 1D-CNN | 部分完成 | `src/1dcnn/` 中已实现并训练；初步指标使用的是另一套 168 窗口数据，session 划分未验证 |
| cGAN | 部分完成 | `src/cWGAN-GP/` 有代码；数据量门槛已满足，但训练尚未跑通，无 checkpoint、无结果 |
| GAN-Stego | 未实现 | 没有生成器，也没有数据 |
| Evaluation | 部分完成 | 目前只有规则基线与逻辑回归基线 |

## 数据流

```text
明文
 → AES-256-GCM
 → 密文
 → 帧封装
 → 比特流
 → 800/1200 应用层长度调制
 → TCP
 → Proxy-B 长度恢复
 → 帧解码 / CRC / 重组
 → AES-256-GCM 解密
```

## 分析流

```text
原始 session JSONL
 → observed_length 事件流
 → 128 事件窗口
 → X = [N, 4, 128]
 → session 级 train/val/test
 → 规则 / 逻辑回归 / 后续 CNN
```
