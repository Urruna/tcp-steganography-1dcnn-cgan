# CHANGELOG

## Evidence Note

No Git repository or commit history was present when this file was created
(`D:\C\work_DC\.git` did not exist; Ubuntu `tcp-lab` had no `.git`).

Therefore this changelog is based on:

- project Markdown documents;
- file modification times;
- actual execution records and reports.

Dates below are evidence-based, not commit dates.

## 2026-07-28

- Added `new_727.md` / `new_727.pdf`: project research plan and architecture.
- Introduced the target workflow: Normal → Baseline-Stego → GAN-Stego,
  1D-CNN and cGAN.

Source: `docs/planning/new_727.md`, file timestamps.

## 2026-07-29

- Added `Docker_m1.md`: early Docker/TCP lab notes.
- Added early `baseline_lenmix_v1` data:
  256 client events, 512 Proxy-A events, 512 Proxy-B events.
- Added early Docker Normal smoke data:
  13-byte `hello network`, 2 proxy-side sessions, 4 events.

Source: `docs/planning/docker_m1.md`,
`datasets/historical/baseline_lenmix_v1/`,
`datasets/historical/docker_chain_smoke/`.

## 2026-09-07 to 2026-09-08

- Added `newtry97` v0.1/v0.2:
  - line-based cover business;
  - Preamble/Version/Frame ID/Length/CRC;
  - sliding-window Preamble search;
  - write-splitting stego;
  - E2E demo and logs.
- Added containerized `newtry97` chain and `work917.md`.

Source: `docs/experiments/newtry97-v0.2.md`,
`docs/planning/work917.md`, `src/newtry97/`.

## 2026-09-17

- Configured Docker environment on Ubuntu6.21:
  Compose v2, buildx, registry mirrors, daemon DNS and log rotation.
- Added `normal` file-transfer chain and `normal_v1` dataset:
  8 downloads, client/proxy/server CSV logs, 3,082,890 bytes.
- Added `data.md` experiment record.

Source: `src/normal_file_transfer/data.md`,
`datasets/normal_v1/`, `docs/planning/work917.md`.

## 2026-09-18 to 2026-09-19

- Added `crypto` module:
  AES-256-GCM, PBKDF2 key derivation, fixed 30 B overhead, self-test.
- Added `protocol_stego`:
  frame encode/decode, CRC, bitstream, reassembly, 800/1200 modulation,
  Proxy-A/B, JSONL logs, tests and E2E demo.
- Expanded protocol dataset to 23 Normal + 23 Stego sessions.
- Built processed dataset:
  `X=[138,4,128]`, `y=[138]`, session-level splits.
- Added data quality report and rule-based / Logistic Regression baseline.
- Built `dataset_release_v1` and SHA256 checksums.

Source: `docs/experiments/`,
`src/protocol_stego/docs/`, `releases/dataset_release_v1/`.

## Repository Organization

- Reorganized source into `src/`.
- Reorganized documentation into `docs/`.
- Reorganized datasets into `datasets/` and `releases/`.
- Added root README / status / team guide / migration notes.

No algorithm, AES, protocol, Docker network, or dataset content was changed
by this organization step. See `docs/migration-notes.md`.

## 2026-09-19 – 1D-CNN module

- Added the independent 1D-CNN delivery under `src/1dcnn/`:
  two-layer 1D-CNN, training and evaluation scripts, frozen inference
  interface, Logistic Regression and rule baselines, trained checkpoint,
  result files and plots.
- The module uses a separate 168-window dataset:
  `train=117 (32 Normal / 85 Stego)`,
  `val=26 (6/20)`,
  `test=25 (10/15)`.
- Recorded software tests: 6 tests OK.
- Reported test comparison:
  CNN accuracy 0.9200 / F1 0.9375 / ROC-AUC 0.9867;
  Logistic Regression accuracy 0.8800 / F1 0.8889 / ROC-AUC 1.0000;
  rule baseline accuracy 0.8800 / F1 0.8889.
- The dataset has no session index; session isolation is **not verified**.
  The 168-window arrays have no exact overlap with the 138-window
  `datasets/protocol_stego` array, so the two must not be silently merged.

Source: `src/1dcnn/README.md`, `src/1dcnn/results/result_report.md`,
`src/1dcnn/results/software_tests.txt`.
