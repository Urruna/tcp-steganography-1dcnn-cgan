# Migration Notes

This file records differences found while organizing the repository.

## Git History

- Windows `D:\C\work_DC\.git`: not present.
- Ubuntu `/home/urruna/docker/tcp-lab`: no `.git` directory.

No commit history was available for comparison.

## Compared Directories

The following directories existed in both Windows and Ubuntu:

```text
crypto/
normal/
newtry97/
protocol_stego/
```

A SHA256 manifest comparison was performed (Ubuntu `sha256sum`, Windows
Python `hashlib`).

## Files Only in Ubuntu

- `crypto/out/crypto_selftest.json`
- `crypto/out/*.enc` demo ciphertexts
- `newtry97/__pycache__/*` (cache, not to be committed)
- `newtry97/logs/docker917/proxy_a_events.csv`
- `newtry97/logs/docker917/proxy_b_events.csv`
- `newtry97/logs/docker917/recovered.txt`
- `normal/files/manifest.json`
- `normal/files/report_small.txt`
- `normal/files/report_medium.txt`
- `normal/files/report_large.bin`
- `normal/logs/client_events.csv`
- `normal/logs/dataset_summary.json`
- `normal/logs/proxy_a_events.csv`
- `normal/logs/proxy_b_events.csv`
- `normal/logs/server_events.csv`
- `protocol_stego/out/client_result.json`
- `protocol_stego/out/demo_config.yaml`
- `protocol_stego/out/demo_key.bin`
- `protocol_stego/out/server_result.json`

Actions:

- Docker917 logs copied to `src/newtry97/logs/docker917/`.
- Normal files copied to `datasets/normal_v1/files/`.
- Normal CSV data copied to `datasets/normal_v1/logs/` (content identical,
  verified by SHA256).
- Crypto self-test artifacts copied to `docs/experiments/crypto-selftest/`;
  `demo.key` was not copied into the repository.

## Files Only in Windows

- `normal/client_events.csv`
- `normal/dataset_summary.json`
- `normal/proxy_a_events.csv`
- `normal/proxy_b_events.csv`
- `normal/server_events.csv`
- `normal/normalTraffic.zip`
- `protocol_stego/dataset/processed/.gitkeep`
- `protocol_stego/dataset/raw/normal/.gitkeep`
- `protocol_stego/dataset/raw/stego/.gitkeep`
- `protocol_stego/dataset/splits/.gitkeep`
- `protocol_stego/docs/plots/.gitkeep`
- `protocol_stego/scripts/build_dataset_release.py`

Notes:

- The `normal/*.csv` files in Windows are byte-identical to the
  `normal/logs/*.csv` files in Ubuntu (SHA256 equality confirmed).
- `build_dataset_release.py` is a Windows-side tool not present in Ubuntu;
  copied to `tools/build_release/`.
- `normalTraffic.zip` content/use was not confirmed; it is preserved but
  should be reviewed before committing to a release.

## Content Differences for Shared Paths

The following paths existed in both locations but had different hashes:

```text
protocol_stego/data/secret.txt
protocol_stego/logs/receiver.jsonl
protocol_stego/logs/sender.jsonl
protocol_stego/out/experiment_summary.json
protocol_stego/out/receiver_result.json
protocol_stego/out/recovered_secret.txt
protocol_stego/out/sender_result.json
```

These differences are caused by different demo runs (different random
secret/key or later re-runs). No file was overwritten by this migration;
both originals remain in their respective environments.

## Path Decisions

- `src/crypto` and `src/protocol_stego` remain siblings so
  `core/crypto_adapter.py` can still resolve `../crypto/crypto.py`.
- The working dataset was moved from `src/protocol_stego/dataset` to
  `datasets/protocol_stego` so code and data are clearly separated.
  The container mount target remains `/work/protocol_stego/dataset`, so
  scripts inside the container keep the same runtime paths.
- `releases/dataset_release_v1/` is a delivery artifact, not runtime source.
- Historical and protocol datasets remain separated.
- The Ubuntu runtime tree `/home/urruna/docker/tcp-lab` was intentionally
  left in place. It was used as the source for Ubuntu-only files, which were
  copied into this repository. No Ubuntu experiment data was deleted or
  moved.
- An empty root directory `protocol_stego/` may remain after the move because
  a Windows process temporarily held it open; it contains no files and is
  not tracked by Git.
- `normalTraffic.zip` was removed at the user's request; it was confirmed
  unused.
- The large `data_quality_report.json` files are intentionally not carried in
  the Git repository; they remain on disk and in the release archive.
