# Dataset Overview

## 1. Historical Docker Normal Dataset

- Source: Ubuntu `/home/urruna/docker/tcp-lab/logs/`
- Repository copy: `datasets/historical/docker_chain_smoke/`
- Type: early Docker TCP chain normal traffic
- Payload: `hello network` (13 bytes)
- Sessions: 2 proxy-side sessions (Proxy-A + Proxy-B)
- Events: 4 (forward/reverse)
- Format: CSV
- No modulation, no secret data
- No pcap
- Known limitation: very small, early smoke data

## 2. Historical `baseline_lenmix_v1`

- Repository copy: `datasets/historical/baseline_lenmix_v1/`
- Type: earlier normal-traffic baseline
- 1 experiment/session
- 256 client events (all passed)
- 512 Proxy-A events (256 forward + 256 reverse)
- 512 Proxy-B events (256 forward + 256 reverse)
- lengths: 64, 128, 256, 512, 1024 bytes cycling
- no modulation, no pcap
- Source environment: earlier Ubuntu 20.04 VMware native multi-process
  experiment, not the current protocol_stego Docker control group

## 3. `normal_v1` File-Transfer Dataset

- Repository copy: `datasets/normal_v1/`
- Source code: `src/normal_file_transfer/`
- Type: normal Docker file download through proxy chain
- 8 downloads, all SHA-256 verified
- client events: 8
- Proxy-A events: 771 (8 forward, 763 reverse)
- Proxy-B events: 773 (8 forward, 765 reverse)
- server events: 8
- total bytes: 3,082,890
- files: 64 KiB / 256 KiB / 1 MiB
- no 800/1200 modulation

## 4. protocol_stego Dataset (current main dataset)

- Working location: `datasets/protocol_stego/`
- Released copy: `releases/dataset_release_v1/protocol_stego/`
- Raw normal sessions: 233 (all successful)
- Raw stego sessions: 233 (all successful)
- Total events: 210165
- Processed windows: 1398
- Normal windows: 699
- Stego windows: 699

The dataset started at 23 + 23 sessions / 138 windows and was scaled up on
2026-09-26; see `docs/experiments/dataset-scaleup-20260926.md`.

Processed shape:

```text
X.shape = [1398, 4, 128]
y.shape = [1398]
```

Labels:

```text
0 = Normal
1 = Stego (800/1200 application-layer length modulation)
```

Session-level split:

```text
train: 374 sessions, 1122 windows
val:    46 sessions,  138 windows
test:   46 sessions,  138 windows
```

Validation:

- no train/val/test session overlap;
- no duplicate sample;
- no NaN / Inf;
- BER = 0;
- frame error rate = 0;
- CRC failure rate = 0.

Length distribution (documented limitation): Normal events are all exactly
1024 B, Stego events are exactly 800 B or 1200 B. The `direction` channel is
constant 1 for both classes. A detector trained on this pair therefore learns
the 800/1200 modulation signature rather than general covert-channel
detectability.

## 5. Not Yet Generated

- pcap datasets;
- GAN-Stego dataset;
- datasets under different RTT / bandwidth / loss conditions.
