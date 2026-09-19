import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
FEATURES = ["direction", "write_len", "interval", "cum_bytes"]


def resolve_path(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_config(path="config.json"):
    return json.loads(resolve_path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_x(x):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 3 or x.shape[1:] != (4, 128):
        raise ValueError(f"X must have shape [N,4,128], got {x.shape}")
    if not np.isfinite(x).all():
        raise ValueError("X contains NaN or Inf")
    return np.ascontiguousarray(x)


def validate_y(y, n):
    y = np.asarray(y)
    if y.shape != (n,) or not np.isin(y, [0, 1]).all():
        raise ValueError("y must have shape [N] and only contain 0/1")
    return y.astype(np.int64)


def load_split(data_dir, split):
    p = resolve_path(data_dir)
    x = validate_x(np.load(p / f"real_{split}_X.npy", allow_pickle=False))
    y = validate_y(np.load(p / f"real_{split}_y.npy", allow_pickle=False), len(x))
    if not len(x):
        raise ValueError(f"Empty {split} split")
    return x, y


class WindowScaler:
    # 与原 scaler 一致：按 C 顺序展平，对 512 个位置分别标准化。
    def __init__(self, path):
        with np.load(resolve_path(path), allow_pickle=False) as s:
            self.mean = s["mean"].astype(np.float64)
            self.scale = s["scale"].astype(np.float64)
        if self.mean.shape != (512,) or self.scale.shape != (512,):
            raise ValueError("Scaler must contain 512 positions")
        if not np.isfinite(self.mean).all() or not np.isfinite(self.scale).all() or (self.scale <= 0).any():
            raise ValueError("Invalid scaler parameters")

    def transform(self, raw):
        x = validate_x(raw)
        return ((x.reshape(len(x), 512).astype(np.float64) - self.mean) / self.scale).reshape(x.shape).astype(np.float32)

    def inverse_transform(self, standardized):
        x = validate_x(standardized)
        return (x.reshape(len(x), 512).astype(np.float64) * self.scale + self.mean).reshape(x.shape)


def audit_data(data_dir):
    p = resolve_path(data_dir)
    report = {"splits": {}, "exact_cross_split_duplicates": {}, "files_sha256": {},
              "session_split_verified": False,
              "session_note": "未提供样本会话索引，无法验证会话隔离；数组重复检查不能替代会话检查。"}
    hashes = {}
    for split in ["train", "val", "test"]:
        x, y = load_split(p, split)
        h = [hashlib.sha256(row.tobytes()).hexdigest() for row in x]
        hashes[split] = set(h)
        report["splits"][split] = {"X_shape": list(x.shape), "y_shape": list(y.shape),
            "normal": int((y == 0).sum()), "stego": int((y == 1).sum()),
            "exact_internal_duplicates": len(h) - len(set(h)), "finite": True}
        for suffix in ["X", "y"]:
            name = f"real_{split}_{suffix}.npy"
            report["files_sha256"][name] = sha256(p / name)
    for left, right in [("train", "val"), ("train", "test"), ("val", "test")]:
        report["exact_cross_split_duplicates"][f"{left}_{right}"] = len(hashes[left] & hashes[right])
    report["files_sha256"]["scaler_params.npz"] = sha256(p / "scaler_params.npz")
    return report
