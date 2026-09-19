"""生成 Normal 数据集使用的确定性测试文件。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from pathlib import Path


def _text_bytes(target_size: int, prefix: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    index = 0
    while total < target_size:
        line = (
            f"{prefix}|record={index:07d}|"
            f"payload=normal-proxy-file-transfer-{'x' * 24}\n"
        ).encode("utf-8")
        chunks.append(line)
        total += len(line)
        index += 1
    return b"".join(chunks)[:target_size]


def _binary_bytes(target_size: int, seed: int) -> bytes:
    return random.Random(seed).randbytes(target_size)


def _write(path: Path, data: bytes) -> dict[str, object]:
    path.write_bytes(data)
    return {
        "name": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def generate(directory: Path) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "experiment_id": "normal_v1",
        "files": [
            _write(directory / "report_small.txt", _text_bytes(64 * 1024, "small")),
            _write(directory / "report_medium.txt", _text_bytes(256 * 1024, "medium")),
            _write(directory / "report_large.bin", _binary_bytes(1024 * 1024, 917)),
        ],
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="generate normal dataset files")
    parser.add_argument("--dir", default=os.getenv("FILES_DIR", "files"))
    args = parser.parse_args()
    manifest = generate(Path(args.dir))
    for item in manifest["files"]:
        print(
            f"[make_files] {item['name']} bytes={item['bytes']} "
            f"sha256={item['sha256']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
