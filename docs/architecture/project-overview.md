# Project Overview

## Research Goal

Study TCP traffic feature modulation in an authorized proxy-forwarding
environment, together with reliable secret delivery and detectability
evaluation.

The long-term plan in `docs/planning/new_727.md` includes:

- Normal traffic;
- Baseline-Stego traffic;
- GAN-Stego traffic;
- 1D-CNN detector;
- cGAN feature optimizer.

## Two Engineering Lines

### Communication line

```text
Client → Proxy-A → Proxy-B → Server
```

Goal: normal business traffic must keep working while Proxy-A modulates only
allowed application-layer write behavior.

### Analysis line

```text
logs / datasets
        ↓
fixed event windows
        ↓
rule-based / traditional ML baseline
        ↓
1D-CNN (planned)
        ↓
cGAN / GAN-Stego (planned)
```

## Implemented Reality

Implemented now:

- Docker TCP chains;
- AES-256-GCM;
- frame + CRC + bitstream + reassembly;
- 800/1200 application-layer write-length stego;
- raw dataset and fixed-window processed dataset;
- rule-based and Logistic Regression baselines.

Not implemented now:

- 1D-CNN;
- cGAN;
- GAN-Stego;
- FEC / retransmission;
- pcap-based feature extraction.

## Evidence

- `PROJECT_AUDIT.md`
- `PROJECT_STATUS.md`
- `src/`
- `src/protocol_stego/docs/`
- `releases/dataset_release_v1/`
