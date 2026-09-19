# 实验说明

## 1 运行实验

```bash
cd /home/urruna/docker/tcp-lab/protocol_stego
docker compose build
docker compose run --rm tests python examples/demo_secret_transfer.py
```

## 2 指标定义

- `total_bits`：发送端 bit 总数；
- `bit_error_count`：发送 bit 与接收 bit 不一致的数量；
- `ber = bit_error_count / total_bits`；
- `frame_count`：发送端帧数；
- `received_frame_count`：接收端 CRC 通过的帧数；
- `crc_failure_count`：CRC 失败次数；
- `frame_error_rate`：帧错误数 / 总帧数；
- `duration_ms`：端到端耗时；
- `throughput_secret_Bps`：原始 secret 字节数 / 耗时。

## 3 保存日志

每次运行会覆盖/追加：

```text
logs/sender.jsonl
logs/receiver.jsonl
logs/errors.jsonl
out/experiment_summary.json
```

日志字段尽量统一，便于后续数据管道：

```text
timestamp, session_id, frame_id, bit, target_length,
actual_write_length, observed_length, crc_status, error_reason
```

## 4 为 1D-CNN 准备数据

后续建议：

1. 读取 `sender.jsonl` / `receiver.jsonl`；
2. 按 session_id 分组；
3. 以连续 64/128 个事件为窗口；
4. 提取特征：
   - direction；
   - block length；
   - inter-event gap；
   - cumulative bytes；
5. 将 Normal（`normal/` 数据集）作为负样本，Baseline-Stego 作为正样本；
6. 训练传统分类器与 1D-CNN。

## 5 注意事项

- 本实验只调制 application-layer write length；
- 不要用抓包层 packet length 直接替代应用层块长；
- 如果出现 `length_out_of_range`，先调大 `stego.block_gap_ms` 再重跑；
- 第一版不做 FEC/重传，错误只记录，不修复。

## 6 本次实测结果

完整测试：

```text
20/20 unit tests: OK
```

端到端 Demo：

```json
{
  "passed": true,
  "secret_size": 64,
  "recovered_size": 64,
  "plaintext_match": true,
  "cover_match": true,
  "total_bits": 840,
  "bit_error_count": 0,
  "ber": 0.0,
  "frame_count": 1,
  "received_frame_count": 1,
  "frame_error_count": 0,
  "frame_error_rate": 0.0,
  "crc_failure_count": 0,
  "ciphertext_bytes": 94,
  "cover_bytes": 825600,
  "duration_ms": 9752.239511999505,
  "throughput_secret_Bps": 6.562595178394881
}
```

输出文件：

- `out/experiment_summary.json`
- `out/sender_result.json`
- `out/receiver_result.json`
- `out/server_result.json`
- `out/recovered_secret.txt`
- `logs/sender.jsonl`
- `logs/receiver.jsonl`
- `logs/errors.jsonl`

## 7 数据生成 smoke test

```text
normal sessions: 3
stego sessions: 3
success: 6/6

raw:       dataset/raw/{normal,stego}/<session_id>/
processed: dataset/processed/windows.npz
splits:    dataset/splits/{train,val,test}.npz

X.shape = [18, 4, 128]
y.shape = [18]
normal windows = 9
stego windows = 9
train/val/test sessions = 2 / 2 / 2
session overlap = none
NaN/Inf = false

BER = 0.0
frame_error_rate = 0.0
crc_failure_count = 0
```
