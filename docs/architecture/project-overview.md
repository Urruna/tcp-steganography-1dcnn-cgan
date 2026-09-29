# 项目总体说明

## 研究目标

在授权的代理转发环境中研究 TCP 流量特征调制，同时评估秘密数据的可靠交付
与可检测性。

`docs/planning/new_727.md` 中的长期规划包含：

- Normal 流量；
- Baseline-Stego 流量；
- GAN-Stego 流量；
- 1D-CNN 检测器；
- cGAN 特征优化器。

## 两条工程主线

### 通信线

```text
Client → Proxy-A → Proxy-B → Server
```

目标：正常业务流量必须照常工作，Proxy-A 只调制被允许的应用层写入行为。

### 分析线

```text
日志 / 数据集
        ↓
固定长度的滑动窗口
        ↓
规则 / 传统机器学习基线
        ↓
1D-CNN（已实现，初步）
        ↓
cGAN / GAN-Stego（规划中）
```

## 当前实际已完成

已经实现：

- Docker TCP 链；
- AES-256-GCM；
- 帧 + CRC + 比特流 + 重组；
- 800/1200 应用层写入长度隐写；
- 原始数据集与固定窗口的处理后数据集；
- 规则基线与逻辑回归基线；
- 一个带已训练权重与结果文件的 1D-CNN 模块，但它使用的是一套独立的
  168 窗口数据，session 划分未经验证（`src/1dcnn/`）；
- 一个用于生成长度策略的条件 WGAN-GP 模块，但尚未跑通训练
  （`src/cWGAN-GP/`）。

尚未实现：

- GAN-Stego；
- FEC / 重传；
- 基于 pcap 的特征提取。

## 证据来源

- `PROJECT_AUDIT.md`
- `PROJECT_STATUS.md`
- `src/`
- `src/protocol_stego/docs/`
- `releases/dataset_release_v1/`
