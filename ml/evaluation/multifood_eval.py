"""Multi-food detection + per-item classification benchmark on labelled images.

Without a labelled multi-food photo set, this builds SYNTHETIC plates: 2–3 circular crops of held-out Food-101 test
images placed on a plate over a table colour, so every item has a known box and class. It measures the app's real
pipeline (vision.analyze): class-agnostic detection (IoU ≥ 0.5), per-item top-1/top-3 classification, and latency.
Synthetic composites are easier than real meals (clean edges, no overlap, no sauces); treat results as a lower bound
on difficulty, not as real-world accuracy. A labelled real set can be scored with --labels (JSON:
[{"image": path, "items": [{"label": str, "bbox": {x,y,w,h normalised}}]}]).
Usage: python ml/evaluation/multifood_eval.py <food101_test_root> [--plates 60] [--out test-results/multifood]
"""
import argparse
import json
import random
import statistics
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.services import vision  # noqa: E402

TABLES = [(139, 94, 60), (60, 60, 64), (200, 190, 170), (90, 120, 150), (40, 80, 50)]


def make_plate(rng, pool, n, path):
    W, H = 1024, 768
    img = Image.new("RGB", (W, H), rng.choice(TABLES))
    ImageDraw.Draw(img).ellipse((60, 20, W - 60, H - 20), fill=(244, 244, 240))
    slots = rng.sample([(250, 230), (560, 200), (760, 380), (330, 520), (600, 560)], n)
    items = []
    for (cx, cy), (label, p) in zip(slots, rng.sample(pool, n)):
        r = rng.randint(115, 150)
        src = Image.open(p).convert("RGB")
        s = min(src.size)
        src = src.crop(((src.width - s) // 2, (src.height - s) // 2, (src.width + s) // 2, (src.height + s) // 2)).resize((2 * r, 2 * r))
        mask = Image.new("L", (2 * r, 2 * r), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
        img.paste(src, (cx - r, cy - r), mask)
        items.append({"label": label, "bbox": {"x": (cx - r) / W, "y": (cy - r) / H, "w": 2 * r / W, "h": 2 * r / H}})
    img.save(path, quality=92)
    return {"image": str(path), "items": items}


def iou(a, b):
    x1, y1 = max(a["x"], b["x"]), max(a["y"], b["y"])
    x2, y2 = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / (a["w"] * a["h"] + b["w"] * b["h"] - inter + 1e-9)


def ap50(dets, n_gt):
    """VOC-style all-point AP over (score, is_tp) detections."""
    dets = sorted(dets, key=lambda d: -d[0])
    tp = fp = 0
    prec, rec = [], []
    for _, ok in dets:
        tp, fp = tp + ok, fp + (not ok)
        prec.append(tp / (tp + fp))
        rec.append(tp / n_gt)
    ap, prev_r = 0.0, 0.0
    for i, r in enumerate(rec):
        ap += (r - prev_r) * max(prec[i:])
        prev_r = r
    return ap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?")
    ap.add_argument("--labels")
    ap.add_argument("--plates", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="test-results/multifood")
    ap.add_argument("--single", help="folder per class of single-dish photos: measures extra items shown per photo")
    ap.add_argument("--single-per-class", type=int, default=25)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    vision.warmup()
    if a.labels:
        samples, kind = json.loads(Path(a.labels).read_text()), "labelled"
    else:
        rng = random.Random(a.seed)
        pool = [(d.name.replace("_", " "), p) for d in sorted(Path(a.root).iterdir()) if d.is_dir() for p in sorted(d.glob("*.jpg"))]
        tmp = Path(tempfile.mkdtemp())
        samples = [make_plate(rng, pool, rng.choice([2, 3]), tmp / f"plate_{i:03d}.jpg") for i in range(a.plates)]
        kind = "synthetic composites of Food-101 test images"
    dets, n_gt, tp, fp, fn = [], 0, 0, 0, 0
    top1 = top3 = 0
    conf, lat, per_class = Counter(), [], Counter()
    rows = []
    for s in samples:
        t0 = time.perf_counter()
        r = vision.analyze(s["image"], "top")
        lat.append((time.perf_counter() - t0) * 1000)
        preds = [p for p in r["items"] if p["kind"] in ("food", "unknown")]  # what the user sees as items
        gts, used = s["items"], set()
        n_gt += len(gts)
        for p in sorted(preds, key=lambda p: -p["score"]):
            pb = p["bbox"] or {"x": 0, "y": 0, "w": 1, "h": 1}  # whole-photo item
            best = max(((iou(pb, g["bbox"]), j) for j, g in enumerate(gts) if j not in used), default=(0, -1))
            ok = best[0] >= 0.5
            dets.append((p["score"], ok))
            if ok:
                used.add(best[1])
                g = gts[best[1]]["label"]
                cands = [c["label"] for c in p["candidates"]]
                top1 += cands[:1] == [g]
                top3 += g in cands[:3]
                pl = p["model_label"] if p["kind"] == "food" else "(unidentified)"
                conf[(g, pl)] += 1
                per_class[g] += 1
        tp += len(used)
        fp += len(preds) - len(used)
        fn += len(gts) - len(used)
        rows.append({"image": Path(s["image"]).name, "gt": len(gts), "pred": len(preds), "tp": len(used)})
    classes = sorted({g for g, _ in conf})
    prf = {}
    for c in classes:
        ctp = conf[(c, c)]
        cfp = sum(v for (g, p), v in conf.items() if p == c and g != c)
        cfn = sum(v for (g, p), v in conf.items() if g == c and p != c)
        pr, rc = ctp / (ctp + cfp) if ctp + cfp else 0.0, ctp / (ctp + cfn) if ctp + cfn else 0.0
        prf[c] = {"precision": round(pr, 3), "recall": round(rc, 3), "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0, "support": per_class[c]}
    res = {
        "dataset": kind, "images": len(samples), "gt_items": n_gt,
        "detection": {"tp": tp, "fp": fp, "fn": fn, "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                      "recall": round(tp / n_gt, 3), "ap50_class_agnostic": round(ap50(dets, n_gt), 3),
                      "note": "IoU ≥ 0.5; detections = items shown to the user (named + unidentified); score = raw classifier softmax"},
        "classification_on_matched": {"n": tp, "top1": round(top1 / tp, 3) if tp else None, "top3": round(top3 / tp, 3) if tp else None,
                                      "per_class": prf, "macro_f1": round(statistics.mean(v["f1"] for v in prf.values()), 3) if prf else None,
                                      "confusion": {f"{g} -> {p}": v for (g, p), v in sorted(conf.items())}},
        "latency_ms": {"mean": round(statistics.mean(lat), 1), "p50": round(statistics.median(lat), 1),
                       "p95": round(sorted(lat)[int(0.95 * (len(lat) - 1))], 1), "device": vision.status().get("device", "cpu")},
        "per_image": rows,
    }
    if a.single:
        sd = {"photos": 0, "exactly_one_item": 0, "correct_single_item": 0, "extra_items_shown": 0}
        for d in sorted(Path(a.single).iterdir()):
            for p in sorted(d.glob("*.jpg"))[:a.single_per_class]:
                shown = [i for i in vision.analyze(str(p), "top")["items"] if i["kind"] in ("food", "unknown")]
                sd["photos"] += 1
                sd["exactly_one_item"] += len(shown) == 1
                sd["correct_single_item"] += len(shown) == 1 and shown[0]["model_label"] == d.name.replace("_", " ")
                sd["extra_items_shown"] += max(len(shown) - 1, 0)
        sd["mean_extra_items_per_photo"] = round(sd["extra_items_shown"] / sd["photos"], 2)
        res["single_dish"] = sd
    (out / "multifood_metrics.json").write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "per_image"}, indent=2))


if __name__ == "__main__":
    main()
