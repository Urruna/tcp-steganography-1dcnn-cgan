# DATA QUALITY REPORT

Conclusion: **READY_FOR_CNN**

## 1 数据集概况

| session_id | mode | label | success | events | bytes | duration_s | sender_lines | receiver_lines |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| normal_000001 | normal | 0 | True | 446 | 456000 | 9.458515 | 448 | 447 |
| normal_000002 | normal | 0 | True | 446 | 456000 | 9.408733 | 448 | 447 |
| normal_000003 | normal | 0 | True | 446 | 456000 | 9.475592 | 448 | 447 |
| normal_000004 | normal | 0 | True | 446 | 456000 | 9.370877 | 448 | 447 |
| normal_000005 | normal | 0 | True | 446 | 456000 | 9.441139 | 448 | 447 |
| normal_000006 | normal | 0 | True | 446 | 456000 | 9.376096 | 448 | 447 |
| normal_000007 | normal | 0 | True | 446 | 456000 | 9.408436 | 448 | 447 |
| normal_000008 | normal | 0 | True | 446 | 456000 | 9.376733 | 448 | 447 |
| normal_000009 | normal | 0 | True | 446 | 456000 | 9.384712 | 448 | 447 |
| normal_000010 | normal | 0 | True | 446 | 456000 | 9.441550 | 448 | 447 |
| normal_000011 | normal | 0 | True | 446 | 456000 | 9.451478 | 448 | 447 |
| normal_000012 | normal | 0 | True | 446 | 456000 | 9.374403 | 448 | 447 |
| normal_000013 | normal | 0 | True | 446 | 456000 | 9.378999 | 448 | 447 |
| normal_000014 | normal | 0 | True | 446 | 456000 | 9.361864 | 448 | 447 |
| normal_000015 | normal | 0 | True | 446 | 456000 | 9.378911 | 448 | 447 |
| normal_000016 | normal | 0 | True | 446 | 456000 | 9.316497 | 448 | 447 |
| normal_000017 | normal | 0 | True | 446 | 456000 | 9.325646 | 448 | 447 |
| normal_000018 | normal | 0 | True | 446 | 456000 | 9.411425 | 448 | 447 |
| normal_000019 | normal | 0 | True | 446 | 456000 | 9.403962 | 448 | 447 |
| normal_000020 | normal | 0 | True | 446 | 456000 | 9.402010 | 448 | 447 |
| normal_000021 | normal | 0 | True | 446 | 456000 | 9.377278 | 448 | 447 |
| normal_000022 | normal | 0 | True | 446 | 456000 | 9.433006 | 448 | 447 |
| normal_000023 | normal | 0 | True | 446 | 456000 | 9.410704 | 448 | 447 |
| stego_000001 | stego | 1 | True | 456 | 448800 | 9.404806 | 458 | 459 |
| stego_000002 | stego | 1 | True | 456 | 447200 | 9.443698 | 458 | 459 |
| stego_000003 | stego | 1 | True | 456 | 452000 | 9.418697 | 458 | 459 |
| stego_000004 | stego | 1 | True | 456 | 447200 | 9.448353 | 458 | 459 |
| stego_000005 | stego | 1 | True | 456 | 452800 | 9.410093 | 458 | 459 |
| stego_000006 | stego | 1 | True | 456 | 444800 | 9.431521 | 458 | 459 |
| stego_000007 | stego | 1 | True | 456 | 442400 | 9.422089 | 458 | 459 |
| stego_000008 | stego | 1 | True | 456 | 451200 | 9.438287 | 458 | 459 |
| stego_000009 | stego | 1 | True | 456 | 448000 | 9.406673 | 458 | 459 |
| stego_000010 | stego | 1 | True | 456 | 446400 | 9.449828 | 458 | 459 |
| stego_000011 | stego | 1 | True | 456 | 449600 | 9.426277 | 458 | 459 |
| stego_000012 | stego | 1 | True | 456 | 448000 | 9.395873 | 458 | 459 |
| stego_000013 | stego | 1 | True | 456 | 450400 | 9.424576 | 458 | 459 |
| stego_000014 | stego | 1 | True | 456 | 456000 | 9.404814 | 458 | 459 |
| stego_000015 | stego | 1 | True | 456 | 444800 | 9.442413 | 458 | 459 |
| stego_000016 | stego | 1 | True | 456 | 448000 | 9.356607 | 458 | 459 |
| stego_000017 | stego | 1 | True | 456 | 449600 | 9.409307 | 458 | 459 |
| stego_000018 | stego | 1 | True | 456 | 447200 | 9.419459 | 458 | 459 |
| stego_000019 | stego | 1 | True | 456 | 448000 | 9.450106 | 458 | 459 |
| stego_000020 | stego | 1 | True | 456 | 452000 | 9.423316 | 458 | 459 |
| stego_000021 | stego | 1 | True | 456 | 444800 | 9.460612 | 458 | 459 |
| stego_000022 | stego | 1 | True | 456 | 453600 | 9.423437 | 458 | 459 |
| stego_000023 | stego | 1 | True | 456 | 451200 | 9.385838 | 458 | 459 |

## 2 Session 统计

| mode | sessions | success | failed |
| --- | --- | --- | --- |
| normal | 23 | 23 | 0 |
| stego | 23 | 23 | 0 |

## 3 Normal / Stego 对比

### duration_s

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 9.316497 | 9.475592 | 9.398633 | 9.402010 | 0.038939 |
| stego | 9.356607 | 9.460612 | 9.421595 | 9.423316 | 0.023248 |

### event_count

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 446.000000 | 446.000000 | 446.000000 | 446.000000 | 0.000000 |
| stego | 456.000000 | 456.000000 | 456.000000 | 456.000000 | 0.000000 |

### total_bytes

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 456000.000000 | 456000.000000 | 456000.000000 | 456000.000000 | 0.000000 |
| stego | 442400.000000 | 456000.000000 | 448869.565217 | 448000.000000 | 3173.043359 |

### avg_event_length

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 1022.421525 | 1022.421525 | 1022.421525 | 1022.421525 | 0.000000 |
| stego | 970.175439 | 1000.000000 | 984.363082 | 982.456140 | 6.958428 |

### inter_arrival_mean

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 0.020880 | 0.021236 | 0.021064 | 0.021071 | 0.000087 |
| stego | 0.020510 | 0.020732 | 0.020651 | 0.020651 | 0.000051 |

### Comparability ratios

| metric | normal_mean | stego_mean | max/min ratio |
| --- | --- | --- | --- |
| duration_s | 9.398633 | 9.421595 | 1.002443 |
| event_count | 446.000000 | 456.000000 | 1.022422 |
| total_bytes | 456000.000000 | 448869.565217 | 1.015885 |

## 4 Stego 调制验证

| item | value |
| --- | --- |
| target counts | {800: 5654, 1200: 4834} |
| bit counts | {0: 5654, 1: 4834} |
| actual_write_length counts | {800: 5654, 1200: 4834} |
| observed_length counts | {800: 5654, 1200: 4834} |
| observed outside 800/1200 | 0 |
| actual == target ratio | 1.000000 |
| actual == observed ratio | 1.000000 |
| BER | 0.000000 |
| frame error rate | 0.000000 |
| CRC failure rate | 0.000000 |

## 5 数据泄漏检查

| check | result |
| --- | --- |
| train ∩ val | [] |
| train ∩ test | [] |
| val ∩ test | [] |
| sessions in multiple splits | [] |
| duplicate sample count | 0 |

## 6 X / y 检查

| item | value |
| --- | --- |
| X.shape | [138, 4, 128] |
| y.shape | [138] |
| X.dtype | float32 |
| y.dtype | int64 |
| features | ['direction', 'length', 'inter_arrival_time', 'cumulative_bytes'] |
| window_size | 128 |
| NaN count | 0 |
| Inf count | 0 |
| class distribution | {'normal': 69, 'stego': 69} |

## 7 特征统计

### direction

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| stego | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |

### length

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 1024.000000 | 1024.000000 | 1024.000000 | 1024.000000 | 0.000000 |
| stego | 800.000000 | 1200.000000 | 981.748188 | 800.000000 | 199.165437 |

### inter_arrival_time

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 0.000000 | 0.029825 | 0.021005 | 0.021049 | 0.001131 |
| stego | 0.000000 | 0.025833 | 0.020593 | 0.020583 | 0.001906 |

### cumulative_bytes

| mode | min | max | mean | median | std |
| --- | --- | --- | --- | --- | --- |
| normal | 1024.000000 | 393216.000000 | 197120.000000 | 197120.000000 | 113511.296824 |
| stego | 800.000000 | 384400.000000 | 186397.010870 | 185200.000000 | 109262.222437 |

## 8 异常数据与观察

- preferred normal session count >=50 not reached (current 23)
- preferred stego session count >=50 not reached (current 23)

## 9 数据质量问题

Normal length stats: {'count': 10258, 'min': 320.0, 'max': 1024.0, 'mean': 1022.4215246636771, 'median': 1024.0, 'std': 33.29797369786817}

- normal sender contains modulation fields: 0
- normal exact 800 events: 0
- normal exact 1200 events: 0

## 10 是否可以进入 1D-CNN

结论：**READY_FOR_CNN**

## 11 下一步建议

- 当前规模与可比性满足首轮 1D-CNN 基线实验。
- CNN 结果应解释为对 800/1200 modulation 的检测，不能直接推广为一般隐写可检测性。
- 建议继续增加 Normal 业务多样性（不同文件大小、双向 HTTP 业务）。
- 训练 CNN 时同时报告 rule-based 与传统 ML baseline。
- 生成的多份统计图见 docs/plots/。

