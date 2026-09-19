# newtry97 实现记录：代理转发中的“正常流量”隐蔽传输 v0.2

> 关联项目：《基于代理转发与 1D-CNN/cGAN 的授权 TCP 流量隐写及可检测性评估研究》（`D:\C\work_DC\new_727.pdf`）
>
> 关联虚拟机：Ubuntu6.21（VMware，位于 `D:\ctf\ubuntu\newtry6.21\Ubuntu6.21.vmx`）
>
> 虚拟机内既有项目路径：`/home/urruna/docker/tcp-lab/`
>
> 本文件记录第一版可运行的隐蔽传输：不改变任何业务字节，只利用 Proxy-A → Proxy-B 转发时的应用层写入分块/节奏来携带秘密帧。

## 0 一句话结论

**已实现并跑通**：在 `Client → Proxy-A → Proxy-B → Server` 的四节点 TCP 链路上，Proxy-A 把一条 `Hello from A to B (newtry97)` 秘密消息编码进 312 bit 的转发分块中；Proxy-B 用滑窗搜索 Preamble 并恢复出整帧（`frame_id=0`），CRC-16 校验通过；Client 正常业务 344/344 行全部正确回显，Server 收到的字节与 Client 发送的字节完全一致。

实测输出：

```text
[proxy_b] RECOVERED 312 bits | frame_id=0 | payload='Hello from A to B (newtry97)' | crc=ok
[demo] client echo 344/344
```

代码位于本文件同级的 `newtry97/` 目录，纯 Python 标准库，无 Docker/第三方依赖，可直接拷入 Ubuntu6.21 的 `~/docker/tcp-lab/` 下运行。

---

## 1 设计思路

### 1.1 与 new_727.pdf 的对应

PDF 中建议从“应用层写入长度”入手，并明确第一版应以 Proxy-A/Proxy-B 的**应用层事件日志**为主要依据，抓包只做验证。因此本版没有去改 TCP 头字段，也没有依赖网络层恰好能看到“每个应用层 write 的长度”。

对应关系：

| new_727.pdf 中的阶段 | newtry97 本次完成 |
| --- | --- |
| 普通 TCP 转发 | 沿用/复现 Client→A→B→Server 行式 Echo |
| 单 bit 编码与恢复 | bit 0 = 1 次 write，bit 1 = 2 次 write |
| 短消息连续恢复 | 每行 cover record 承载 1 bit，连续恢复 |
| 分帧/同步字 | 帧首 32 bit Preamble = `0x6E9797A1`，Proxy-B 滑窗搜索 |
| Version / Frame ID | 4 bit Version + 16 bit Frame ID |
| 长度字段 | 16 bit Payload Length |
| CRC | CRC-16/XMODEM |
| 结构化日志 | 已补齐 CSV（见第 7 节） |

### 1.2 为什么选择“行上传/回显”作为 cover business

之前的 `baseline_lenmix_v1` 使用“Client 发送固定长度报文 → Server 回显”的方式，Proxy 日志里天然有明确的方向切换。延续这个模型：

1. Client 每次只发一行 cover record，并等 Server 回显后再发下一行；
2. 因此任一时刻 A→B 方向上最多只有一个 record 在途；
3. Proxy-A 可以按 record 调制，Proxy-B 可以按 record 恢复，不需要额外的带外握手；
4. 整个链路不改业务内容，Server 只是一个普通行式 Echo，对隐蔽数据完全无感知。

### 1.3 调制方式

秘密消息先封装成二进制帧，再展开为比特流。对每一行 cover record：

| 隐蔽比特 | Proxy-A 对 Proxy-B 的写行为 |
| --- | --- |
| 0 | 整行只调用一次 `sendall()`，即 1 个应用层 write |
| 1 | 把同一行从中间拆成两段，`sendall(前半)` → sleep(默认 80 ms) → `sendall(后半)`，即 2 个应用层 write |

Proxy-B 统计“收到一个完整 record 消耗了几个 recv 事件”：1 次恢复为 0，2 次恢复为 1。80 ms 的间隔足以让本地/局域网 TCP 上两个 write 不被接收端合并成一次 recv；若在真实网络中发现合并，可调大 `--gap`。

注意：这里调制的是 **TCP 发送方的应用层写入节奏**，不是往业务字节里塞额外数据。Server 最终收到的是完整行；多余的“隐蔽开销”是时间与分块模式，不是字节数。

---

## 2 协议格式

与 PDF 建议一致，v0.2 帧结构为：

```text
| Preamble (32 bit) | Version(4 bit)+Reserved(4 bit)
  | Frame ID (16 bit) | Payload Length (16 bit) | Payload | CRC-16 (16 bit) |
```

具体约定：

| 字段 | 长度 | 取值 |
| --- | --- | --- |
| Preamble | 32 bit | `0x6E9797A1`，Proxy-B 用滑窗在 bit 流中搜索 |
| Version | 4 bit | `1`，与 Reserved 合成 1 字节（高 4 bit） |
| Frame ID | 16 bit | 帧序号，大端 |
| Payload Length | 16 bit | Payload 的字节数，大端 |
| Payload | 0–512 B | 实际秘密消息（UTF-8） |
| CRC-16 | 16 bit | 对 Preamble 之后的全部字段计算 CRC-16/XMODEM |

示例：`Hello from A to B (newtry97)` 长 28 字节，帧共 4+1+2+2+28+2=39 字节，
共 312 bit。`run_demo.py` 默认在其前放 16 行正常 cover、之后放 16 行，
因此总业务行数为 344 行，用于验证 Proxy-B 不从第 1 行开始解码。

解码端 `FrameDecoder` 不再假设帧从第 1 行开始：它在累积 bit 流中搜索
Preamble，按 Version/Frame ID/Length 解析；CRC 失败时输出 `crc_bad`
事件并继续向后重同步，不破坏正常 TCP 连接。

---

## 3 代码结构

```text
newtry97/
├── framing.py            # 帧组装、bit 展开、CRC-16、帧解析
├── event_log.py          # 结构化 CSV 日志：表头与 baseline 对齐并含隐蔽字段
├── echo_server.py        # Server：普通行式 TCP Echo，不感知隐蔽数据
├── sender_proxy.py       # Proxy-A：透明转发 + 按 bit 拆分 write
├── receiver_proxy.py     # Proxy-B：按 recv 事件恢复 bit + 透明转发
├── covert_client.py      # Client：发送 N 行 cover record 并逐行校验 Echo
└── run_demo.py           # 一条命令在 127.0.0.1 上启动四节点并测试
```

各文件职责：

- `framing.py`：`build_frame(payload)`、`bytes_to_bits()`、`decode_frame(bits)`。
- `event_log.py`：`SessionEventLog`，每次应用层 write/recv 事件写一行 CSV。
- `sender_proxy.py`：`serve(listen, upstream, message, split_gap)`；bit 未结束时对每行执行拆分策略，bit 结束后恢复正常逐行转发。
- `receiver_proxy.py`：`serve(listen, server, recovered_file)`；统计每个完整 record 的 recv 次数，恢复 bit，按 `framing` 校验；恢复成功后若给出 `--recovered-file` 会写文件。
- `covert_client.py`：不知道秘密消息，只负责发送正常 cover 行并校验 Server 回显。
- `run_demo.py`：为方便验收，用 `multiprocessing` 一次性拉起 4 个节点。

---

## 4 实现顺序（对应 PDF 的“先基础后加固”）

1. **普通 TCP 转发**：先让一行文字完整穿过双代理并被 Server 回显。
2. **单 bit**：先只验证 `sendall(整行)` 与 `sendall(两段)` 在 Proxy-B 眼中分别是 1/2 个 recv 事件。
3. **固定短消息**：把 `HELLO` 展开成 8×5 bit，每行 1 bit，连续恢复。
4. **加 Preamble**：用 `0x6E97` 告诉 Proxy-B 帧起点（第一版固定从首行开始）。
5. **加 Length**：让 Proxy-B 知道一共要恢复多少 bit，不会把“秘密结束后的正常行”也算进帧里。
6. **加 CRC**：判断恢复的 Payload 是否完全正确。

---

## 5 运行方法

### 5.1 主机本地一键测试

```bash
cd newtry97
python3 run_demo.py
```

预期输出：

```text
[echo_server] listening 127.0.0.1:9003
[proxy_b] listening 127.0.0.1:9002 -> 127.0.0.1:9003
[proxy_a] listening 127.0.0.1:9001 -> 127.0.0.1:9002, covert_bits=272
[proxy_b] RECOVERED 272 bits | payload='Hello from A to B (newtry97)' | crc=ok
[demo] client echo 304/304
```

### 5.2 手动分四个终端启动（便于观察和后续接日志）

终端 1（Server，端口 9003）：

```bash
python3 echo_server.py --host 127.0.0.1 --port 9003
```

终端 2（Proxy-B，监听 9002，转发到 9003）：

```bash
python3 receiver_proxy.py \
  --listen-host 127.0.0.1 --listen-port 9002 \
  --server-host 127.0.0.1 --server-port 9003 \
  --recovered-file logs/recovered.txt \
  --log-dir logs
```

终端 3（Proxy-A，监听 9001，转发到 9002，携带秘密消息）：

```bash
python3 sender_proxy.py \
  --listen-host 127.0.0.1 --listen-port 9001 \
  --upstream-host 127.0.0.1 --upstream-port 9002 \
  --message "Hello from A to B (newtry97)" \
  --gap 0.08 \
  --log-dir logs
```

终端 4（Client，走 Proxy-A）：

```bash
python3 covert_client.py --host 127.0.0.1 --port 9001 --lines 304
```

如果消息长度改变，cover 行数至少应为 `len(frame) * 8`；`run_demo.py` 会自动计算。

### 5.3 放入 Ubuntu6.21 虚拟机

Ubuntu6.21 已开机（VMware Workstation 中显示为 `Ubuntu6.21`），虚拟机内既有项目路径为：

```text
/home/urruna/docker/tcp-lab/
```

把 `D:\C\work_DC\newtry97/` 整个目录复制到该路径下即可，例如：

```bash
cd ~/docker/tcp-lab
cp -r <host挂载路径>/newtry97 ./newtry97
cd newtry97
python3 run_demo.py
```

也可以先沿用既有 `proxy.py` 的端口习惯：9001/9002/9003。由于本项目只使用 Python 标准库，不需要再装包。

> 提示：在真实 VMware NAT/局域网里如果 Proxy-B 偶尔把两次 write 合成一次 recv，把 `--gap` 提高到 0.10–0.20 秒重测即可；后续第 7 节的“随机化间隔”会解决稳定性和可检测性的权衡。

---

## 6 本次实测记录

测试环境：Ubuntu6.21（VMware）`/home/urruna/docker/tcp-lab/newtry97`，
四个进程全部绑定 127.0.0.1，split gap = 80 ms，帧前 16 行普通 cover。

| 项目 | 结果 |
| --- | --- |
| 秘密消息 | `Hello from A to B (newtry97)` |
| 消息长度 | 28 B |
| 帧长度 | 39 B（Preamble 4B + Version/Frame ID/Length 5B + Payload 28B + CRC 2B） |
| 隐蔽比特数 | 312 bit |
| cover 行数 | 344 行（16 行普通 + 312 行编码 + 16 行普通） |
| Proxy-B 恢复 | 312 bit，`frame_id=0`，滑窗搜索 Preamble 正确 |
| CRC-16 | 通过 |
| Client 正常业务校验 | 344/344 行 Echo 正确 |
| 日志 | `logs/proxy_a_events.csv`、`logs/proxy_b_events.csv`、`logs/recovered.txt` |
| 负载是否被修改 | 否，Server 回显与 Client 发送逐字节一致 |
| 是否需要额外 Python 包 | 否 |

说明：本次在虚拟机回环网络上验证“通信线 + 滑窗重同步”跑通。真实网络下的
BER/FER、时延与可检测性属于下一阶段（第 7 节）的对照实验内容。

---

## 7 从 v0.2 到论文体系的下一步

### 7.1 v0.2 已完成与后续工程项

1. **结构化 CSV 日志（v0.1 已完成，v0.2 保留）**：Proxy-A/B 记录 `timestamp, proxy_name, experiment_id, session_id, direction, event_index, byte_length, inter_event_gap_ms, frame_id, encoded_bit, recovered_bit, crc_status`；`run_demo.py` 生成 `logs/proxy_a_events.csv`、`logs/proxy_b_events.csv` 与 `logs/recovered.txt`。
2. **Preamble 滑窗搜索（v0.2 已完成）**：`FrameDecoder` 维护滑动窗口搜索 32 bit Preamble，再按 Length/CRC 解析。
3. **帧序号与重同步（v0.2 已完成）**：协议加入 16 bit `Frame ID`；CRC 失败时记录 `crc_bad` 事件并继续向后搜索，不破坏正常 TCP 连接。
4. **拆分点随机化（下一步）**：bit=1 时不要总从正中间拆，改为随机切分位置；bit=0/1 之间的时间间隔也随机化，避免形成固定指纹。

### 7.2 检测与优化线

对应 PDF 的阶段设计，后续可以逐步推进：

1. 采集三组流量：Normal（无隐蔽）、Baseline-Stego（固定规则 v0.1）、GAN-Stego（cGAN 辅助）。
2. 从 CSV/抓包提取每会话固定窗口（64/128 事件）的序列特征：方向、数据块长度、相邻发送间隔、累计字节变化。
3. 先训练传统基线（统计特征 + 随机森林/逻辑回归），再训练 1D-CNN。
4. 训练 cGAN 生成更接近 Normal 分布的“候选分块策略”，再把候选约束成 Proxy-A 实际可执行的操作。
5. 画 `秘密传输速率 ↔ BER ↔ 业务时延 ↔ 检测 AUC` 权衡图，而不是只报准确率。

### 7.3 v0.2 已知限制（写论文时也要保留）

- 依赖“逐行上传/回显”的 cover 业务节奏；改成流式下载时需要新的 record 边界定义。
- 只编码在 A→B 一个方向上；后续若要双向同时传，需要处理两个方向的同步。
- 80 ms×312 bit 的原始速率约 12.5 bit/s，容量很低；这是为了第一版稳定，后续通过多等级长度、多 bit/record、时间-长度混合编码提高容量。
- TCP 在真实链路上可能合包/分包，因此第一版以应用层 recv 事件日志为恢复依据，不能只依赖抓包层面的包长度。

---

## 8 边界与授权说明

本实现延续 `new_727.pdf` 的边界设定：只在封闭、授权的实验环境中运行；Server 是普通业务服务，不需要也不感知隐蔽消息；代码不做任何破坏正常 TCP 连接或未经授权的重传/丢包操作。
