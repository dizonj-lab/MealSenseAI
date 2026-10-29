"""Copy the EXP-001/EXP-002 training evidence (produced on Buddy) into the repository and derive summary figures.

Usage: python derive_training_evidence.py <unpacked evidence folder>   (the folder holding evidence/ and datasets/)
Large or path-bearing files (best_model.pth, predictions.csv, excluded_images.csv, duplicate_audit.json) are read
but not copied; their summaries are written instead.
"""
import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np

SRC = Path(sys.argv[1])
EV = SRC / "evidence"
OUT = Path(__file__).resolve().parents[2] / "ml/models/exp002/evidence/training"
OUT.mkdir(parents=True, exist_ok=True)

COPY = ["cleaning_summary.json", "dataset_inventory.json", "dataset_splits.json"]
for exp in ("EXP-001_UnifiedFood", "EXP-002_FineTuning"):
    COPY += [f"{exp}/{f}" for f in ("config.json", "summary.json", "environment.json", "training_history.csv")]
COPY += [f"EXP-002_FineTuning/evaluation/{f}" for f in ("overall_metrics.json", "dataset_metrics.json", "confidence_calibration.json",
                                                         "classification_report.json", "confusion_matrix.png", "confidence_reliability.png")]
for f in COPY:
    (OUT / f).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EV / f, OUT / f)

name = {v: k for k, v in json.loads((SRC / "datasets/class_mapping.json").read_text()).items()}
E = EV / "EXP-002_FineTuning/evaluation"
derived = {}

# data cleaning: duplicates, exclusions, and whether any duplicate still spans two splits after exclusion
audit = json.loads((EV / "duplicate_audit.json").read_text())
excluded = list(csv.DictReader(open(EV / "excluded_images.csv")))
gone = {r["image_path"] for r in excluded}
spanning = sum(len({x["split"] for x in g if x["image_path"] not in gone}) > 1 for g in audit["cross_split_duplicates"].values())
derived["cleaning"] = {"audit": audit["summary"], "excluded_by_reason": Counter(r["exclusion_reason"] for r in excluded),
                       "cross_split_groups_remaining_after_exclusion": spanning}

# per-class F1 with names; per-dataset macro-F1 over each dataset's own classes
cr = json.loads((E / "classification_report.json").read_text())
per_class = sorted(((name[int(k)], v["precision"], v["recall"], v["f1-score"], int(v["support"])) for k, v in cr.items() if k.isdigit()), key=lambda r: r[3])
with open(OUT / "per_class_f1.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["class", "precision", "recall", "f1", "support"]); w.writerows([[n, round(p, 4), round(r, 4), round(f, 4), s] for n, p, r, f, s in per_class])
f1 = np.array([r[3] for r in per_class])
derived["per_class_f1"] = {"classes": len(f1), "median": round(float(np.median(f1)), 4), "f1_ge_0.8": int((f1 >= 0.8).sum()), "f1_lt_0.5": int((f1 < 0.5).sum()),
                           "lowest": [[n, round(f, 3), s] for n, _, _, f, s in per_class[:10]], "highest": [[n, round(f, 3), s] for n, _, _, f, s in per_class[-10:]]}

preds = list(csv.DictReader(open(E / "predictions.csv")))
by_ds = {}
for ds in sorted({r["dataset"] for r in preds}):
    p = [r for r in preds if r["dataset"] == ds]
    f1s = []
    for c in sorted({r["true_label_id"] for r in p}):
        tp = sum(r["true_label_id"] == c and r["predicted_label_id"] == c for r in p)
        fn = sum(r["true_label_id"] == c for r in p) - tp
        fp = sum(r["predicted_label_id"] == c and r["true_label_id"] != c for r in p)
        pr, rc = (tp / (tp + fp) if tp + fp else 0), (tp / (tp + fn) if tp + fn else 0)
        f1s.append(2 * pr * rc / (pr + rc) if pr + rc else 0)
    by_ds[ds] = {"images": len(p), "classes": len(f1s), "top1": round(sum(r["correct"] == "True" for r in p) / len(p), 4),
                 "top3": round(sum(r["top3_correct"] == "True" for r in p) / len(p), 4), "macro_f1_own_classes": round(float(np.mean(f1s)), 4)}
derived["per_dataset"] = by_ds

# most frequent confusions
M = np.load(E / "confusion_matrix.npy"); np.fill_diagonal(M, 0)
top = np.dstack(np.unravel_index(np.argsort(M.ravel())[::-1][:15], M.shape))[0]
derived["top_confusions"] = [[name[int(i)], name[int(j)], int(M[i, j])] for i, j in top]

# confidence: calibration error and the app's thresholds (0.20 not auto-added, 0.20-0.50 marked for checking)
cal = json.loads((E / "confidence_calibration.json").read_text())
n = sum(b["samples"] for b in cal)
conf = np.array([float(r["confidence"]) for r in preds]); ok = np.array([r["correct"] == "True" for r in preds])
derived["confidence"] = {"ece_10_bins": round(sum(b["samples"] * abs(b["mean_confidence"] - b["actual_accuracy"]) for b in cal) / n, 4),
                         "bands": {f"{lo}-{hi}": {"share": round(float(((conf >= lo) & (conf < hi)).mean()), 4), "top1": round(float(ok[(conf >= lo) & (conf < hi)].mean()), 4)}
                                   for lo, hi in ((0, 0.2), (0.2, 0.5), (0.5, 1.01))}}
(OUT / "derived_summary.json").write_text(json.dumps(derived, indent=1, default=int))
print(json.dumps(derived, indent=1, default=int)[:3000])
