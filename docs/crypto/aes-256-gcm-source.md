# newtry97 加密层设计与使用说明

日期：2026-09-19

## 0 任务目标

本目录只做一件事：为后续隐写编码提供一个**可正确解密、长度可控、两端共享密钥**
的内容加密层。它解决“秘密内容看不懂”，但**不解决“流量看起来正常”**。

对应本次提出的四条要求：

| 要求 | 本设计 |
| --- | --- |
| 1. `Decrypt(Encrypt(M,K),K)=M` | 自检中做多轮随机往返验证 |
| 2. 不破坏后续隐写编码 | 固定开销 30 B；可选固定长度填充模式 |
| 3. 接收端用同一密钥恢复密文 | 预共享 32 B 密钥；支持口令派生 |
| 4. 加密安全 ≠ 流量隐蔽 | 单独分层说明，不把密码学结论当隐写结论 |

## 1 算法选择

选用 **AES-256-GCM**（AEAD：同时提供机密性与完整性）。

原因：

- 标准算法，Python `cryptography` 库直接提供；
- 加密与认证一次完成，接收端能识别密钥错误或密文被篡改；
- 密文长度 = 明文长度 + 固定开销，不产生不可控扩张；
- 随机 nonce 让同一明文每次得到不同密文，符合“随机比特串”的预期。

没有选用：

- AES-CBC：需要额外设计 HMAC，组合容易出错；
- ECB：相同明文块产生相同密文，不适合本项目；
- 自己实现密码算法：工程上不可取，容易引入不可验证的安全缺陷。

## 2 密文格式与长度

密文包格式：

```text
| Header(1B) | Flags(1B) | Nonce(12B) | Ciphertext | GCM Tag(16B) |
```

- Header：高 4 bit 为版本号，低 4 bit 为算法编号；
- Flags：bit0 表示是否使用固定长度填充；
- Nonce：每条消息随机生成 12 B，绝不复用；
- Ciphertext：AES-GCM 输出的密文；
- Tag：16 B 认证标签，防止篡改和错误密钥。

固定开销：

```text
1 + 1 + 12 + 16 = 30 字节
```

普通模式：

```text
len(ciphertext) = len(plaintext) + 30
```

固定长度模式（`pad_to`）：

```text
明文先加 4 B 长度前缀，再补零到 pad_to 字节；
len(ciphertext) = pad_to + 30
```

示例：

| 明文 | 模式 | 明文长度 | 密文长度 |
| --- | --- | ---: | ---: |
| `HELLO` | 普通 | 5 | 35 |
| `Hello from A to B (newtry97)` | 普通 | 28 | 58 |
| `HELLO` | `pad_to=64` | 5 | 94 |
| 任意 ≤ 60 B 消息 | `pad_to=64` | - | 94 |

这意味着：

- 消息长度变化只带来固定 30 B 开销，帧长可精确计算；
- 如果实验要求“固定容量”，用 `pad_to` 把载荷固定到指定字节数；
- 不会出现“加密后长度随机波动”的情况。

## 3 密钥管理

支持两种密钥来源：

1. `keygen`：生成 32 B 随机密钥，适合实验环境；
2. `derive-key`：用 PBKDF2-HMAC-SHA256（200,000 次迭代）从口令派生 32 B 密钥。

实验拓扑中：

```text
Client / Proxy-A  ── K ──> encrypt(message) ──> 密文
Proxy-B           ── K ──> decrypt(ciphertext) ──> message
```

两端必须使用同一个 `K`。本阶段通过预共享密钥/密钥文件解决；
真正的密钥分发、轮换、前向保密不属于当前实验范围。

注意：

- GCM 的 nonce 在同一密钥下不可重复；本实现每条消息随机生成；
- AAD 可选，但加密与解密必须传入相同 AAD；
- 认证失败时解密封装会抛 `CryptoError`，不会返回错误明文。

## 4 与隐写层的关系

加密层输出的是**载荷**，隐写层负责把载荷变成 0/1 比特，再映射成
应用层写入分块与时间节奏。

推荐调用顺序：

```text
message
  → encrypt(message, K, pad_to=P)     # 本目录
  → payload (固定长度 P+30)
  → framing.build_frame(payload)      # newtry97/framing.py
  → bits
  → 0/1 调制（长度等级 / 拆分 / 间隔）
```

帧长可精确计算。以 v0.2 帧格式（Preamble 4 B + Version/Frame ID/Length 5 B
+ CRC 2 B，共 11 B 额外开销）为例：

```text
帧字节数 = (30 + P) + 11
帧比特数 = ((30 + P) + 11) * 8
```

因此：

- 普通模式：`帧比特数 = (len(M) + 41) * 8`；
- 固定长度模式：`帧比特数 = (P + 41) * 8`，与消息长度无关。

## 5 加密、隐写、cGAN 不是同一件事

这是本项目实验设计的关键边界：

| 层次 | 解决的问题 | 本设计的角色 |
| --- | --- | --- |
| 加密 | 内容看不懂 | AES-256-GCM |
| 隐写 | 看不出有秘密通信 | Proxy-A/B 的分块与节奏调制 |
| cGAN | 让流量特征更接近正常分布 | 后续训练与策略优化 |

例如：

```text
0 → 约 800 B
1 → 约 1200 B
```

即使这些长度对应的是 AES 密文片段，观察者仍可能从长度序列发现异常。
AES 的安全性不能替代流量特征隐藏；cGAN 也不能替代密码学认证与密钥管理。

## 6 目录与文件

```text
crypto/
├── crypto.py          # 加密/解密核心库
├── crypto_tool.py     # CLI：keygen / derive-key / encrypt / decrypt / demo / selftest
├── requirements.txt   # cryptography
├── Dockerfile         # 可复现实验镜像
├── compose.yaml       # 一键自检
└── crypto.md          # 本文档
```

## 7 使用说明

构建并运行自检（推荐）：

```bash
cd /home/urruna/docker/tcp-lab/crypto
docker compose up --build
```

自检会验证：

- 多轮随机长度 `Decrypt(Encrypt(M,K),K)=M`；
- 密文长度恒为 `len(M)+30`；
- 固定长度模式长度恒定且可正确还原；
- 篡改 1 bit 能被检测；
- 错误密钥无法解密。

命令行示例：

```bash
# 生成 32 B 密钥
python3 crypto_tool.py keygen --out secret.key
python3 crypto_tool.py keygen --hex

# 从口令派生密钥（两端使用同一口令）
python3 crypto_tool.py derive-key --passphrase '实验口令' --out secret.key

# 普通加密/解密
python3 crypto_tool.py encrypt --input message.txt --output message.enc --key-file secret.key
python3 crypto_tool.py decrypt --input message.enc --output message.dec --key-file secret.key

# 固定长度模式（payload 固定 64 B，密文固定 94 B）
python3 crypto_tool.py encrypt --input message.txt --output message.pad.enc \
  --key-file secret.key --pad-to 64
python3 crypto_tool.py decrypt --input message.pad.enc --output message.dec \
  --key-file secret.key

# 生成演示样本与自检报告
python3 crypto_tool.py demo --out-dir out
python3 crypto_tool.py selftest --iterations 200 --report out/crypto_selftest.json
```

## 8 实测结果

执行环境：Ubuntu6.21（VMware），Docker Compose v2.27.1，
镜像 `crypto-node:1`，Python 3.11 + `cryptography 50.0.1`。

执行命令：

```bash
cd /home/urruna/docker/tcp-lab/crypto
docker compose up --build
```

自检报告：

```json
{
  "rounds": 200,
  "overhead_bytes": 30,
  "padded_ok": true,
  "tamper_detected": true,
  "wrong_key_detected": true,
  "passed": true
}
```

演示样本（`demo`）：

| 明文 | 明文长度 | 普通密文 | 固定长度密文（pad_to=64） |
| --- | ---: | ---: | ---: |
| `HELLO` | 5 | 35 | 94 |
| `Hello from A to B (newtry97)` | 28 | 58 | 94 |
| 空文件 | 0 | 30 | 94 |

产物位于：

```text
/home/urruna/docker/tcp-lab/crypto/out/
├── crypto_selftest.json
├── demo.key
├── hello.txt.enc
├── hello.txt.padded.enc
├── secret28.txt.enc
├── secret28.txt.padded.enc
├── empty.bin.enc
└── empty.bin.padded.enc
```

结论：

- 要求 1 已验证：200 轮随机长度往返 `Decrypt(Encrypt(M,K),K)=M` 全部通过；
- 要求 2 已验证：普通模式开销恒为 30 B，固定长度模式长度恒为 `pad_to+30`；
- 要求 3 已验证：错误密钥无法解密；
- 要求 4 已在第 5 节单独说明，加密层不负责流量隐蔽。

构建时遇到并处理的问题：

- Docker 构建容器最初无法解析 PyPI 域名（容器 DNS 指向 VMware NAT 网关，
  解析失败）。在 `/etc/docker/daemon.json` 中加入
  `"dns": ["223.5.5.5", "119.29.29.29"]` 并重启 Docker 后，
  容器 DNS 与 PyPI 安装恢复正常。

## 9 已知限制与后续工作

1. 本设计只保证内容机密性与完整性，不保证流量不可检测；
2. 当前默认使用固定 KDF salt、预共享密钥，后续应加入会话级随机 salt 与密钥轮换；
3. nonce 由发送端随机生成并随密文传输，需继续确认密钥生命周期内不复用；
4. 固定长度填充会消耗容量，后续需要结合 scheduler 做容量与时延权衡；
5. 与 `newtry97/framing.py`、Proxy-A/B 的集成需要在下一阶段用端到端实验验证。
