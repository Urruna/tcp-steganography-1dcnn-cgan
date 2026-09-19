import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score, roc_curve)


def calculate_metrics(y, probability, threshold=0.5):
    y = np.asarray(y)
    p = np.asarray(probability)
    if y.ndim != 1 or p.shape != y.shape or not len(y):
        raise ValueError("Expected non-empty one-dimensional labels and probabilities")
    if not np.isin(y, [0, 1]).all() or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid labels or probabilities")
    pred = (p >= threshold).astype(np.int64)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    both = len(np.unique(y)) == 2
    return {
        "samples": len(y), "threshold": float(threshold),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)) if both else None,
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, p)) if both else None,
        "false_positive_rate": float(fp / (tn + fp)) if tn + fp else None,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def save_predictions(path, y, p, threshold=0.5):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["sample_index", "true_label", "predicted_label", "prob_stego", "correct"])
        for i, prob in enumerate(p):
            pred = int(prob >= threshold)
            label = "" if y is None else int(y[i])
            correct = "" if y is None else int(label == pred)
            writer.writerow([i, label, pred, float(prob), correct])


def plot_training(history, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    e = [r["epoch"] for r in history]
    for key, label in [("train_loss", "Train"), ("val_loss", "Validation")]:
        axes[0].plot(e, [r[key] for r in history], label=label)
    axes[0].set(title="Cross-entropy (unweighted, eval mode)", xlabel="Epoch", ylabel="Loss")
    for key, label in [("train_f1", "Train"), ("val_f1", "Validation")]:
        axes[1].plot(e, [r[key] for r in history], label=label)
    axes[1].set(title="F1 score", xlabel="Epoch", ylabel="F1", ylim=(-0.02, 1.02))
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_evaluation(y, p, threshold, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cm = confusion_matrix(y, p >= threshold, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.imshow(cm, cmap="Blues", vmin=0)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=18,
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Normal", "Stego"],
           yticklabels=["Normal", "Stego"], xlabel="Predicted", ylabel="Actual", title="CNN confusion matrix")
    fig.tight_layout()
    fig.savefig(out / "confusion_matrix.png", dpi=180)
    plt.close(fig)
    if len(np.unique(y)) == 2:
        fpr, tpr, thresholds = roc_curve(y, p)
        np.savetxt(out / "roc_points.csv", np.c_[fpr, tpr, thresholds], delimiter=",",
                   header="fpr,tpr,threshold", comments="")
        fig, ax = plt.subplots(figsize=(4.8, 4.2))
        ax.plot(fpr, tpr, label=f"CNN AUC = {roc_auc_score(y, p):.4f}")
        ax.plot([0, 1], [0, 1], "--", color="grey")
        ax.set(xlabel="False positive rate", ylabel="True positive rate", title="Test ROC", xlim=(0, 1), ylim=(0, 1.02))
        ax.grid(alpha=0.2)
        ax.legend(loc="lower right")
        fig.tight_layout()
        fig.savefig(out / "roc_curve.png", dpi=180)
        plt.close(fig)
