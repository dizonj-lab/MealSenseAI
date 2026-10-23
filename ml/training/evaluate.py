"""Stage 9 — model evaluation: accuracy, precision, recall, F1, confusion matrix, per-class, top-5, latency."""
import csv
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from common import write_json


def evaluate_split(model, root: Path, manifest: str, tf, classes: list[dict], out_dir: Path) -> dict:
    names = [c["name"] for c in classes]
    n = len(names)
    with open(root / manifest) as f:
        rows = list(csv.DictReader(f))
    y_true, y_pred, topk_hit, lat = [], [], 0, []
    k = min(5, n)
    model.eval()
    with torch.no_grad():
        for r in rows:
            x = tf(Image.open(root / r["path"]).convert("RGB")).unsqueeze(0)
            t0 = time.perf_counter()
            logits = model(x)[0]
            lat.append((time.perf_counter() - t0) * 1000)
            y = int(r["class_idx"])
            y_true.append(y)
            y_pred.append(int(logits.argmax()))
            topk_hit += int(y in logits.topk(k).indices.tolist())
    cm = np.zeros((n, n), dtype=int)
    for a, b in zip(y_true, y_pred):
        cm[a, b] += 1
    per = {}
    for i, name in enumerate(names):
        tp, fp, fn = cm[i, i], cm[:, i].sum() - cm[i, i], cm[i, :].sum() - cm[i, i]
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        per[name] = {"precision": round(float(p), 4), "recall": round(float(rc), 4),
                     "f1": round(float(2 * p * rc / (p + rc)) if p + rc else 0.0, 4), "support": int(cm[i].sum())}
    s = sorted(lat)
    metrics = {
        "split": manifest.removesuffix(".csv"), "n_samples": len(rows),
        "accuracy": round(float(np.trace(cm) / cm.sum()), 4),
        "macro_precision": round(float(np.mean([v["precision"] for v in per.values()])), 4),
        "macro_recall": round(float(np.mean([v["recall"] for v in per.values()])), 4),
        "macro_f1": round(float(np.mean([v["f1"] for v in per.values()])), 4),
        f"top{k}_accuracy": round(topk_hit / len(rows), 4),
        "latency_avg_ms": round(sum(s) / len(s), 2), "latency_p95_ms": round(s[int(0.95 * (len(s) - 1))], 2),
        "per_class": per, "confusion_matrix": {"labels": names, "matrix": cm.tolist()},
    }
    write_json(out_dir / "metrics.json", metrics)
    plot_cm(cm, names, out_dir / "confusion_matrix.png")
    return metrics


def plot_cm(cm: np.ndarray, names: list[str], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sz = max(4, len(names) * 0.55)
    fig, ax = plt.subplots(figsize=(sz + 1, sz))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(names)), names, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(names)), names, fontsize=8)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=8, color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    ax.set_title("Confusion matrix (test split)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
