# Tools

## build_release

`build_release/build_dataset_release.py` is the dataset release builder
copied from `src/protocol_stego/scripts/build_dataset_release.py`.

It builds:

```text
releases/dataset_release_v1/
releases/dataset_release_v1.zip
checksums/SHA256SUMS.txt
```

Before running it after the repository reorganization, confirm its internal
paths point to:

```text
datasets/protocol_stego
datasets/historical/...
```

The original script remains unchanged in `src/protocol_stego/scripts/`.
