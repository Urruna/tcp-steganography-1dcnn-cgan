# AES-256-GCM

## 算法

实现位置：`src/crypto/crypto.py`

算法：AES-256-GCM（AEAD）。

## 数据格式

```text
Header(1B) | Flags(1B) | Nonce(12B) | Ciphertext | Tag(16B)
```

固定开销：

```text
1 + 1 + 12 + 16 = 30 字节
```

## 密钥

- `keygen()` → 32 字节随机密钥（`os.urandom`）；
- `derive_key(passphrase)` → PBKDF2-HMAC-SHA256，默认 200000 轮；
- 默认 salt：`newtry97-crypto-v1`；
- 当前实验使用预共享密钥或确定性派生密钥。

未实现：密钥交换、密钥轮换、每 session 随机 salt。

## Nonce

- 每条消息 12 字节随机值；
- 随密文一起传输；
- 绝不允许与同一密钥重复使用。

## 认证标签（Authentication Tag）

- 16 字节；
- 由 AES-GCM 生成；
- 密钥错误或密文被篡改都会抛出 `CryptoError`。

## 接口

```python
from crypto import encrypt, decrypt, keygen, derive_key

key = keygen()
blob = encrypt(b"message", key)
plain = decrypt(blob, key)
```

定长模式：

```python
blob = encrypt(b"message", key, pad_to=64)
```

## 加密流程

```text
明文
 → 可选的长度前缀 + 零填充
 → AES-256-GCM(key, nonce)
 → Header + Flags + Nonce + Ciphertext + Tag
```

## 解密流程

```text
密文块
 → 校验 Header/Flags
 → 取出 nonce
 → AES-256-GCM 解密 + 标签验证
 → 可选地去除填充
 → 明文
```

## 示例

来源：`src/crypto/crypto.md`、`src/crypto/crypto_tool.py`。

```bash
cd src/crypto
docker compose up --build
```

实测输出：

```text
HELLO                  -> 35 B 普通 / 94 B pad_to=64
Hello from A to B ...  -> 58 B 普通 / 94 B pad_to=64
empty                  -> 30 B 普通 / 94 B pad_to=64
```

自检结果：

```text
rounds=200, overhead=30, padded_ok=true,
tamper_detected=true, wrong_key_detected=true
```

## 局限

- 只保证内容机密性；
- 不隐藏任何流量特征；
- 实验模式下 KDF salt 固定；
- 没有密钥交换与轮换。

相关源码说明见 `docs/crypto/aes-256-gcm-source.md`。
