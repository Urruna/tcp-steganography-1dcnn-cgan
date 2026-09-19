# Datasets

This directory separates datasets by source.

```text
datasets/
├── historical/
│   ├── docker_chain_smoke/
│   └── baseline_lenmix_v1/
├── normal_v1/
└── protocol_stego/          # pointer/README in phase 1
```

Important:

- Historical Normal and protocol Normal are different experiments.
- Do not mix them without an explicit experiment design.
- Raw data must not be modified, reordered, or re-encoded.
- The current protocol_stego working dataset is kept in
  `datasets/protocol_stego/`.
- The released copy is in `releases/dataset_release_v1/`.
- The 1D-CNN module under `src/1dcnn/` currently ships its own separate
  168-window dataset in `src/1dcnn/data/`; that dataset has no exact overlap
  with `datasets/protocol_stego/` and must not be silently merged with it.
