"""Embedding analysis of the EXP-002 classifier: PCA, clustering and k-nearest neighbours (read-only).

Run on the training machine (the test images must be on disk), in the training environment (PyTorch, torchvision):

    python ml/evaluation/embedding_eval.py \\
        --predictions ~/development/mealsenseai/evidence/EXP-002_FineTuning/evaluation/predictions.csv \\
        --model ml/models/exp002/best_model.pth --classes ml/models/exp002/class_mapping.json \\
        --per-class 40 --out embedding_eval.json

For a stratified sample of the held-out test set (up to --per-class images per class) it extracts the 1280-value
feature vector the classifier's head sees (EfficientNet-B0 global average pool), L2-normalised, and measures:
  * PCA: explained variance, and k-NN accuracy after reducing 1280 dimensions to 16-256 (efficiency vs accuracy);
  * k-nearest neighbours (cosine, similarity-weighted vote, 5-fold stratified within the sample) for k = 1, 5, 10,
    next to the trained linear head on the same images;
  * clustering: k-means with k = number of classes, compared with the true labels (NMI, ARI, purity), and the
    silhouette of the true labels;
  * 2-D PCA coordinates for a few classes, for a scatter plot.
NumPy only for the analysis; no file is written except --out.
"""
import argparse
import csv
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

SHOW = ["chicken rice", "nasi lemak", "laksa", "kaya toast", "pizza", "sushi", "steak", "filet mignon", "dumpling",
        "xiao long bao", "edamame", "bee hoon"]


def features(model, paths, device, bs=64):
    import torch
    from PIL import Image
    from torchvision import transforms
    tf = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
                             transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    feats, logits = [], []
    with torch.no_grad():
        for i in range(0, len(paths), bs):
            x = torch.stack([tf(Image.open(p).convert("RGB")) for p in paths[i:i + bs]]).to(device)
            f = torch.flatten(model.avgpool(model.features(x)), 1)
            feats.append(f.cpu().numpy()); logits.append(model.classifier(f).cpu().numpy())
            print(f"\r{min(i + bs, len(paths))}/{len(paths)}", end="", flush=True)
    print()
    return np.vstack(feats).astype(np.float32), np.vstack(logits)


def l2(x):
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)


def folds(y, k=5, seed=42):
    rng = random.Random(seed); f = np.zeros(len(y), int)
    for c in np.unique(y):
        idx = list(np.where(y == c)[0]); rng.shuffle(idx)
        for j, i in enumerate(idx): f[i] = j % k
    return f


def knn_accuracy(X, y, ks=(1, 5, 10), nfold=5):
    X = l2(X); f = folds(y, nfold); hits = {k: 0 for k in ks}; t = 0.0
    for fo in range(nfold):
        q, g = f == fo, f != fo
        t0 = time.perf_counter(); S = X[q] @ X[g].T; t += time.perf_counter() - t0
        order = np.argsort(-S, axis=1)[:, :max(ks)]; yg = y[g]
        for k in ks:
            for row, o in enumerate(order[:, :k]):
                votes = defaultdict(float)
                for j in o: votes[yg[j]] += S[row, j]
                hits[k] += max(votes, key=votes.get) == y[q][row]
    return {f"k={k}": round(hits[k] / len(y), 4) for k in ks}, round(t / len(y) * 1000, 4)


def kmeans(X, k, iters=25, seed=42):
    rng = np.random.default_rng(seed); X = l2(X)
    C = [X[rng.integers(len(X))]]
    d = 1 - X @ C[0]
    for _ in range(1, k):                                   # k-means++ (cosine distance)
        C.append(X[rng.choice(len(X), p=np.maximum(d, 0) / np.maximum(d, 0).sum())]); d = np.minimum(d, 1 - X @ C[-1])
    C = np.vstack(C)
    for _ in range(iters):
        lab = (X @ C.T).argmax(1)
        C = l2(np.vstack([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)]))
    return lab


def nmi_ari(a, b):
    n = len(a); ua, ia = np.unique(a, return_inverse=True); ub, ib = np.unique(b, return_inverse=True)
    M = np.zeros((len(ua), len(ub))); np.add.at(M, (ia, ib), 1)
    pa, pb, p = M.sum(1) / n, M.sum(0) / n, M / n
    nz = p > 0
    mi = (p[nz] * np.log(p[nz] / np.outer(pa, pb)[nz])).sum()
    h = lambda q: -(q[q > 0] * np.log(q[q > 0])).sum()
    nmi = 2 * mi / (h(pa) + h(pb))
    c2 = lambda x: x * (x - 1) / 2
    sij, sa, sb = c2(M).sum(), c2(M.sum(1)).sum(), c2(M.sum(0)).sum()
    exp = sa * sb / c2(n)
    ari = (sij - exp) / (0.5 * (sa + sb) - exp)
    return round(float(nmi), 4), round(float(ari), 4), round(float(M.max(0).sum() / n), 4)


def silhouette(X, y, n=3000, seed=42):
    rng = np.random.default_rng(seed); i = rng.choice(len(X), min(n, len(X)), replace=False)
    X, y = l2(X[i]), y[i]; D = 1 - X @ X.T
    cls, yi = np.unique(y, return_inverse=True)
    Y = np.zeros((len(y), len(cls))); Y[np.arange(len(y)), yi] = 1
    sums, cnt = D @ Y, Y.sum(0)
    own = cnt[yi] - 1
    a = sums[np.arange(len(y)), yi] / np.maximum(own, 1)
    other = sums / cnt; other[np.arange(len(y)), yi] = np.inf
    b = other.min(1); ok = own > 0
    return round(float(np.mean(((b - a) / np.maximum(a, b))[ok])), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True); ap.add_argument("--model", required=True)
    ap.add_argument("--classes", required=True); ap.add_argument("--per-class", type=int, default=40)
    ap.add_argument("--out", default="embedding_eval.json"); a = ap.parse_args()
    names = {v: k for k, v in json.loads(Path(a.classes).read_text()).items()}
    rows = [r for r in csv.DictReader(open(Path(a.predictions).expanduser())) if r.get("split", "test") == "test"]
    by = defaultdict(list)
    for r in rows: by[int(r["true_label_id"])].append(r)
    rng = random.Random(42); sample = []
    for c in sorted(by):
        rr = by[c][:]; rng.shuffle(rr); sample += rr[:a.per_class]
    paths = [r["image_path"] for r in sample]; y = np.array([int(r["true_label_id"]) for r in sample])
    import torch
    from torch import nn
    from torchvision import models
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(a.model, map_location="cpu", weights_only=True)
    m = models.efficientnet_b0(weights=None); m.classifier[1] = nn.Linear(1280, len(names))
    m.load_state_dict(ck["model_state_dict"]); m.eval().to(device)
    t0 = time.time(); X, logits = features(m, paths, device); t_feat = time.time() - t0
    out = {"images": len(y), "classes": int(len(np.unique(y))), "per_class_max": a.per_class, "device": device,
           "feature_dim": int(X.shape[1]), "feature_seconds": round(t_feat, 1),
           "linear_head_top1": round(float((logits.argmax(1) == y).mean()), 4)}
    knn, ms = knn_accuracy(X, y); out["knn_cosine_1280d"] = knn; out["knn_query_ms_1280d"] = ms
    Xc = l2(X); mu = Xc.mean(0); U, Sv, Vt = np.linalg.svd(Xc - mu, full_matrices=False)
    ev = (Sv ** 2) / (Sv ** 2).sum(); cum = np.cumsum(ev)
    out["pca_explained_variance"] = {str(d): round(float(cum[d - 1]), 4) for d in (2, 10, 16, 32, 64, 128, 256)}
    out["pca_components_for_90pct"] = int(np.searchsorted(cum, 0.90) + 1)
    out["knn_after_pca"] = {}
    for d in (16, 32, 64, 128, 256):
        Z = (Xc - mu) @ Vt[:d].T
        acc, qms = knn_accuracy(Z, y, ks=(5,))
        out["knn_after_pca"][str(d)] = {"k=5": acc["k=5"], "query_ms": qms}
    lab = kmeans(X, out["classes"]); nmi, ari, pur = nmi_ari(y, lab)
    out["kmeans"] = {"k": out["classes"], "nmi": nmi, "ari": ari, "purity": pur}
    out["silhouette_true_labels"] = silhouette(X, y)
    show = [c for c, n in names.items() if n in SHOW]
    sel = np.isin(y, show); Zs = l2(X[sel]); Zs = Zs - Zs.mean(0)
    _, _, V2 = np.linalg.svd(Zs, full_matrices=False); P = Zs @ V2[:2].T
    out["pca2d_selected"] = [{"label": names[int(c)], "x": round(float(p[0]), 4), "y": round(float(p[1]), 4)} for c, p in zip(y[sel], P)]
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "pca2d_selected"}, indent=1))


if __name__ == "__main__":
    main()
