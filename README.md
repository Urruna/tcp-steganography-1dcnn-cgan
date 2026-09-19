# Authorized TCP Steganography Lab

## Project Overview

This repository collects the current results of a closed, authorized
laboratory project that studies:

- normal TCP traffic forwarded through two proxies;
- secret data transport over the same proxy chain;
- application-layer traffic feature modulation;
- dataset construction for later 1D-CNN / cGAN detection experiments.

The project is **not** a production system and must only be used in an
authorized experimental environment.

## Research Goal

The long-term goal is to study the trade-off between:

```text
secret payload capacity
        ↔
reliable delivery (BER / FER)
        ↔
network performance (latency / throughput)
        ↔
detectability (1D-CNN / cGAN experiments)
```

Encryption, steganography, and GAN-based feature optimization are three
different layers and must not be confused:

| Layer | Solves |
| --- | --- |
| AES-256-GCM | content confidentiality |
| application-layer length modulation | hiding the secret transmission |
| cGAN (planned) | making modulated traffic look closer to normal traffic |

## Architecture

```text
Client → Proxy-A → Proxy-B → Server
              ↘       ↙
           logs / datasets
                  ↓
             Analysis
```

Current implemented stacks:

1. `src/tcp_lab/` – original Docker 4-container TCP echo chain.
2. `src/normal_file_transfer/` – Docker file-download chain used for normal
   traffic.
3. `src/crypto/` – AES-256-GCM module.
4. `src/newtry97/` – v0.2 frame protocol and write-splitting demo.
5. `src/protocol_stego/` – current protocol, 800/1200 stego, dataset and
   experiment scripts.

## Network Topology

### Base Docker chain

```text
client → proxy_a:9001 → proxy_b:9002 → server:9003
```

Networks:

```text
client_net, backbone_net, server_net   (internal)
```

### Current protocol_stego experiment

```text
client → proxy_a:9101 → proxy_b:9102 → server:9103
```

Important: `src/protocol_stego/compose.yaml` currently starts a single
`tests` container. The four-node flow is simulated in-process by
`examples/demo_secret_transfer.py` and `scripts/session_runner.py`.

See `docs/architecture/network-topology.md`.

## Current Status

See `PROJECT_STATUS.md` for the complete table.

Short version:

- Docker base chain: Completed
- Normal traffic collection: Partial
- AES-256-GCM: Completed
- Frame protocol / CRC / bitstream / reassembly: Completed
- 800/1200 application-layer stego: Completed
- Dataset (raw/processed/splits): Partial (23 Normal + 23 Stego sessions)
- Rule-based + Logistic Regression baseline: Completed
- 1D-CNN: Not Implemented
- cGAN / GAN-Stego: Design only

## Repository Structure

```text
.
├── README.md
├── PROJECT_STATUS.md
├── PROJECT_AUDIT.md
├── REPOSITORY_PLAN.md
├── CHANGELOG.md
├── TEAM_GUIDE.md
├── LICENSE_OR_USAGE.md
├── docs/
│   ├── architecture/
│   ├── crypto/
│   ├── protocol/
│   ├── steganography/
│   ├── dataset/
│   ├── experiments/
│   ├── planning/
│   └── audit/
├── src/
│   ├── tcp_lab/
│   ├── normal_file_transfer/
│   ├── crypto/
│   ├── newtry97/
│   └── protocol_stego/
├── datasets/
│   ├── historical/
│   ├── normal_v1/
│   └── protocol_stego/
└── releases/
    ├── dataset_release_v1/
    └── dataset_release_v1.zip
```

## Quick Start

### 1. Base Docker TCP chain

```bash
cd src/tcp_lab
docker compose up
```

Expected client output:

```text
[client] received: hello network
[client] PASS: returned payload matches sent payload
```

### 2. Normal file-transfer chain

```bash
cd src/normal_file_transfer
docker compose up --abort-on-container-exit --exit-code-from client
```

### 3. Crypto self-test

```bash
cd src/crypto
docker compose up --build
```

### 4. protocol_stego tests and demo

```bash
cd src/protocol_stego
docker compose build
docker compose run --rm tests python -m unittest discover -s tests -v
docker compose run --rm tests python examples/demo_secret_transfer.py
```

### 5. Re-run the dataset pipeline

```bash
cd src/protocol_stego
docker compose run --rm tests python scripts/run_experiment.py \
  --mode both --normal 20 --stego 20 --seed 42 \
  --secret-size 16 --block-gap-ms 20 --window-size 128
docker compose run --rm tests python scripts/dataset_builder.py --window-size 128
docker compose run --rm tests python scripts/split_dataset.py
docker compose run --rm tests python scripts/dataset_stats.py
docker compose run --rm tests python scripts/data_quality_report.py
docker compose run --rm tests python scripts/baseline_analysis.py
```

## Dataset

Main machine-learning dataset:

```text
src/protocol_stego/dataset/processed/windows.npz
releases/dataset_release_v1/protocol_stego/processed/X.npy
releases/dataset_release_v1/protocol_stego/processed/y.npy
```

Current shape:

```text
X.shape = [138, 4, 128]
y.shape = [138]
labels: 0 = Normal, 1 = Stego
features:
  0 direction
  1 length
  2 inter_arrival_time
  3 cumulative_bytes
```

Current session summary:

```text
Normal sessions: 23, events: 10258
Stego sessions:  23, events: 10488
windows: 138 (69 Normal / 69 Stego)
```

Do not re-split windows randomly: use the existing session-level split in
`src/protocol_stego/dataset/splits/`.

See `docs/dataset/dataset-overview.md`.

## Encryption

Implementation:

```text
src/crypto/crypto.py
src/crypto/crypto_tool.py
```

Algorithm: AES-256-GCM.

Format:

```text
Header(1B) + Flags(1B) + Nonce(12B) + Ciphertext + Tag(16B)
```

Fixed overhead: 30 bytes.

See `docs/crypto/aes-256-gcm.md`.

## Protocol

Implemented protocol fields:

```text
Preamble(32 bit) | Version(8 bit field, version=1)
| Frame ID(16 bit) | Payload Length(16 bit)
| Payload | CRC-16/XMODEM(16 bit)
```

Preamble: `0x6E9797A1`.

Implementations:

```text
src/newtry97/framing.py
src/protocol_stego/core/framing.py
```

See `docs/protocol/protocol-design.md`.

## Steganography

Current baseline strategy:

```text
bit 0 → ~800 B application-layer write length
bit 1 → ~1200 B application-layer write length
```

This modulates application-layer write length, **not** TCP packet length.

Implementation:

```text
src/protocol_stego/core/modulation.py
src/protocol_stego/proxy/sender_stego.py
src/protocol_stego/proxy/receiver_stego.py
```

See `docs/steganography/basic-stego.md`.

## Experiments

Existing experiment results:

- `docs/experiments/data-quality-report.md`
- `docs/experiments/baseline-analysis.md`
- `docs/experiments/newtry97-v0.2.md`

Current dataset quality verdict: `READY_FOR_CNN`.

The current Normal data is mostly 1024 B writes, while Stego is 800/1200 B.
Therefore a CNN run mainly tests detection of the 800/1200 modulation
signature, not general steganography detection.

## Team Development Notes

Read `TEAM_GUIDE.md` before changing anything.

Do not modify without explicit agreement:

- AES-256-GCM implementation;
- existing protocol field layout;
- Docker network topology;
- existing raw datasets;
- 800/1200 baseline modulation.

New experiments should be added under `docs/experiments/` and
`src/protocol_stego/` (or a new clearly named subproject), not by rewriting
the current results.
