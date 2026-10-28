"""Export a frozen dataset version's user samples for training (run on the server, where the photos are):

    docker compose exec backend python -m app.tools.export_dataset EXP-003
    docker compose cp backend:/data/exports/EXP-003 datasets/raw/user_labels      # then train on the GPU machine

Only the samples in the version's manifest are written, and only those still shared: anything withdrawn or deleted
since the version was frozen is left out (and counted). Each crop uses the 12% padding the app classifies with,
in the folder-per-class layout ml/training/prepare_dataset.py reads as its "user_labels" source:

  <out>/<class_folder>/<sample_id>.jpg
  <out>/manifest.csv     one row per image: label, source, the model's own guess, weight, pseudonymous contributor
  <out>/summary.json     counts, withdrawals since freezing, labels that are not classes of the live model
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import DatasetVersion, TrainingSample
from app.services import datasets, screening, vision


def folder(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "unlabelled"


def export(version: str, out: Path) -> dict:
    vision.warmup()
    known = set((vision._state.get("cls") or {}).get("names") or [])
    with SessionLocal() as db:
        v = db.scalar(select(DatasetVersion).where(DatasetVersion.name == version))
        if not v:
            raise SystemExit(f"No dataset version called {version}")
        ids = v.manifest.get("sample_ids", [])
        weights = v.manifest.get("weights", {})
        rows = {s.id: s for s in db.scalars(select(TrainingSample).where(TrainingSample.id.in_(ids)))} if ids else {}
    out.mkdir(parents=True, exist_ok=True)
    written, withdrawn, deleted, missing = [], 0, 0, 0
    for i in ids:
        s = rows.get(i)
        if s is None:
            deleted += 1
            continue
        if s.withdrawn_at:
            withdrawn += 1
            continue
        if not Path(s.image_path).is_file():
            missing += 1
            continue
        dst = out / folder(s.label) / f"{s.id}.jpg"
        dst.parent.mkdir(parents=True, exist_ok=True)
        screening.crop(s.image_path, s.bbox).save(dst, quality=92)
        written.append({"path": str(dst.relative_to(out)), "label": s.label, "class_folder": folder(s.label),
                        "taxonomy_class": s.taxonomy_class or "", "custom_food_id": s.custom_food_id or "",
                        "nutrition_key": s.nutrition_key or "", "source": s.source, "model_label": s.model_label or "",
                        "model_score": s.model_score if s.model_score is not None else "",
                        "model_version": s.model_version or "", "weight": weights.get(str(s.id), 1.0),
                        "contributor": datasets.pseudonym(s.user_id), "bbox": json.dumps(s.bbox) if s.bbox else ""})
    with open(out / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(written[0]) if written else ["path"])
        w.writeheader()
        w.writerows(written)
    per = Counter(r["label"] for r in written)
    summary = {"dataset_version": version, "samples": len(written), "in_manifest": len(ids),
               "withdrawn_since_freeze": withdrawn, "deleted_since_freeze": deleted, "photo_missing": missing,
               "contributors": len({r["contributor"] for r in written}), "per_class": dict(per.most_common()),
               "by_source": dict(Counter(r["source"] for r in written)),
               "new_classes_not_in_live_model": sorted(lbl for lbl in per if lbl not in known),
               "base_datasets": v.manifest.get("base_datasets", []),
               "note": "New classes need an entry in ml/training/class_map.json (name -> nutrition key) and enough "
                       "images per class before retraining. Use the weight column: 0.5 marks samples that only "
                       "confirmed the model's own guess."}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Export a frozen dataset version for training")
    ap.add_argument("version")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    summary = export(a.version, a.out or settings.data_dir / "exports" / a.version)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
