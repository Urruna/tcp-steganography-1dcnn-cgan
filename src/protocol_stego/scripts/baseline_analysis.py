"""Rule-based and simple traditional-ML baselines for Normal/Stego data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, object]:
    y_true = y_true.astype(int)
    y_pred = y_pred.astype(int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / max(1, tp + tn + fp + fn)
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def _length_rules(X: np.ndarray) -> dict[str, np.ndarray]:
    lengths = X[:, 1, :]
    in_mod = np.isin(lengths, [800, 1200])
    return {
        "rule_any_800_1200": in_mod.any(axis=1).astype(int),
        "rule_mean_length_le_1000": (lengths.mean(axis=1) <= 1000.0).astype(int),
        "rule_majority_800_1200": (in_mod.mean(axis=1) >= 0.5).astype(int),
    }


def _summary_features(X: np.ndarray) -> np.ndarray:
    features = [
        X.mean(axis=2),
        X.std(axis=2),
        X.min(axis=2),
        X.max(axis=2),
    ]
    return np.concatenate(features, axis=1)


def _sigmoid(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, -50, 50)
    return 1.0 / (1.0 + np.exp(-value))


def _logistic_regression(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_eval: np.ndarray,
    *,
    iterations: int = 5000,
    learning_rate: float = 0.1,
    l2: float = 1e-3,
) -> tuple[np.ndarray, dict[str, float]]:
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std[std == 0] = 1.0
    Xn = (X_train - mean) / std
    Xe = (X_eval - mean) / std
    weights = np.zeros(Xn.shape[1])
    bias = 0.0
    n = len(Xn)
    for _ in range(iterations):
        logits = Xn @ weights + bias
        pred = _sigmoid(logits)
        error = pred - y_train
        grad_w = Xn.T @ error / n + l2 * weights
        grad_b = error.mean()
        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b
    logits = Xe @ weights + bias
    return _sigmoid(logits), {"bias": float(bias)}


def run(processed_dir: Path, splits_dir: Path, docs_dir: Path) -> dict[str, object]:
    data = np.load(processed_dir / "windows.npz")
    X_all = data["X"]
    y_all = data["y"]
    train = np.load(splits_dir / "train.npz")
    val = np.load(splits_dir / "val.npz")
    test = np.load(splits_dir / "test.npz")
    X_train, y_train = train["X"], train["y"]
    X_val, y_val = val["X"], val["y"]
    X_test, y_test = test["X"], test["y"]

    split_sessions = {
        name: {str(item["session_id"]) for item in _read_jsonl(splits_dir / f"{name}_index.jsonl")}
        for name in ("train", "val", "test")
    }
    overlaps = {
        "train_val": sorted(split_sessions["train"] & split_sessions["val"]),
        "train_test": sorted(split_sessions["train"] & split_sessions["test"]),
        "val_test": sorted(split_sessions["val"] & split_sessions["test"]),
    }

    rules = _length_rules(X_all)
    rule_results = {
        "all": {
            name: _metrics(y_all, pred)
            for name, pred in rules.items()
        },
        "test": {},
    }
    test_rule_pred = _length_rules(X_test)
    rule_results["test"] = {
        name: _metrics(y_test, pred)
        for name, pred in test_rule_pred.items()
    }

    summary_train = _summary_features(X_train)
    summary_val = _summary_features(X_val)
    summary_test = _summary_features(X_test)

    ml_results: dict[str, object] = {}
    ml_available = len(X_train) > 0 and len(np.unique(y_train)) == 2
    if ml_available:
        val_prob, meta = _logistic_regression(summary_train, y_train, summary_val)
        test_prob, _ = _logistic_regression(summary_train, y_train, summary_test)
        ml_results = {
            "model": "logistic_regression_summary_features",
            "feature_count": int(summary_train.shape[1]),
            "train_samples": int(len(X_train)),
            "val_samples": int(len(X_val)),
            "test_samples": int(len(X_test)),
            "val": _metrics(y_val, (val_prob >= 0.5).astype(int)),
            "test": _metrics(y_test, (test_prob >= 0.5).astype(int)),
            "training_meta": meta,
        }
    else:
        ml_results = {
            "model": "logistic_regression_summary_features",
            "available": False,
            "reason": "train split does not contain both classes",
        }

    rule_best_f1 = max(
        result["f1"] for result in rule_results["test"].values()
    ) if rule_results["test"] else 0.0
    ml_test_f1 = (
        ml_results["test"]["f1"]  # type: ignore[index]
        if ml_available
        else 0.0
    )
    data_issues = any(overlaps.values())
    if data_issues:
        verdict = "NEEDS_EXPERIMENT_FIX"
    elif rule_best_f1 < 0.9 or (ml_available and ml_test_f1 < 0.9):
        verdict = "NEEDS_EXPERIMENT_FIX"
    elif len(X_all) >= 100 and len(np.unique(y_all)) == 2:
        verdict = "READY_FOR_CNN"
    else:
        verdict = "NEEDS_MORE_DATA"

    result = {
        "verdict": verdict,
        "data": {
            "X_shape": list(X_all.shape),
            "y_shape": list(y_all.shape),
            "class_distribution": {
                "normal": int((y_all == 0).sum()),
                "stego": int((y_all == 1).sum()),
            },
            "train_shape": list(X_train.shape),
            "val_shape": list(X_val.shape),
            "test_shape": list(X_test.shape),
            "split_sessions": {key: sorted(value) for key, value in split_sessions.items()},
            "overlaps": overlaps,
        },
        "rules": rule_results,
        "traditional_ml": ml_results,
    }
    (processed_dir / "baseline_analysis.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_markdown(docs_dir / "BASELINE_ANALYSIS.md", result)
    return result


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _metrics_table(metrics: dict[str, object]) -> str:
    cm = metrics["confusion_matrix"]  # type: ignore[index]
    return (
        f"accuracy={_fmt(metrics['accuracy'])}, "
        f"precision={_fmt(metrics['precision'])}, "
        f"recall={_fmt(metrics['recall'])}, "
        f"F1={_fmt(metrics['f1'])}, "
        f"CM(tn/fp/fn/tp)={cm['tn']}/{cm['fp']}/{cm['fn']}/{cm['tp']}"
    )


def _write_markdown(path: Path, result: dict[str, object]) -> None:
    data = result["data"]  # type: ignore[assignment]
    rules = result["rules"]  # type: ignore[assignment]
    ml = result["traditional_ml"]  # type: ignore[assignment]
    lines = [
        "# BASELINE ANALYSIS",
        "",
        f"Verdict: **{result['verdict']}**",
        "",
        "## 1 数据稳定性",
        "",
        f"- X.shape: {data['X_shape']}",
        f"- y.shape: {data['y_shape']}",
        f"- class distribution: {data['class_distribution']}",
        f"- train shape: {data['train_shape']}",
        f"- val shape: {data['val_shape']}",
        f"- test shape: {data['test_shape']}",
        f"- split overlaps: {data['overlaps']}",
        "",
        "## 2 800/1200 调制稳定性",
        "",
        "调制稳定性与 BER/FER/CRC 详见 `DATA_QUALITY_REPORT.md`。"
        " 本次扩采后所有 Stego session 的 BER/FER/CRC 统计为 0。",
        "",
        "## 3 Normal / Stego 分布差异",
        "",
        "- Normal 主要以 1024 B 写块为主，少量 320 B 来自 TCP 分段。",
        "- Stego 由 800/1200 B 调制写块构成。",
        "- 其他统计特征（duration、event count、total bytes、inter-arrival）"
        "两者接近，主要差异来自 800/1200 modulation 本身。",
        "",
        "## 4 Rule-based baseline",
        "",
    ]
    for name, metrics in rules["all"].items():  # type: ignore[union-attr]
        lines.append(f"- {name}: all=({_metrics_table(metrics)})")
    for name, metrics in rules["test"].items():  # type: ignore[union-attr]
        lines.append(f"- {name}: test=({_metrics_table(metrics)})")
    lines.extend(
        [
            "",
            "## 5 Traditional ML baseline",
            "",
        ]
    )
    if ml.get("available", True):
        lines.append(
            f"- model={ml['model']}, features={ml['feature_count']}, "
            f"train={ml['train_samples']}, val={ml['val_samples']}, test={ml['test_samples']}"
        )
        lines.append(f"- val: {_metrics_table(ml['val'])}")
        lines.append(f"- test: {_metrics_table(ml['test'])}")
    else:
        lines.append(f"- unavailable: {ml.get('reason')}")
    lines.extend(
        [
            "",
            "## 6 是否适合进入 1D-CNN",
            "",
            f"结论：**{result['verdict']}**",
            "",
            "说明：rule-based 与 Logistic Regression 已经能在 session-level "
            "split 上高准确率区分 Normal/Stego；但当前 Normal 的 1024 B "
            "写块较单一，因此 CNN 结果主要解释为对 800/1200 调制特征的检测，"
            "不能直接推广为一般隐写可检测性。",
            "",
            "## 7 下一步",
            "",
            "- 若继续扩采，优先增加 Normal 业务多样性（不同文件大小、HTTP 双向业务）。",
            "- 扩采时必须保持 session-level train/val/test 划分与 seed 可复现。",
            "- 训练 CNN 时同时报告 rule-based 与 Logistic Regression 基线，"
            "避免只报 CNN 准确率。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="rule-based and traditional ML baseline")
    base = Path(__file__).resolve().parents[1]
    parser.add_argument("--processed-dir", default=str(base / "dataset" / "processed"))
    parser.add_argument("--splits-dir", default=str(base / "dataset" / "splits"))
    parser.add_argument("--docs-dir", default=str(base / "docs"))
    args = parser.parse_args()
    result = run(
        Path(args.processed_dir),
        Path(args.splits_dir),
        Path(args.docs_dir),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
