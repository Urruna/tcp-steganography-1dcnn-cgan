"""Session-level train/validation/test split (prevents window leakage)."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _split_ids(
    session_ids: list[str],
    *,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> tuple[list[str], list[str], list[str]]:
    rng = random.Random(seed)
    shuffled = list(session_ids)
    rng.shuffle(shuffled)
    n = len(shuffled)
    if n == 0:
        return [], [], []
    if n == 1:
        return shuffled, [], []
    if n == 2:
        return shuffled[:1], shuffled[1:], []
    test_count = max(1, round(n * test_ratio))
    val_count = max(1, round(n * val_ratio))
    if test_count + val_count >= n:
        test_count = 1
        val_count = 1
    train_count = n - test_count - val_count
    return (
        shuffled[:train_count],
        shuffled[train_count : train_count + val_count],
        shuffled[train_count + val_count :],
    )


def split_dataset(
    processed_dir: Path,
    splits_dir: Path,
    *,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> dict[str, object]:
    data = np.load(processed_dir / "windows.npz")
    X = data["X"]
    y = data["y"]
    index = _read_jsonl(processed_dir / "index.jsonl")
    if len(index) != len(y):
        raise RuntimeError("index length does not match y length")

    sessions_by_label: dict[int, set[str]] = {0: set(), 1: set()}
    for item in index:
        sessions_by_label[int(item["label"])].add(str(item["session_id"]))

    split_sessions: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for label in (0, 1):
        train, val, test = _split_ids(
            sorted(sessions_by_label[label]),
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed + label,
        )
        split_sessions["train"].update(train)
        split_sessions["val"].update(val)
        split_sessions["test"].update(test)

    train_ids = split_sessions["train"]
    val_ids = split_sessions["val"]
    test_ids = split_sessions["test"]
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        overlap = split_sessions[left] & split_sessions[right]
        if overlap:
            raise RuntimeError(f"session overlap between {left} and {right}: {sorted(overlap)}")

    splits_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "val_ratio": val_ratio,
        "test_ratio": test_ratio,
        "seed": seed,
        "splits": {},
    }
    for split_name, session_ids in (
        ("train", train_ids),
        ("val", val_ids),
        ("test", test_ids),
    ):
        selected = [
            idx
            for idx, item in enumerate(index)
            if str(item["session_id"]) in session_ids
        ]
        split_X = X[selected]
        split_y = y[selected]
        np.savez_compressed(
            splits_dir / f"{split_name}.npz",
            X=split_X,
            y=split_y,
        )
        (splits_dir / f"{split_name}_index.jsonl").write_text(
            "\n".join(json.dumps(index[idx], ensure_ascii=False) for idx in selected) + "\n",
            encoding="utf-8",
        )
        manifest["splits"][split_name] = {  # type: ignore[index]
            "sessions": sorted(session_ids),
            "session_count": len(session_ids),
            "sample_count": int(len(split_y)),
            "class_distribution": {
                "normal": int((split_y == 0).sum()),
                "stego": int((split_y == 1).sum()),
            },
        }
    manifest["overlap_checked"] = True
    (splits_dir / "split_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="split dataset by session id")
    base = Path(__file__).resolve().parents[1]
    parser.add_argument("--processed-dir", default=str(base / "dataset" / "processed"))
    parser.add_argument("--splits-dir", default=str(base / "dataset" / "splits"))
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    manifest = split_dataset(
        Path(args.processed_dir),
        Path(args.splits_dir),
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
