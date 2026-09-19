"""独立检测接口：供 GAN 模块或其他流量生成模块评估候选窗口。"""
import argparse

import numpy as np

from data_utils import resolve_path, validate_y, write_json
from detector import Detector
from metrics import calculate_metrics, plot_evaluation, save_predictions


def evaluate_windows(x, *, input_space, y=None, detector=None):
    detector = detector if detector is not None else Detector()
    probabilities = detector.predict_proba(x, input_space=input_space)
    score = probabilities[:, 1]
    result = {"probabilities": probabilities, "prob_stego": score,
              "labels": (score >= detector.threshold).astype(np.int64),
              "threshold": detector.threshold}
    if y is not None:
        y = validate_y(y, len(score))
        result["metrics"] = calculate_metrics(y, score, detector.threshold)
    return result


def main():
    parser = argparse.ArgumentParser(description="Evaluate external/GAN windows with a frozen CNN")
    parser.add_argument("--x", required=True, help=".npy, shape [N,4,128]")
    parser.add_argument("--y", help="Optional .npy labels, 0=Normal / 1=Stego")
    parser.add_argument("--input-space", choices=["raw", "standardized"], required=True)
    parser.add_argument("--model", default="models/best_model.pt")
    parser.add_argument("--scaler", default="data/scaler_params.npz")
    parser.add_argument("--out", default="results/external")
    args = parser.parse_args()
    x = np.load(resolve_path(args.x), allow_pickle=False)
    y = np.load(resolve_path(args.y), allow_pickle=False) if args.y else None
    if not len(x):
        raise ValueError("External dataset is empty")
    detector = Detector(args.model, args.scaler)
    result = evaluate_windows(x, input_space=args.input_space, y=y, detector=detector)
    out = resolve_path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "probabilities.npy", result["probabilities"])
    save_predictions(out / "predictions.csv", y, result["prob_stego"], result["threshold"])
    summary = {"samples": len(x), "input_space": args.input_space, "threshold": result["threshold"],
               "fraction_predicted_stego": float(result["labels"].mean()),
               "label_note": "Without ground-truth labels, prediction rate is not accuracy.",
               "evaluation_scope": "window-level frozen-detector evaluation; not a communication reliability test"}
    if y is not None:
        summary["metrics"] = result["metrics"]
        plot_evaluation(y, result["prob_stego"], result["threshold"], out)
    write_json(out / "summary.json", summary)
    print(f"Saved {len(x)} predictions to {out}")


if __name__ == "__main__":
    main()
