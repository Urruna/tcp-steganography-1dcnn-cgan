# cWGAN-GP Status Report

Reported: 2026-09-26

Source of truth for the module itself: `src/cWGAN-GP/README_cWGAN.md`.
This report records **what is actually present in the repository**, not what
is planned.

## 1. What exists

| Item | Status | Location |
| --- | --- | --- |
| Conditional WGAN-GP implementation | Present | `src/cWGAN-GP/cWGAN-GP.py` (343 lines) |
| Module documentation | Present | `src/cWGAN-GP/README_cWGAN.md` |
| Trained generator checkpoint | **Absent** | – |
| Generated synthetic length strategies | **Absent** | – |
| GAN-Stego dataset | **Absent** | – |
| GAN-Stego detection results | **Absent** | – |

The module was added in commit `6840169` ("Add cWGAN-GP module and README",
2026-09-21). Nothing else in the repository imports it yet.

## 2. What the code does

```text
noise z + label
   → Generator → [B, 128] continuous values in [0, 1]
   → projection onto two non-overlapping length bands
        bit 0 → BIT0_RANGE = (-1.5, -0.5)
        bit 1 → BIT1_RANGE = ( 0.5,  1.5)
```

- Critic consumes length sequences only, with a label embedding.
- Loss: WGAN-GP (`Critic = E[D(fake)] - E[D(real)] + λ·GP`, `Generator = -E[D(fake)]`, `λ = 10.0`).
- Class balance via `WeightedRandomSampler`.
- Only the generator is saved in the checkpoint; no critic/optimizer state,
  so the checkpoint cannot resume training.

Design rationale recorded in the module README: the proxy can only control the
**application-layer write length**, so generating a full `[4, 128]` window
would produce a strategy the proxy cannot execute. Fixed 800/1200 lengths are
two sharp histogram spikes; two wide bands keep the bit decodable
(non-overlapping bands → single threshold in Proxy-B) while flattening the
histogram.

## 3. Blocking issue: training data volume

The module README states a hard requirement of **at least 1000 training
windows**, and documents an observed failure at the current size:

```text
Epoch    1/500 | Critic: -50.5     | Generator: 20.3
Epoch   20/500 | Critic: -6452.5   | Generator: 2792.9
Epoch   50/500 | Critic: -50489.5  | Generator: 23294.0
Epoch  130/500 | Critic: -400434.0 | Generator: 205152.5
```

Monotonic divergence of both losses is the described symptom of insufficient
samples.

Current data availability:

| Dataset | Training windows | Meets requirement |
| --- | ---: | --- |
| `datasets/protocol_stego/` | 114 (train split) | No |
| `src/1dcnn/data/` | 117 (train split) | No |

The module's stated target is 167 Normal + 167 Stego sessions ≈ 1000+ windows.
The repository currently has 23 + 23 sessions.

**No training run has been completed, so there is no cWGAN-GP result to report.**

## 4. Data interface inconsistencies (must be fixed before training)

These are verified by reading the code and the repository contents.

| # | Issue | Evidence |
| --- | --- | --- |
| 1 | Default `--data-dir` expects `real_train_X.npy` / `real_train_y.npy` **directly** under `datasets/protocol_stego/` | `cWGAN-GP.py` lines 147–148, `--data-dir` default |
| 2 | The repository only ships `datasets/protocol_stego/processed/windows.npz`; the two `.npy` files are present only under `releases/dataset_release_v1/.../processed/` and `src/1dcnn/data/` | directory listing |
| 3 | The code assumes a per-channel standardized length channel (`mean ≈ 0, std ≈ 1`) | `cWGAN-GP.py` lines 46–49 |
| 4 | The protocol dataset stores raw features (`direction = ±1`, `length = 800/1200`); no shared scaler was found for it | `datasets/protocol_stego/processed/stats.json` |
| 5 | `README_cWGAN.md` §10 states that the 1D-CNN uses `datasets/protocol_stego` | Actual 1D-CNN data is `src/1dcnn/data/real_train_X.npy` (168 windows) |

Consequence of (3) + (4): running with the default `BIT0_RANGE` / `BIT1_RANGE`
against unstandardized byte lengths would project into nonsensical values.
Either standardize the length channel and keep the defaults, or change the
ranges to the real byte bands (e.g. `(780, 820)` / `(1180, 1220)`) as the
module README describes.

## 5. What still has to happen

1. Implement the P0 data-expansion task (≥167 + 167 sessions) so that the
   1000-window requirement is met.
2. Reconcile the data interface: either export `real_train_X.npy` /
   `real_train_y.npy` into `datasets/protocol_stego/`, or point the loader at
   `processed/windows.npz`; then fix the band constants to match the actual
   length scale.
3. Train and record the loss curve; the pass condition per the module README is
   that both losses oscillate within roughly ±5 instead of diverging.
4. Generate synthetic length strategies and assemble `[N, 4, 128]` windows
   (replace channel 1 with generated lengths, keep the other three channels
   from real windows).
5. Execute the generated strategy through Proxy-A for real, re-collect the
   traffic, and evaluate Normal vs Baseline-Stego vs GAN-Stego with the same
   1D-CNN and the same session-level split.

## 6. Honest status summary

```text
cGAN implementation     : present
cGAN training           : blocked (data volume), no successful run
cGAN checkpoint         : none
GAN-Stego data          : none
GAN-Stego evaluation    : none
```

`PROJECT_STATUS.md` therefore records cGAN as **Partial**, not Completed and
not Design-only.
