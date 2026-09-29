# 工具

## build_release

`build_release/build_dataset_release.py` 是数据集发布包的构建脚本，
从 `src/protocol_stego/scripts/build_dataset_release.py` 复制而来。

它会生成：

```text
releases/dataset_release_v1/
releases/dataset_release_v1.zip
checksums/SHA256SUMS.txt
```

仓库重组之后，运行它之前请先确认脚本内部的路径指向：

```text
datasets/protocol_stego
datasets/historical/...
```

原始脚本仍保留在 `src/protocol_stego/scripts/` 中，未做改动。
