"""Export user-labelled photo regions for the next training cycle.

Only users who opted in (Settings → "Use my corrected photos for training") are exported. Each sample's region
is cropped from the original photo (same 12% padding the app classifies with) into a folder-per-class layout that
ml/training/prepare_dataset.py reads as the "user_labels" source:

  datasets/raw/user_labels/<class_folder>/<sample_id>.jpg
  datasets/raw/user_labels/manifest.csv      one row per image (label, source, model's own guess, pseudonymous user)
  datasets/raw/user_labels/summary.json      counts per class; labels that are NOT EXP-002 classes (need a
                                             class-map entry / class-index extension before training)
Usage: python ml/export/export_training_samples.py [--out datasets/raw/user_labels] [--min-per-class 1]
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import TrainingSample, User  # noqa: E402
from app.services import vision  # noqa: E402

PAD = 0.12


def folder(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "unlabelled"


def crop(path: str, bbox: dict | None) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if not bbox:
        return img
    W, H = img.size
    x1, y1 = max(0.0, bbox["x"] - PAD * bbox["w"]), max(0.0, bbox["y"] - PAD * bbox["h"])
    x2, y2 = min(1.0, bbox["x"] + bbox["w"] * (1 + PAD)), min(1.0, bbox["y"] + bbox["h"] * (1 + PAD))
    return img.crop((round(x1 * W), round(y1 * H), round(x2 * W), round(y2 * H)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "datasets/raw/user_labels"))
    ap.add_argument("--min-per-class", type=int, default=1)
    a = ap.parse_args()
    out = Path(a.out)
    vision.warmup()
    known = set((vision._state.get("cls") or {}).get("names") or [])   # EXP-002's 320 class names
    with SessionLocal() as db:
        rows = db.execute(select(TrainingSample, User.id).join(User, User.id == TrainingSample.user_id)
                          .where(User.training_consent.is_(True)).order_by(TrainingSample.id)).all()
    counts = Counter(folder(s.label) for s, _ in rows)
    keep = [(s, uid) for s, uid in rows if counts[folder(s.label)] >= a.min_per_class]
    out.mkdir(parents=True, exist_ok=True)
    written, missing = [], 0
    for s, uid in keep:
        if not Path(s.image_path).is_file():
            missing += 1
            continue
        dst = out / folder(s.label) / f"{s.id}.jpg"
        dst.parent.mkdir(parents=True, exist_ok=True)
        crop(s.image_path, s.bbox).save(dst, quality=92)
        written.append({"path": str(dst.relative_to(out)), "label": s.label, "class_folder": folder(s.label),
                        "exp002_class": s.taxonomy_class or "", "custom_food_id": s.custom_food_id or "",
                        "nutrition_key": s.nutrition_key or "", "source": s.source, "model_label": s.model_label or "",
                        "model_score": s.model_score if s.model_score is not None else "", "model_version": s.model_version or "",
                        "user": hashlib.sha256(f"mealsense-user-{uid}".encode()).hexdigest()[:12],
                        "meal_id": s.meal_id, "bbox": json.dumps(s.bbox) if s.bbox else ""})
    with open(out / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(written[0]) if written else ["path"])
        w.writeheader()
        w.writerows(written)
    per = Counter(r["label"] for r in written)
    summary = {"samples": len(written), "skipped_missing_image": missing, "consenting_users": len({r["user"] for r in written}),
               "per_class": dict(per.most_common()), "by_source": dict(Counter(r["source"] for r in written)),
               "new_classes_not_in_exp002": sorted(l for l in per if l not in known),
               "note": "New classes need an entry in ml/training/class_map.json (name -> nutrition key) and enough "
                       "images per class before retraining; corrected labels of existing classes can be used as-is."}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
