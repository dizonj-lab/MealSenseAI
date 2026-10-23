"""Dataset pre-processing pipeline (stages 1-7 and 10 of the training diagram).

1 Data sources        - folder-per-class sources from config.yaml (Food-101, FoodSG-233, own images)
2 Ingest & validate   - register source/version, integrity check, format filter, exact + near duplicates
3 Label harmonisation - normalise names, map equivalents, drop ambiguous, merge; select MVP classes
4 Pre-processing      - EXIF orientation, RGB, border trim, resize short side (aspect kept)
6 Balancing analysis  - class distribution, imbalance ratio, class weights (strategy applied in train.py)
7 Split               - stratified 70/15/15, seeded
10 Training-ready     - processed images, manifests, class list + mapping, configs, dataset hash

Augmentation (5) is applied on the fly to the train split only, in train.py.
Usage: python ml/training/prepare_dataset.py [--config ml/training/config.yaml] [--source name=path ...]
"""
import argparse
import csv
import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError

from common import ROOT, dataset_dir, load_config, norm_label, resolve, sha1_file, write_json

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def dhash(img: Image.Image, size: int = 8) -> int:
    g = img.convert("L").resize((size + 1, size), Image.BILINEAR)
    px = list(g.getdata())
    bits = 0
    for r in range(size):
        for c in range(size):
            bits = (bits << 1) | (px[r * (size + 1) + c] > px[r * (size + 1) + c + 1])
    return bits


def trim_borders(img: Image.Image, tol: int = 12) -> Image.Image:
    """Remove uniform borders (letterboxing / scan edges) if they are < 25% of the image."""
    bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
    diff = ImageChops.add(ImageChops.difference(img, bg), ImageChops.difference(img, bg), 2.0, -tol)
    box = diff.getbbox()
    if box and (box[2] - box[0]) * (box[3] - box[1]) > 0.75 * img.width * img.height:
        return img.crop(box)
    return img


def ingest(sources: list[dict]) -> tuple[list[dict], list[dict]]:
    """Stage 1-2a: register sources and list candidate files (raw data is never modified)."""
    registry, items = [], []
    for s in sources:
        root = resolve(s["path"])
        if not root.exists():
            registry.append({**s, "status": "missing", "files": 0})
            print(f"[ingest] skip {s['name']}: {root} not found")
            continue
        files = sorted(p for p in root.rglob("*") if p.suffix.lower() in EXTS)
        listing = hashlib.sha256("\n".join(str(p.relative_to(root)) for p in files).encode()).hexdigest()[:16]
        registry.append({**s, "status": "ok", "files": len(files), "listing_hash": listing})
        for p in files:
            items.append({"source": s["name"], "path": p, "raw_label": p.parent.name})
        print(f"[ingest] {s['name']}: {len(files)} files")
    return registry, items


class NearDupIndex:
    """dHash index: with Hamming distance <= k, at least one of k+1 bit-bands matches exactly (pigeonhole)."""
    def __init__(self, k: int):
        self.k, self.bands = k, [defaultdict(list) for _ in range(k + 1)]
        self.width = -(-64 // (k + 1))

    def _keys(self, h: int):
        return [(h >> (i * self.width)) & ((1 << self.width) - 1) for i in range(self.k + 1)]

    def seen(self, h: int) -> bool:
        for band, key in zip(self.bands, self._keys(h)):
            if any(bin(h ^ o).count("1") <= self.k for o in band[key]):
                return True
        return False

    def add(self, h: int) -> None:
        for band, key in zip(self.bands, self._keys(h)):
            band[key].append(h)


def validate(items: list[dict], cfg: dict) -> tuple[list[dict], Counter]:
    """Stage 2b: integrity, format, size, missing labels, exact and near duplicates."""
    d = cfg["dataset"]
    issues, ok, seen_sha = Counter(), [], {}
    near = NearDupIndex(d["near_duplicate_hamming"]) if d["near_duplicate_hamming"] else None
    for it in items:
        if not it["raw_label"] or it["raw_label"] == it["path"].anchor:
            issues["missing_label"] += 1
            continue
        try:
            with Image.open(it["path"]) as im:
                im.verify()
            with Image.open(it["path"]) as im:
                fmt = im.format
                im.load()
                size = im.size
                dh = dhash(im) if d["near_duplicate_hamming"] else None
        except (UnidentifiedImageError, OSError, SyntaxError):
            issues["corrupt"] += 1
            continue
        if fmt not in d["allowed_formats"] and fmt != "HEIF":
            issues["invalid_format"] += 1
            continue
        if min(size) < d["min_side_px"]:
            issues["too_small"] += 1
            continue
        sha = sha1_file(it["path"])
        if sha in seen_sha:
            issues["exact_duplicate"] += 1
            continue
        if near and near.seen(dh):
            issues["near_duplicate"] += 1
            continue
        seen_sha[sha] = True
        if near:
            near.add(dh)
        ok.append({**it, "sha1": sha, "size": size})
    return ok, issues


def harmonise(items: list[dict], cmap: dict, cfg: dict) -> tuple[list[dict], list[str], dict]:
    """Stage 3: standardise labels and select MVP classes."""
    aliases, remove, classes = cmap["aliases"], set(cmap["remove"]), cmap["classes"]
    report = {"removed_ambiguous": 0, "renamed": Counter()}
    out = []
    for it in items:
        lab = norm_label(it["raw_label"])
        if lab in remove:
            report["removed_ambiguous"] += 1
            continue
        canon = aliases.get(lab, lab)
        if canon != lab:
            report["renamed"][f"{lab}->{canon}"] += 1
        out.append({**it, "label": canon})
    counts = Counter(i["label"] for i in out)
    mvp = cfg["dataset"]["mvp"]
    eligible = [c for c, n in counts.items() if n >= mvp["min_images_per_class"]]
    eligible.sort(key=lambda c: (classes.get(c, {}).get("priority", 9), -counts[c], c))
    selected = sorted(eligible[: mvp["max_classes"]])
    report["dropped_classes"] = {c: counts[c] for c in counts if c not in selected}
    report["renamed"] = dict(report["renamed"])
    return [i for i in out if i["label"] in selected], selected, report


def preprocess(items: list[dict], out_dir: Path, cfg: dict) -> None:
    """Stage 4: write cleaned, resized copies (originals untouched)."""
    pp = cfg["dataset"]["preprocess"]
    for it in items:
        with Image.open(it["path"]) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            if pp["trim_borders"]:
                im = trim_borders(im)
            s = pp["short_side_px"] / min(im.size)
            if s < 1:
                im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            dst = out_dir / "images" / it["label"] / f"{it['source']}_{it['sha1'][:16]}.jpg"
            dst.parent.mkdir(parents=True, exist_ok=True)
            im.save(dst, "JPEG", quality=pp["jpeg_quality"])
            it["processed"] = str(dst.relative_to(out_dir))


def split(items: list[dict], cfg: dict) -> dict[str, list[dict]]:
    """Stage 7: stratified split per class."""
    sp = cfg["dataset"]["split"]
    rng = random.Random(sp["seed"])
    by = defaultdict(list)
    for it in items:
        by[it["label"]].append(it)
    out = {"train": [], "val": [], "test": []}
    for lab in sorted(by):
        group = sorted(by[lab], key=lambda i: i["sha1"])
        rng.shuffle(group)
        n = len(group)
        n_test = max(1, round(n * sp["test"]))
        n_val = max(1, round(n * sp["val"]))
        out["test"] += group[:n_test]
        out["val"] += group[n_test:n_test + n_val]
        out["train"] += group[n_test + n_val:]
    return out


def balance_report(train: list[dict], classes: list[str]) -> dict:
    """Stage 6: distribution analysis and inverse-frequency class weights."""
    c = Counter(i["label"] for i in train)
    n, k = sum(c.values()), len(classes)
    weights = {lab: round(n / (k * c[lab]), 4) for lab in classes}
    return {"train_counts": {lab: c[lab] for lab in classes},
            "imbalance_ratio": round(max(c.values()) / min(c.values()), 3), "class_weights": weights}


def plot_distribution(counts: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labs = list(counts)
    fig, ax = plt.subplots(figsize=(max(6, len(labs) * 0.45), 3.5))
    ax.bar(labs, [counts[x] for x in labs], color="#14b8a6")
    ax.set_ylabel("train images")
    ax.set_title("Class distribution (train split)")
    plt.xticks(rotation=60, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "ml/training/config.yaml"))
    ap.add_argument("--source", action="append", default=[], help="override sources: name=path")
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.source:
        cfg["dataset"]["sources"] = [{"name": s.split("=", 1)[0], "path": s.split("=", 1)[1], "version": "local"} for s in a.source]
    cmap = json.loads(resolve(cfg["dataset"]["class_map"]).read_text())
    out = dataset_dir(cfg)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    registry, items = ingest(cfg["dataset"]["sources"])
    valid, issues = validate(items, cfg)
    print(f"[validate] {len(valid)}/{len(items)} valid; issues: {dict(issues)}")
    kept, classes, hreport = harmonise(valid, cmap, cfg)
    if len(classes) < 2:
        raise SystemExit(f"Need at least 2 classes with >= {cfg['dataset']['mvp']['min_images_per_class']} images; got {classes}")
    print(f"[harmonise] {len(classes)} MVP classes, {len(kept)} images")
    preprocess(kept, out, cfg)
    splits = split(kept, cfg)
    bal = balance_report(splits["train"], classes)

    idx = {c: i for i, c in enumerate(classes)}
    for name, rows in splits.items():
        with open(out / f"{name}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "label", "class_idx", "source", "sha1"])
            for r in sorted(rows, key=lambda r: r["processed"]):
                w.writerow([r["processed"], r["label"], idx[r["label"]], r["source"], r["sha1"]])
    h = hashlib.sha256()
    for name in ("train", "val", "test"):
        h.update((out / f"{name}.csv").read_bytes())
    dataset_hash = h.hexdigest()

    write_json(out / "classes.json", [{"idx": idx[c], "name": c,
                                        "nutrition_key": cmap["classes"].get(c, {}).get("nutrition_key")} for c in classes])
    write_json(out / "report.json", {
        "created_at": datetime.now(timezone.utc).isoformat(), "dataset_hash": dataset_hash,
        "sources": registry, "validation_issues": dict(issues), "valid_images": len(valid),
        "harmonisation": hreport, "classes": classes,
        "split_sizes": {k: len(v) for k, v in splits.items()}, "balancing": bal,
        "preprocessing": cfg["dataset"]["preprocess"], "augmentation": cfg["train"]["augmentation"],
        "normalize": cfg["train"]["normalize"],
    })
    plot_distribution(bal["train_counts"], out / "class_distribution.png")
    print(f"[done] {out}  hash={dataset_hash[:12]}  splits={ {k: len(v) for k, v in splits.items()} }")


if __name__ == "__main__":
    main()
