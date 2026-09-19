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
- Raw normal sessions: 23
- Raw stego sessions: 23
- Normal events: 10258
- Stego events: 10488
- Processed windows: 138
- Normal windows: 69
- Stego windows: 69

Processed shape:

```text
X.shape = [138, 4, 128]
y.shape = [138]
```

Labels:

```text
0 = Normal
1 = Stego (800/1200 application-layer length modulation)
```

Session-level split:

```text
train: 38 sessions, 114 windows
val:    4 sessions, 12 windows
test:   4 sessions, 12 windows
```

Validation:

- no train/val/test session overlap;
- no duplicate sample;
- no NaN / Inf;
- BER = 0;
- frame error rate = 0;
- CRC failure rate = 0.

## 5. Not Yet Generated

- pcap datasets;
- GAN-Stego dataset;
- datasets under different RTT / bandwidth / loss conditions.
