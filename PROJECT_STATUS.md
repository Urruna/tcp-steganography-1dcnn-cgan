# 项目状态总表

状态取值：`已完成` / `部分完成` / `设计阶段` / `未实现` / `未确认`。

| 模块 | 状态 | 位置 | 说明 |
| --- | --- | --- | --- |
| 网络链路 | 已完成 | `src/tcp_lab/`、`src/normal_file_transfer/`、`src/protocol_stego/examples/` | Client → Proxy-A → Proxy-B → Server 三条链路均已实际运行 |
| Docker | 已完成 | `src/tcp_lab/docker-compose.yml`、`src/normal_file_transfer/compose.yaml`、`src/protocol_stego/compose.yaml` | Docker / Compose 环境可构建可运行；protocol_stego 是单测试容器，不是四容器链 |
| 加密 | 已完成 | `src/crypto/` | AES-256-GCM，含密钥生成、PBKDF2 派生、nonce、tag、固定 30 字节开销，自检通过 |
| 协议 | 已完成 | `src/newtry97/framing.py`、`src/protocol_stego/core/framing.py`、`core/reassembly.py` | Preamble / Version / Frame ID / Length / Payload / CRC 均已实现，测试通过 |
| 隐写 | 已完成 | `src/protocol_stego/core/modulation.py`、`src/protocol_stego/proxy/` | 800/1200 应用层写入长度调制已实现并验证 |
| 数据集 | 部分完成 | `datasets/protocol_stego/` | 2026-09-26 扩容后：233 Normal + 233 Stego 全部成功，1398 窗口（699/699）；session 级划分 374/46/46 = 1122/138/138 窗口；BER = FER = CRC 失败 = 0。Normal 仍是固定 1024 字节写入，因此检测任务本质上仍是「800/1200 签名识别」。详见 `docs/experiments/dataset-scaleup-20260926.md` |
| 1D-CNN | 部分完成 | `src/1dcnn/` | 代码、已训练权重、推理接口、测试与结果文件齐全；但指标基于另一套 168 窗口数据且无 session 索引，session 隔离与跨 session 泛化均未验证 |
| cGAN | 部分完成 | `src/cWGAN-GP/` | 条件 WGAN-GP 已实现（生成器只输出长度通道，投影到两个互不重叠的长度区间）；数据量门槛已于 2026-09-26 满足（train 1122 窗口 > 要求的 1000），但训练尚未跑通，原因是数据接口不一致，因此无 checkpoint、无合成数据、无 GAN-Stego 结果。详见 `docs/experiments/cwgan-results.md` |

补充状态：

| 项目 | 状态 | 证据 |
| --- | --- | --- |
| 规则基线 | 已完成 | `docs/experiments/baseline-analysis.md` |
| 逻辑回归基线 | 已完成 | 同上 |
| 历史 Docker Normal 数据 | 部分完成 | 早期 Docker 冒烟数据，2 个代理侧 session / 4 个事件 |
| `normal_v1` 文件传输数据集 | 已完成（代码+数据） | `datasets/normal_v1/`，8 次下载，3,082,890 字节 |
| pcap 抓包 | 未实现 | 仓库内没有任何 `.pcap` 文件 |
| FEC / 重传 | 未实现 | 协议代码中不存在 |
| GAN-Stego 数据 | 未实现 | 没有生成器，也没有数据集 |
| cWGAN-GP 数据接口 | 部分完成 | `src/cWGAN-GP/cWGAN-GP.py` 需要 `datasets/protocol_stego/` 下的 `real_train_X.npy` / `real_train_y.npy`，仓库里只有 `processed/windows.npz`；且长度区间常量假定长度通道已标准化 |
| 失败 Stego session | 已记录 | 扩容过程中 8 个 session 报 `length_out_of_range`，已移到虚拟机的 `protocol_stego/raw_failed/stego/`（未删除，不属于数据集），并已补采替换 |
| 数据集发布包 | 部分完成 | `releases/dataset_release_v1/` 仍是 46 个 session 的旧快照，扩容后未重新生成 |
