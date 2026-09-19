import argparse
import csv
import platform
import random
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from cnn_model import CNNDetector
from data_utils import FEATURES, load_config, load_split, resolve_path, sha256, write_json
from metrics import calculate_metrics, plot_training


@torch.inference_mode()
def assess(model, x, y, device, batch_size):
    model.eval()
    logits = torch.cat([model(torch.from_numpy(x[i:i+batch_size]).to(device)).cpu()
                        for i in range(0, len(x), batch_size)])
    loss = nn.functional.cross_entropy(logits, torch.from_numpy(y)).item()
    return loss, logits.softmax(1)[:, 1].numpy()


def train(config_path="config.json"):
    cfg = load_config(config_path)
    seed = cfg["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(cfg["num_threads"])
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device(cfg["device"])
    out = resolve_path(cfg["result_dir"])
    models = resolve_path(cfg["model_dir"])
    out.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)
    x_train, y_train = load_split(cfg["data_dir"], "train")
    x_val, y_val = load_split(cfg["data_dir"], "val")
    if len(np.unique(y_train)) != 2 or len(np.unique(y_val)) != 2:
        raise ValueError("Training and validation sets must contain both classes")
    # 训练过程只读取训练集和验证集。
    counts = np.bincount(y_train, minlength=2)
    weights = len(y_train) / (2 * counts) if cfg["class_weight"] else np.ones(2)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32, device=device))
    loader = DataLoader(TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train)),
                        batch_size=cfg["batch_size"], shuffle=True, num_workers=0,
                        generator=torch.Generator().manual_seed(seed))
    model = CNNDetector(cfg["dropout"]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"])
    best_loss, best_epoch, stale = float("inf"), 0, 0
    history = []
    started = time.perf_counter()
    for epoch in range(1, cfg["epochs"] + 1):
        model.train()
        for xb, yb in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(xb.to(device)), yb.to(device))
            loss.backward()
            optimizer.step()
        train_loss, train_p = assess(model, x_train, y_train, device, cfg["batch_size"])
        val_loss, val_p = assess(model, x_val, y_val, device, cfg["batch_size"])
        tm = calculate_metrics(y_train, train_p, cfg["threshold"])
        vm = calculate_metrics(y_val, val_p, cfg["threshold"])
        row = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss,
               "train_accuracy": tm["accuracy"], "val_accuracy": vm["accuracy"],
               "train_f1": tm["f1"], "val_f1": vm["f1"], "val_auc": vm["roc_auc"]}
        history.append(row)
        if val_loss < best_loss:
            best_loss, best_epoch, stale = val_loss, epoch, 0
            checkpoint = {"state_dict": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                "dropout": cfg["dropout"], "threshold": cfg["threshold"], "epoch": epoch,
                "val_loss": val_loss, "seed": seed, "input_shape": [4, 128], "features": FEATURES,
                "scaler_sha256": sha256(resolve_path(cfg["data_dir"]) / "scaler_params.npz")}
            torch.save(checkpoint, models / "best_model.pt")
        else:
            stale += 1
        if epoch == 1 or epoch % 10 == 0:
            print(f"epoch={epoch:03d} train_loss={train_loss:.4f} val_loss={val_loss:.4f} val_f1={vm['f1']:.4f}", flush=True)
        if stale >= cfg["patience"]:
            break
    with open(out / "history.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=history[0].keys())
        w.writeheader()
        w.writerows(history)
    plot_training(history, out / "training_curves.png")
    summary = {"best_epoch": best_epoch, "epochs_run": len(history), "best_val_loss": best_loss,
               "class_weights": weights.tolist(), "selection": "minimum unweighted validation cross-entropy",
               "threshold_selection": "fixed 0.5 before training", "config": cfg,
               "seconds": time.perf_counter() - started,
               "environment": {"python": platform.python_version(), "torch": str(torch.__version__),
                               "numpy": np.__version__, "platform": platform.platform()}}
    write_json(out / "training_summary.json", summary)
    print(f"Saved best_model.pt: epoch {best_epoch}; test set was not read during training.")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    train(parser.parse_args().config)
