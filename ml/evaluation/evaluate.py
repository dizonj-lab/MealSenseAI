"""End-to-end evaluation of the app's inference pipeline (detection + classification + fallbacks) on labeled
images, persisted as an Experiment.

Inputs: a folder per class (<root>/<class_name>/*.jpg, e.g. food-101/images) or a held-out manifest from
ml/training (--manifest datasets/processed/<ds>/test.csv). Only classes in CLASS_MAP are scored.
Usage: python ml/evaluation/evaluate.py <root> [--manifest test.csv] [--per-class 50] [--name food101-overlap]
"""
import csv
import argparse
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.core.db import SessionLocal  # noqa: E402
from app.core.migrate import upgrade_db  # noqa: E402
from app.models import Experiment  # noqa: E402
from app.services import vision  # noqa: E402

# Food-101 class -> nutrition key predicted by the pipeline
CLASS_MAP = {
    "pizza": "pizza", "hot_dog": "hot_dog", "hamburger": "cheeseburger", "ice_cream": "ice_cream",
    "guacamole": "guacamole", "spaghetti_carbonara": "carbonara", "donuts": "donut",
    "chocolate_cake": "chocolate_cake", "breakfast_burrito": "burrito", "club_sandwich": "sandwich",
    "steak": "beef_steak", "sushi": "sushi", "french_fries": "french_fries", "fried_rice": "nasi_goreng",
}


def _tmp_copy(img: Path) -> str:
    """analyze() writes an overlay next to the image; keep dataset folders untouched."""
    import shutil
    import tempfile
    d = Path(tempfile.mkdtemp())
    return str(shutil.copy(img, d / img.name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--per-class", type=int, default=50)
    ap.add_argument("--manifest", default=None, help="CSV with path,label columns relative to root")
    ap.add_argument("--name", default="food101-overlap")
    a = ap.parse_args()
    if a.manifest:
        with open(a.root / a.manifest) as f:
            rows = [(r["label"], a.root / r["path"]) for r in csv.DictReader(f)]
    else:
        rows = [(d.name, p) for d in sorted(a.root.iterdir()) if d.is_dir()
                for p in sorted(d.glob("*.jp*g"))[: a.per_class]]
    classes = sorted({c for c, _ in rows})
    used = [c for c in classes if c in CLASS_MAP]
    y_true, y_pred, lat = [], [], []
    for c, img in rows:
        if c in CLASS_MAP:
            t = time.perf_counter()
            preds = vision.merge([vision.analyze(_tmp_copy(img), "top")])
            lat.append((time.perf_counter() - t) * 1000)
            y_true.append(CLASS_MAP[c])
            y_pred.append(preds[0]["nutrition_key"] if preds else "none")
    if not y_true:
        sys.exit(f"No images found for mapped classes. Available classes: {classes[:10]}...")
    labels = sorted(set(y_true))
    tp = Counter(t for t, p in zip(y_true, y_pred) if t == p)
    pc, tc = Counter(y_pred), Counter(y_true)
    per = {}
    for lb in labels:
        p = tp[lb] / pc[lb] if pc[lb] else 0.0
        r = tp[lb] / tc[lb]
        per[lb] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0, "n": tc[lb]}
    s = sorted(lat)
    metrics = {
        "accuracy": sum(tp.values()) / len(y_true),
        "macro_precision": sum(v["precision"] for v in per.values()) / len(per),
        "macro_recall": sum(v["recall"] for v in per.values()) / len(per),
        "macro_f1": sum(v["f1"] for v in per.values()) / len(per),
        "no_prediction_rate": y_pred.count("none") / len(y_pred),
        "latency_avg_ms": sum(s) / len(s), "latency_p95_ms": s[int(0.95 * (len(s) - 1))],
        "throughput_img_s": 1000 / (sum(s) / len(s)), "per_class": per,
    }
    upgrade_db()
    with SessionLocal() as db:
        names = " + ".join(m["name"] for m in vision.models().values())
        db.add(Experiment(name=a.name, model_name=names, dataset=f"{a.root}" + (f" [{a.manifest}]" if a.manifest else ""),
                          n_samples=len(y_true), has_ground_truth=True, metrics=metrics,
                          notes=f"Scored classes: {used}. Skipped {len(classes) - len(used)} classes outside model vocabulary."))
        db.commit()
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in metrics.items() if k != "per_class"})
    vision.close()


if __name__ == "__main__":
    main()
