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

## 2026-09-21 – cWGAN-GP module

- Added `src/cWGAN-GP/`: a conditional WGAN-GP whose generator emits only the
  application-layer length channel `[B, 128]`, projected onto two
  non-overlapping length bands, plus `README_cWGAN.md`.
- The module documents a hard requirement of at least **1000 training
  windows**. With the current 114 training windows both critic and generator
  losses diverge monotonically; no checkpoint and no generated data were
  produced.

Source: Git commit `6840169` ("Add cWGAN-GP module and README"), which is also
the first entry in this changelog taken directly from Git history rather than
from file timestamps.

## 2026-09-26 – dataset scale-up to 466 sessions

No protocol, modulation, encryption or Docker definition was changed.

- Collected 210 new Normal and 210 new Stego sessions on the Ubuntu6.21 VM
  with the same parameters as the original 23 + 23 (`seed=42`,
  `secret_size=16`, `block_gap_ms=20`, `window_size=128`).
- Eight Stego sessions failed with the already-documented
  `length_out_of_range` (receiver-side coalescing of two proxy writes,
  observed 1600/2000 B). They were moved to the VM's
  `protocol_stego/raw_failed/stego/` instead of being deleted, and fresh
  sessions were collected until all 233 Stego sessions succeeded.
- Rebuilt the processed dataset and splits:

  ```text
  sessions : 466 (233 Normal + 233 Stego, all successful)
  windows  : 1398 (699 / 699), X = [1398, 4, 128]
  splits   : train 374 sessions / 1122 windows
             val    46 sessions /  138 windows
             test   46 sessions /  138 windows
  ```

- Regenerated `DATA_QUALITY_REPORT.md` (verdict `READY_FOR_CNN`),
  `BASELINE_ANALYSIS.md`, `stats.json`, `build_summary.json` and the plots.
  BER, frame error rate and CRC failure rate are all 0; no session overlap, no
  duplicate sample, no NaN/Inf.
- Rebuilt `raw/run_summary.json` as an aggregate of every session's
  `metadata.json`, because the two parallel collection workers each overwrite
  that file with their own run.
- Recorded the whole procedure, the quarantined session ids and the remaining
  limitations in `docs/experiments/dataset-scaleup-20260926.md`.

Effect on the cWGAN-GP module: its 1000-training-window requirement is now
met (1122 training windows). It is still not trainable because of the data
interface mismatch documented in `docs/experiments/cwgan-results.md`.

## 2026-09-26 – consolidation and status review

This pass did not change any algorithm, dataset or Docker definition.

- Cloned the GitHub repository into the OS projects directory as
  `projects/tcp-steganography`.
- Read-only verified the Ubuntu6.21 VM project directory
  (`/home/urruna/docker/tcp-lab`, 1162 files): no file newer than 2026-09-20,
  no `1dcnn` or `cWGAN-GP` directory, and no result that is missing from the
  repository.
- Compared the local working copy (`D:\C\work_DC`, commit `01f8304`): the only
  extra files are four intentionally ignored artifacts (two 19.7 MB
  `data_quality_report.json` files excluded by `.gitignore`, and two `*.log`
  files).
- Added `PROJECT_REVIEW.md`: consolidated Chinese overview of the project,
  the three sources, and the prioritized next steps.
- Added `docs/experiments/cwgan-results.md`: what the cWGAN-GP module actually
  contains, the data-volume blocker, and the verified data-interface
  inconsistencies.
- Corrected the cGAN status from `Design` to `Partial` in `PROJECT_STATUS.md`,
  `README.md`, `docs/architecture/workflow.md` and
  `docs/architecture/project-overview.md`, which previously still listed the
  1D-CNN as not implemented.
