import argparse
import csv

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from data_utils import WindowScaler, load_config, load_split, resolve_path, write_json
from detector import Detector
from metrics import calculate_metrics, plot_evaluation, save_predictions


def summary_features(raw):
    return np.concatenate([raw.mean(2), raw.std(2), raw.min(2), raw.max(2)], axis=1)


def evaluate(config_path="config.json"):
    cfg = load_config(config_path)
    out = resolve_path(cfg["result_dir"])
    out.mkdir(parents=True, exist_ok=True)
    data_dir = resolve_path(cfg["data_dir"])
    model_dir = resolve_path(cfg["model_dir"])
    detector = Detector(model_dir / "best_model.pt", data_dir / "scaler_params.npz", cfg["device"])
    scaler = WindowScaler(data_dir / "scaler_params.npz")
    cnn_metrics = {}
    for split in ["train", "val", "test"]:
        x, y = load_split(data_dir, split)
        p = detector.predict_proba(x, input_space="standardized")[:, 1]
        cnn_metrics[split] = calculate_metrics(y, p, detector.threshold)
        save_predictions(out / f"cnn_{split}_predictions.csv", y, p, detector.threshold)
        if split == "test":
            plot_evaluation(y, p, detector.threshold, out)
    write_json(out / "cnn_metrics.json", cnn_metrics)

    x_train, y_train = load_split(data_dir, "train")
    x_test, y_test = load_split(data_dir, "test")
    raw_train = scaler.inverse_transform(x_train)
    raw_test = scaler.inverse_transform(x_test)
    baseline = make_pipeline(StandardScaler(), LogisticRegression(
        C=1.0, max_iter=2000, class_weight="balanced", random_state=cfg["seed"]))
    baseline.fit(summary_features(raw_train), y_train)
    joblib.dump(baseline, model_dir / "logistic_baseline.joblib")
    p_lr = baseline.predict_proba(summary_features(raw_test))[:, 1]
    lr_metrics = calculate_metrics(y_test, p_lr)
    save_predictions(out / "logistic_test_predictions.csv", y_test, p_lr)
    # 规则作用于原始字节数；容差仅处理 float32 标准化的还原误差。
    lengths = raw_test[:, 1, :]
    rule = (np.isclose(lengths, 800, atol=0.01, rtol=0) |
            np.isclose(lengths, 1200, atol=0.01, rtol=0)).any(1).astype(float)
    rule_metrics = calculate_metrics(y_test, rule)
    rule_metrics["roc_auc"] = None  # 此规则只报告固定工作点，不把硬标签作为连续 ROC 分数。
    save_predictions(out / "rule_test_predictions.csv", y_test, rule)
    comparison = {"CNN": cnn_metrics["test"], "LogisticRegression": lr_metrics, "Rule8001200": rule_metrics}
    write_json(out / "comparison.json", comparison)
    with open(out / "comparison.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["model"] + list(cnn_metrics["test"].keys()))
        w.writeheader()
        for name, values in comparison.items():
            w.writerow({"model": name, **values})
    print("Test results (fixed thresholds):")
    for name, m in comparison.items():
        print(f"{name}: accuracy={m['accuracy']:.4f} F1={m['f1']:.4f} AUC={m['roc_auc']}")
    return comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    evaluate(parser.parse_args().config)
