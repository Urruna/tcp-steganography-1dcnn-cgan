# 1D-CNN Results

## Module Location

```text
src/1dcnn/
```

The module contains:

- two-layer 1D-CNN (`cnn_model.py`);
- training/evaluation pipeline (`train.py`, `evaluate.py`, `run_all.py`);
- frozen inference interface (`detector.py`, `gan_interface.py`);
- Logistic Regression and 800/1200 rule baselines;
- trained checkpoint (`models/best_model.pt`);
- result reports and plots (`results/`);
- pipeline tests (`tests/test_pipeline.py`).

## Data Used By This Module

The module ships its own dataset:

```text
data/real_{train,val,test}_{X,y}.npy
data/scaler_params.npz
```

Shapes and labels:

| Split | Samples | Normal | Stego |
| --- | ---: | ---: | ---: |
| train | 117 | 32 | 85 |
| val | 26 | 6 | 20 |
| test | 25 | 10 | 15 |

Input form:

```text
X = [N, 4, 128]
features = direction, write_len, interval, cum_bytes
labels = 0 Normal, 1 Baseline-Stego
```

The dataset summary says the window configuration is `window=128`,
`step=64`. It has **no session index**.

## Relation To The Repository Dataset

The repository's current `datasets/protocol_stego/processed/windows.npz`
contains 138 windows (`window=128`, non-overlapping) with balanced labels
(69 Normal / 69 Stego).

The 1D-CNN module's 168 windows have **zero exact overlap** with those 138
windows. They must be treated as a separate dataset until their generation
and session mapping are confirmed.

## Model

```text
Conv1d(4, 32, kernel=5, padding=2)
→ BatchNorm → ReLU → MaxPool(2)
→ Conv1d(32, 64, kernel=5, padding=2)
→ BatchNorm → ReLU → GlobalAveragePooling
→ Dropout(0.3)
→ Linear(64, 2)
```

Training configuration:

| Item | Value |
| --- | --- |
| Seed | 42 |
| Epochs | 100 |
| Batch size | 32 |
| Learning rate | 0.001 |
| Weight decay | 0.0001 |
| Dropout | 0.3 |
| Class weighting | enabled |
| Threshold | 0.5, fixed before training |
| Device | CPU |

Training did not read the test split.

## Reported Test Results

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | TN/FP/FN/TP |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| CNN | 0.9200 | 0.8824 | 1.0000 | 0.9375 | 0.9867 | 8/2/0/15 |
| Logistic Regression | 0.8800 | 1.0000 | 0.8000 | 0.8889 | 1.0000 | 10/0/3/12 |
| Rule8001200 | 0.8800 | 1.0000 | 0.8000 | 0.8889 | — | 10/0/3/12 |

Recorded software tests:

```text
6 tests OK
```

## How To Run

```bash
cd src/1dcnn
python -m pip install -r requirements.txt

# evaluate the saved model
python evaluate.py

# run pipeline/interface tests
python -m unittest discover -s tests -v

# retrain from scratch (overwrites models/ and results/)
python run_all.py
```

Use a copy of the directory if the delivered result files must be preserved.

## Known Limitations

1. **Session isolation is not verified.**  
   `results/data_check.json` explicitly records
   `session_split_verified: false`; no window-to-session mapping was
   provided.

2. **Different dataset from `datasets/protocol_stego`.**  
   The module uses 168 overlapping-like windows (`step=64`), while the
   repository dataset has 138 non-overlapping windows. Exact overlap is zero.

3. **Small test set.**  
   Only 25 test windows; one window corresponds to 4 percentage points of
   accuracy.

4. **Class imbalance.**  
   The module dataset is imbalanced (for example, train 32 Normal / 85
   Stego).

5. **No GAN-Stego data.**  
   The GAN interface exists, but no real GAN-generated windows have been
   evaluated. Do not present interface demo results as GAN results.

6. **Application-layer features only.**  
   Results are not direct packet-capture or real-network detection results.

## Recommended Next Step

Before using this model as a formal cross-session detector:

1. obtain the generation script and session IDs for the 168-window dataset;
2. re-split train/val/test by session;
3. regenerate the scaler on the training split only;
4. retrain and record the new metrics;
5. keep the current results as preliminary only.
