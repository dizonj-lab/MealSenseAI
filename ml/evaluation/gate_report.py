"""Evaluate a candidate classifier against the live one on the fixed gate test set, and write the report the model
gate reads (Admin → Models → Upload).

The gate test set is a folder per class (<test-dir>/<class name>/*.jpg; folder names are taxonomy class names,
or the same with underscores). Build it once from a training run's held-out split and never change it: the gate
refuses a report made on a different set (its SHA-256 is in the report). User data must never be in it.

    python ml/evaluation/gate_report.py --candidate path/to/EXP-003 --test-dir datasets/gate_test \
        --name EXP-003 --dataset-version EXP-003

The candidate folder holds model.onnx, class_mapping.json and model_card.json (as ml/models/exp002 does); the report
is written there as report.json, so the folder is the complete package to upload. Runs on CPU or CUDA (onnxruntime).
"""
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.preprocess import to_input  # noqa: E402

GROUPS = json.loads((Path(__file__).with_name("safety_classes.json")).read_text())["groups"]
EXT = {".jpg", ".jpeg", ".png", ".webp"}


def norm(name: str) -> str:
    return name.lower().replace("_", " ").strip()


def load(model_dir: Path):
    mapping = json.loads((model_dir / "class_mapping.json").read_text())
    card = json.loads((model_dir / "model_card.json").read_text())
    providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in ort.get_available_providers()]
    sess = ort.InferenceSession(str(model_dir / "model.onnx"), providers=providers)
    names = [None] * len(mapping)
    for n, i in mapping.items():
        names[i] = n
    return {"session": sess, "names": names, "card": card}


def test_set(test_dir: Path) -> tuple[list[tuple[Path, str]], str]:
    items, h = [], hashlib.sha256()
    for f in sorted(p for p in test_dir.rglob("*") if p.suffix.lower() in EXT):
        label = norm(f.parent.name)
        items.append((f, label))
        h.update(f"{f.relative_to(test_dir)}\0{hashlib.sha256(f.read_bytes()).hexdigest()}\n".encode())
    return items, h.hexdigest()


def evaluate(model, items) -> dict:
    hits, per_class, per_group = 0, defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    group_of = {norm(c): g for g, cs in GROUPS.items() for c in cs}
    for path, label in items:
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        logits = model["session"].run(None, {"input": to_input(img)})[0][0]
        ok = norm(model["names"][int(np.argmax(logits))]) == label
        hits += ok
        per_class[label][0] += ok
        per_class[label][1] += 1
        if label in group_of:
            per_group[group_of[label]][0] += ok
            per_group[group_of[label]][1] += 1
    return {"model": model["card"].get("version") or model["card"].get("name"), "overall_top1": round(hits / len(items), 4),
            "groups": {g: round(a / n, 4) for g, (a, n) in per_group.items() if n},
            "group_images": {g: n for g, (_, n) in per_group.items()},
            "per_class": {c: round(a / n, 4) for c, (a, n) in sorted(per_class.items())}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--live", type=Path, default=ROOT / "ml/models/exp002")
    ap.add_argument("--test-dir", required=True, type=Path)
    ap.add_argument("--name", required=True)
    ap.add_argument("--dataset-version")
    a = ap.parse_args()
    items, sha = test_set(a.test_dir)
    if not items:
        sys.exit(f"No images under {a.test_dir}")
    live, cand = load(a.live), load(a.candidate)
    unknown = sorted({lbl for _, lbl in items} - {norm(n) for n in live["names"]})
    report = {"name": a.name, "dataset_version": a.dataset_version, "created_at": datetime.now(timezone.utc).isoformat(),
              "tool": "ml/evaluation/gate_report.py",
              "test_set": {"path": str(a.test_dir), "sha256": sha, "images": len(items),
                           "classes": len({lbl for _, lbl in items}), "not_in_live_taxonomy": unknown},
              "live": evaluate(live, items), "candidate": evaluate(cand, items)}
    out = a.candidate / "report.json"
    out.write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("name", "test_set")}, indent=1))
    for side in ("live", "candidate"):
        r = report[side]
        print(f"{side:9} {r['model']}: top-1 {r['overall_top1']:.1%}  " +
              "  ".join(f"{g} {v:.1%}" for g, v in r["groups"].items()))
    print(f"\nWrote {out}. Upload the folder's four files in Admin → Models.")


if __name__ == "__main__":
    main()
