# Dataset Scale-Up (2026-09-26)

## Purpose

Raise `datasets/protocol_stego/` to the volume `src/cWGAN-GP/` requires
(at least 1000 training windows) **without changing** the protocol, the
800/1200 modulation, the session parameters or the Docker definitions.

The previous dataset had 23 Normal + 23 Stego sessions and 138 windows.

## Environment

| Item | Value |
| --- | --- |
| Host | Ubuntu6.21 VMware guest, user `urruna` |
| Project path | `/home/urruna/docker/tcp-lab/protocol_stego` |
| Collection runtime | system Python 3.8.10, numpy 1.24.4, PyYAML 5.3.1 |
| Pipeline runtime | project image `protocol-stego:1` via Docker Compose 2.27.1 |

## Commands

Collection. Two workers ran in parallel, one per mode, so that the
`_next_index()` scan cannot hand the same session index to two processes:

```bash
python3 -m scripts.run_experiment --mode normal --normal 210 \
  --seed 42 --secret-size 16 --block-gap-ms 20 --window-size 128

python3 -m scripts.run_experiment --mode stego --stego 210 \
  --seed 42 --secret-size 16 --block-gap-ms 20 --window-size 128
```

All parameters match the original 23 + 23 sessions (`seed=42`,
`secret_size=16`, `block_gap_ms=20`, `window_size=128`), so old and new
sessions are directly comparable.

> Invocation note: the entry point must be run as a module
> (`python3 -m scripts.run_experiment`). Running it as a file
> (`python3 scripts/run_experiment.py`) fails with
> `ModuleNotFoundError: No module named 'scripts'` because Python puts
> `scripts/` rather than the project root on `sys.path`.

Post-processing, exactly the sequence documented in the repository README:

```bash
docker compose run --rm tests python -m scripts.dataset_builder --window-size 128
docker compose run --rm tests python -m scripts.split_dataset \
  --val-ratio 0.1 --test-ratio 0.1 --seed 42
docker compose run --rm tests python -m scripts.dataset_stats
docker compose run --rm tests python -m scripts.data_quality_report
docker compose run --rm tests python -m scripts.baseline_analysis
```

## Result

| Item | Before | After |
| --- | ---: | ---: |
| Normal sessions | 23 | 233 |
| Stego sessions | 23 | 233 |
| Failed sessions in `raw/` | 0 | 0 |
| Events (both classes) | 20 746 | 210 165 |
| Windows | 138 | 1 398 |
| Normal / Stego windows | 69 / 69 | 699 / 699 |
| X shape | `[138, 4, 128]` | `[1398, 4, 128]` |
| Sessions in train / val / test | 38 / 4 / 4 | 374 / 46 / 46 |
| Windows in train / val / test | 114 / 12 / 12 | 1122 / 138 / 138 |

The training split now holds **1122 windows**, which clears the
`>= 1000` figure the cWGAN-GP module documents.

## Failed sessions and how they were handled

Seven of the first 210 Stego sessions and one of the replacements failed with
the already-documented error:

```text
length_out_of_range: length 1600 / 2000 outside LOW(720, 880) / HIGH(1120, 1280)
```

Root cause: the receiver occasionally coalesces two consecutive proxy writes
into one observed read, so a pair of 800/1200 writes is observed as
1600/2000. The 20 ms `block_gap_ms` normally prevents this, so the error is a
timing race rather than a protocol defect. The failure rate was roughly 3%.

Handling:

1. the failed session directories were moved out of
   `dataset/raw/stego/` into `protocol_stego/raw_failed/stego/`
   (they are **not deleted**, but the dataset builder only scans
   `raw/normal` and `raw/stego`, so they cannot leak into the dataset);
2. fresh sessions were collected until 233 of 233 Stego sessions reported
   `success: true`.

Quarantined session ids:

```text
stego_000108  stego_000112  stego_000159  stego_000168
stego_000175  stego_000206  stego_000226  stego_000238
```

Note the consequence: because replacements were appended, the Stego session
ids in `raw/stego/` are `000001`-`000237` plus `000239`-`000241` — the ids of
the quarantined sessions are absent, and the count is still 233. Session ids
are identifiers, not indices, so this is expected.

## `run_summary.json`

Both collection workers write `dataset/raw/run_summary.json` at the end of
their own run, so the file cannot describe a combined run. It was therefore
rebuilt as an aggregate of every session's `metadata.json` (which is the
authoritative per-session record), preserving the original JSON schema and
adding a `note` field that states this. No session record was modified.

## Verified data quality

From the regenerated `DATA_QUALITY_REPORT.md`:

| Check | Result |
| --- | --- |
| Normal sessions | 233, all `success: true` |
| Stego sessions | 233, all `success: true` |
| X / y shape | `[1398, 4, 128]` / `[1398]`, float32 / int64 |
| NaN / Inf | 0 / 0 |
| train ∩ val, train ∩ test, val ∩ test | empty |
| duplicate samples | 0 |
| BER | 0.0 |
| frame error rate | 0.0 |
| CRC failure rate | 0.0 |
| Stego target / actual / observed counts | 800: 57780, 1200: 48468 for all three; 0 observed values outside 800/1200 |
| Comparability (Normal vs Stego mean) | duration ratio 1.015, event-count ratio 1.022, total-bytes ratio 1.018 |

Overall verdict from the report: **READY_FOR_CNN**.

## Limitations recorded by this run

1. **Normal traffic is still a fixed 1024 B write.** Feature statistics show
   Normal `length` identical to 1024 for every event, while Stego is exactly
   800/1200. Any detector trained on this pair therefore learns the
   800/1200 signature, not "is there a covert channel". The report repeats
   this and it must be repeated in any paper or slide that quotes the CNN
   metrics.
2. **The `direction` channel is constant 1** for both classes in the current
   window extraction (only forward-direction events are used), so it carries
   no information for the detector.
3. `dataset/processed/data_quality_report.json` is now ~199 MB and remains
   excluded by `.gitignore`.
4. `releases/dataset_release_v1/` still describes the previous 46-session
   snapshot and was **not** regenerated by this run.
