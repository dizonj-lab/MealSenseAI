"""Transfer-learning trainer (stages 5, 6, 8 of the training diagram) + evaluation (stage 9) + export.

- 5 Augmentation on the train split only: rotation, horizontal flip, random crop/zoom, brightness/contrast, colour jitter
- 6 Balancing strategy: weighted sampler | class-weighted loss | oversampling | none
- 8 ImageNet-pretrained EfficientNet (timm): train head with frozen backbone, then fine-tune the last blocks
- 9 Evaluation on the held-out test split (see evaluate.py)
- Export: ONNX + labels + model card to ml/models/food_classifier/, picked up by the app at startup.
Usage: python ml/training/train.py [--config ...] [--dataset datasets/processed/<name>-v<version>]
"""
import argparse
import csv
import json
import math
import shutil
import time
import urllib.request
from pathlib import Path

import numpy as np
import timm
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms as T

from common import ROOT, dataset_dir, load_config, resolve, write_json
from evaluate import evaluate_split

torch.manual_seed(42)


class ManifestDataset(Dataset):
    def __init__(self, root: Path, manifest: str, tf):
        self.root, self.tf = root, tf
        with open(root / manifest) as f:
            self.rows = [(r["path"], int(r["class_idx"])) for r in csv.DictReader(f)]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        p, y = self.rows[i]
        return self.tf(Image.open(self.root / p).convert("RGB")), y


def transforms(cfg: dict):
    t, a = cfg["train"], cfg["train"]["augmentation"]
    norm = T.Normalize(t["normalize"]["mean"], t["normalize"]["std"])
    size = t["image_size"]
    train = T.Compose([
        T.RandomResizedCrop(size, scale=tuple(a["random_resized_crop_scale"])),
        T.RandomRotation(a["rotation_deg"]),
        *([T.RandomHorizontalFlip()] if a["hflip"] else []),
        T.ColorJitter(a["brightness"], a["contrast"], a["saturation"], a["hue"]),
        T.ToTensor(), norm])
    evaltf = T.Compose([T.Resize(int(size * 256 / 224)), T.CenterCrop(size), T.ToTensor(), norm])
    return train, evaltf


def backbone(cfg: dict, n_classes: int) -> nn.Module:
    t = cfg["train"]
    cache = ROOT / "ml/models/backbones" / Path(t["backbone_weights_url"]).name
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        print(f"[model] downloading ImageNet weights -> {cache}")
        urllib.request.urlretrieve(t["backbone_weights_url"], cache)
    model = timm.create_model(t["backbone"], pretrained=True, num_classes=n_classes,
                              pretrained_cfg_overlay={"file": str(cache)})
    # timm's default head init (uniform ±1/sqrt(n_classes)) gives very large initial logits for few classes,
    # which a short frozen-backbone phase cannot undo; start the new head near zero instead.
    head = model.get_classifier()
    nn.init.normal_(head.weight, std=0.01)
    nn.init.zeros_(head.bias)
    return model


def set_trainable(model: nn.Module, phase: str) -> None:
    head = model.get_classifier()
    for p in model.parameters():
        p.requires_grad = phase == "finetune"
    if phase == "finetune":  # keep early blocks frozen: they hold generic ImageNet features
        for blk in list(model.blocks)[: max(0, len(model.blocks) - 3)]:
            for p in blk.parameters():
                p.requires_grad = False
        for p in model.conv_stem.parameters():
            p.requires_grad = False
    for p in head.parameters():
        p.requires_grad = True


def run_epoch(model, loader, loss_fn, opt=None):
    train = opt is not None
    model.train(train)
    tot, correct, n = 0.0, 0, 0
    with torch.set_grad_enabled(train):
        for x, y in loader:
            out = model(x)
            loss = loss_fn(out, y)
            if train:
                opt.zero_grad()
                loss.backward()
                opt.step()
            tot += loss.item() * len(y)
            correct += (out.argmax(1) == y).sum().item()
            n += len(y)
    return tot / n, correct / n


def macro_f1(model, loader, n_classes):
    model.eval()
    ys, ps = [], []
    with torch.no_grad():
        for x, y in loader:
            ps += model(x).argmax(1).tolist()
            ys += y.tolist()
    f1s = []
    for c in range(n_classes):
        tp = sum(1 for a, b in zip(ys, ps) if a == b == c)
        fp = sum(1 for a, b in zip(ys, ps) if b == c and a != c)
        fn = sum(1 for a, b in zip(ys, ps) if a == c and b != c)
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(f1s) / n_classes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "ml/training/config.yaml"))
    ap.add_argument("--dataset", default=None)
    a = ap.parse_args()
    cfg = load_config(a.config)
    t = cfg["train"]
    root = resolve(a.dataset) if a.dataset else dataset_dir(cfg)
    classes = json.loads((root / "classes.json").read_text())
    report = json.loads((root / "report.json").read_text())
    n = len(classes)
    tr_tf, ev_tf = transforms(cfg)
    train_ds = ManifestDataset(root, "train.csv", tr_tf)
    val_ds = ManifestDataset(root, "val.csv", ev_tf)

    # 6. balancing strategy
    counts = np.bincount([y for _, y in train_ds.rows], minlength=n)
    weights = torch.tensor(len(train_ds) / (n * np.maximum(counts, 1)), dtype=torch.float)
    sampler, loss_w = None, None
    if t["balancing"] == "weighted_sampler":
        sampler = WeightedRandomSampler([weights[y].item() for _, y in train_ds.rows], len(train_ds), replacement=True)
    elif t["balancing"] == "class_weights":
        loss_w = weights
    elif t["balancing"] == "oversample":
        mx = counts.max()
        train_ds.rows = [r for c in range(n) for r in
                         (lambda rs: (rs * math.ceil(mx / max(len(rs), 1)))[:mx])([r for r in train_ds.rows if r[1] == c])]
    train_dl = DataLoader(train_ds, t["batch_size"], shuffle=sampler is None, sampler=sampler, num_workers=t["num_workers"])
    val_dl = DataLoader(val_ds, t["batch_size"], num_workers=t["num_workers"])

    model = backbone(cfg, n)
    loss_fn = nn.CrossEntropyLoss(weight=loss_w, label_smoothing=t["label_smoothing"])
    run_dir = ROOT / "ml/runs" / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    history, best, best_f1, bad = [], run_dir / "best.pt", -1.0, 0
    for phase, epochs, lr in (("head", t["epochs_head"], t["lr_head"]), ("finetune", t["epochs_finetune"], t["lr_finetune"])):
        set_trainable(model, phase)
        params = [p for p in model.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=lr, weight_decay=t["weight_decay"])
        bad = 0
        for ep in range(epochs):
            t0 = time.time()
            tl, ta = run_epoch(model, train_dl, loss_fn, opt)
            vl, va = run_epoch(model, val_dl, loss_fn)
            vf1 = macro_f1(model, val_dl, n)
            history.append({"phase": phase, "epoch": ep + 1, "train_loss": round(tl, 4), "train_acc": round(ta, 4),
                            "val_loss": round(vl, 4), "val_acc": round(va, 4), "val_macro_f1": round(vf1, 4),
                            "seconds": round(time.time() - t0, 1)})
            print(history[-1])
            if vf1 > best_f1:
                best_f1, bad = vf1, 0
                torch.save(model.state_dict(), best)
            else:
                bad += 1
                if bad >= t["early_stopping_patience"]:
                    print("[train] early stopping")
                    break
    model.load_state_dict(torch.load(best))
    model.eval()

    # 9. evaluation on held-out test split
    metrics = evaluate_split(model, root, "test.csv", ev_tf, classes, run_dir)

    # export for the app (onnxruntime, no torch needed at inference)
    export = resolve(t["export_dir"])
    export.mkdir(parents=True, exist_ok=True)
    dummy = torch.randn(1, 3, t["image_size"], t["image_size"])
    torch.onnx.export(model, dummy, run_dir / "model.onnx", input_names=["input"], output_names=["logits"],
                      dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17, dynamo=False)
    card = {
        "name": f"MealSense-{t['backbone']}", "version": run_dir.name, "backbone": t["backbone"],
        "pretrained": "ImageNet-1k (timm)", "task": "food classification (fine-tuned)",
        "dataset": {"name": cfg["dataset"]["name"], "version": cfg["dataset"]["version"],
                    "hash": report["dataset_hash"], "sources": [s["name"] for s in report["sources"] if s["status"] == "ok"],
                    "split_sizes": report["split_sizes"]},
        "input": {"size": t["image_size"], "resize": int(t["image_size"] * 256 / 224), "layout": "NCHW", **t["normalize"]},
        "classes": classes, "training": {k: t[k] for k in ("balancing", "epochs_head", "epochs_finetune", "lr_head",
                                                            "lr_finetune", "label_smoothing", "augmentation")},
        "history": history, "test_metrics": metrics, "score_calibrated": False,
    }
    write_json(run_dir / "model_card.json", card)
    for f in ("model.onnx", "model_card.json", "confusion_matrix.png"):
        shutil.copy(run_dir / f, export / f)
    print(f"[export] {export}  test acc={metrics['accuracy']:.3f} macro-F1={metrics['macro_f1']:.3f}")


if __name__ == "__main__":
    main()
