# 数据集完整性报告

校验结果：**通过**

## protocol_stego

- session 数：{'normal': 23, 'stego': 23}
- 事件数：{'normal': 10258, 'stego': 10488}
- metadata 完整数：46
- 文件数：527
- empty files: ['protocol_stego\\raw\\normal\\normal_000001\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000002\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000003\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000004\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000005\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000006\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000007\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000008\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000009\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000010\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000011\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000012\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000013\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000014\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000015\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000016\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000017\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000018\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000019\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000020\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000021\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000022\\errors.jsonl', 'protocol_stego\\raw\\normal\\normal_000023\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000001\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000002\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000003\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000004\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000005\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000006\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000007\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000008\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000009\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000010\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000011\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000012\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000013\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000014\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000015\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000016\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000017\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000018\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000019\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000020\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000021\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000022\\errors.jsonl', 'protocol_stego\\raw\\stego\\stego_000023\\errors.jsonl']
- 说明：当 session 没有任何错误时，`errors.jsonl` 为空是预期行为
- 非错误类空文件：[]
- JSONL 解析错误：[]
- X.shape：[138, 4, 128]
- y.shape：[138]
- X dtype：<f4
- y dtype：<i8
- 标签分布：{'normal': 69, 'stego': 69}
- 划分重叠：{'train_val': [], 'train_test': [], 'val_test': []}
- 重复样本数：0
- NaN 数：0
- Inf 数：0

## historical_normal

- baseline_lenmix_v1 summary: {"client_events.csv": {"rows": 256, "columns": ["timestamp", "experiment_id", "event_index", "expected_byte_length", "status"], "sessions": 1, "directions": {"forward": 0, "reverse": 0}, "lengths": [64, 128, 256, 512, 1024], "statuses": {"passed": 256}}, "proxy_a_events.csv": {"rows": 512, "columns": ["timestamp", "proxy_name", "experiment_id", "session_id", "direction", "event_index", "byte_length", "inter_event_gap_ms"], "sessions": 1, "directions": {"forward": 256, "reverse": 256}, "lengths": [64, 128, 256, 512, 1024], "statuses": {}}, "proxy_b_events.csv": {"rows": 512, "columns": ["timestamp", "proxy_name", "experiment_id", "session_id", "direction", "event_index", "byte_length", "inter_event_gap_ms"], "sessions": 1, "directions": {"forward": 256, "reverse": 256}, "lengths": [64, 128, 256, 512, 1024], "statuses": {}}}

## checksums

见 `checksums/SHA256SUMS.txt`。

