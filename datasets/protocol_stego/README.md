# protocol_stego Dataset Pointer

Phase 1 keeps the working dataset in:

```text
src/protocol_stego/dataset/
```

Reason: `scripts/dataset_builder.py`, `split_dataset.py`,
`dataset_stats.py`, `data_quality_report.py` and `compose.yaml` reference
that path by default.

The released, self-contained copy is:

```text
releases/dataset_release_v1/protocol_stego/
```

It contains:

- `raw/`
- `processed/X.npy`
- `processed/y.npy`
- `processed/windows.npz`
- `splits/`
- `metadata/`

Moving the working dataset into this directory requires updating compose
mounts and default paths; do that only in a dedicated migration step.
