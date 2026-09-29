# 数据集总览

## 1. 历史 Docker Normal 数据集

- 来源：Ubuntu `/home/urruna/docker/tcp-lab/logs/`
- 仓库副本：`datasets/historical/docker_chain_smoke/`
- 类型：早期 Docker TCP 链的正常流量
- 载荷：`hello network`（13 字节）
- session：2 个代理侧 session（Proxy-A + Proxy-B）
- 事件：4 个（正向 / 反向）
- 格式：CSV
- 无调制、无秘密数据
- 无 pcap
- 已知局限：数据量极小，只是早期的冒烟测试

## 2. 历史 `baseline_lenmix_v1`

- 仓库副本：`datasets/historical/baseline_lenmix_v1/`
- 类型：更早的正常流量基线
- 1 次实验 / 1 个 session
- 256 个 client 事件（全部通过）
- 512 个 Proxy-A 事件（256 正向 + 256 反向）
- 512 个 Proxy-B 事件（256 正向 + 256 反向）
- 长度循环使用 64、128、256、512、1024 字节
- 无调制、无 pcap
- 来源环境：早期 Ubuntu 20.04 VMware 原生多进程实验，不是当前
  protocol_stego 的 Docker 对照组

## 3. `normal_v1` 文件传输数据集

- 仓库副本：`datasets/normal_v1/`
- 源码：`src/normal_file_transfer/`
- 类型：经代理链的正常 Docker 文件下载
- 8 次下载，全部通过 SHA-256 校验
- client 事件：8
- Proxy-A 事件：771（8 正向，763 反向）
- Proxy-B 事件：773（8 正向，765 反向）
- server 事件：8
- 总字节数：3,082,890
- 文件：64 KiB / 256 KiB / 1 MiB
- 无 800/1200 调制

## 4. protocol_stego 数据集（当前主数据集）

- 工作目录：`datasets/protocol_stego/`
- 发布副本：`releases/dataset_release_v1/protocol_stego/`
- 原始 Normal session：233（全部成功）
- 原始 Stego session：233（全部成功）
- 事件总数：210165
- 处理后窗口：1398
- Normal 窗口：699
- Stego 窗口：699

该数据集最初是 23 + 23 个 session、138 个窗口，2026-09-26 完成扩容，
详见 `docs/experiments/dataset-scaleup-20260926.md`。

处理后形状：

```text
X.shape = [1398, 4, 128]
y.shape = [1398]
```

标签：

```text
0 = Normal
1 = Stego（800/1200 应用层长度调制）
```

按 session 划分：

```text
train：374 个 session，1122 个窗口
val：   46 个 session， 138 个窗口
test：  46 个 session， 138 个窗口
```

校验结论：

- train/val/test 之间没有 session 重叠；
- 没有重复样本；
- 没有 NaN / Inf；
- BER = 0；
- 帧错误率 = 0；
- CRC 失败率 = 0。

长度分布（已记录的局限）：Normal 事件恒为 1024 字节，Stego 事件恒为
800 或 1200 字节；两个类别的 `direction` 通道都恒为 1。因此在这套数据上
训练出来的检测器学到的是「800/1200 调制签名」，而不是一般意义上的
隐蔽信道可检测性。

## 5. 尚未生成的数据

- pcap 数据集；
- GAN-Stego 数据集；
- 不同 RTT / 带宽 / 丢包条件下的数据集。
