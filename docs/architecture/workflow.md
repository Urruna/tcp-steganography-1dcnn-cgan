# Workflow

## Target Workflow (from `new_727.md`)

```text
Normal Traffic
      ↓
Basic Stego
      ↓
Dataset
      ↓
1D-CNN
      ↓
cGAN
      ↓
GAN-Stego
      ↓
Evaluation
```

## Current Completion

| Stage | Status | Evidence |
| --- | --- | --- |
| Normal Traffic | Partial | historical Docker normal, `normal_v1`, 23 protocol Normal sessions |
| Basic Stego | Completed | 800/1200 length modulation, 23 Stego sessions |
| Dataset | Partial | 138 windows, session-level split, quality report |
| 1D-CNN | Partial | implemented/trained in `src/1dcnn/`; preliminary metrics use a separate 168-window dataset whose session split is unverified |
| cGAN | Design | only `new_727.md` plan |
| GAN-Stego | Not Implemented | no generator and no data |
| Evaluation | Partial | rule-based and Logistic Regression baselines only |

## Data Flow

```text
plaintext
 → AES-256-GCM
 → ciphertext
 → frame
 → bitstream
 → 800/1200 application-layer length modulation
 → TCP
 → Proxy-B length recovery
 → frame decode / CRC / reassembly
 → AES-256-GCM decrypt
```

## Analysis Flow

```text
raw session JSONL
 → observed_length event stream
 → 128-event windows
 → X = [N, 4, 128]
 → session-level train/val/test
 → rule-based / Logistic Regression / future CNN
```
