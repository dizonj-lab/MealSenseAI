"""Class-agnostic food region proposals (no training, NumPy + Pillow only).

Pattern-recognition pipeline used to split a plate into candidate food items before EXP-002 classifies each crop:
  1. downsample; features = hue (as cos/sin weighted by saturation), saturation, value, and a little x/y position;
     clusters with near-identical colour are merged afterwards so uniform surfaces stay whole
  2. k-means colour clustering (deterministic initialisation)
  3. background removal: near-white / near-black low-saturation pixels (plate, cutlery, shadows) and clusters that
     dominate the image border (table, placemat)
  4. connected components per cluster, small-component removal, bounding boxes, IoU/containment merging
The output regions are *proposals*; the classifier decides what (if anything) each region is, and weak regions are
returned as unidentified items for the user to name.
"""
from collections import deque

import numpy as np
from PIL import Image

GRID = 112            # working resolution (longer side)
K = 8                 # colour clusters
MIN_AREA = 0.012      # min region area as a fraction of the image
MAX_REGIONS = 12


def _kmeans(X: np.ndarray, k: int, iters: int = 12) -> np.ndarray:
    # deterministic init: k evenly spaced samples in value order
    order = np.argsort(X[:, 3])
    C = X[order[np.linspace(0, len(X) - 1, k).astype(int)]].copy()
    for _ in range(iters):
        d = ((X[:, None, :] - C[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = lab == j
            if m.any():
                C[j] = X[m].mean(0)
    return lab


def _components(mask: np.ndarray) -> list[np.ndarray]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        q, pts = deque([(y0, x0)]), []
        seen[y0, x0] = True
        while q:
            y, x = q.popleft()
            pts.append((y, x))
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        comps.append(np.array(pts))
    return comps


def _box_iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    return inter / (area(a) + area(b) - inter + 1e-9), inter / (min(area(a), area(b)) + 1e-9)


def propose(img: Image.Image) -> dict:
    """Return {"regions": [{bbox, area_frac, mask_small}], "plate_area_frac": float|None}."""
    s = GRID / max(img.size)
    small = img.resize((max(8, round(img.width * s)), max(8, round(img.height * s))), Image.BILINEAR)
    hsv = np.asarray(small.convert("HSV"), dtype=np.float32) / 255.0
    h, w = hsv.shape[:2]
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    yy, xx = np.mgrid[0:h, 0:w]
    feats = np.stack([np.cos(2 * np.pi * H) * S, np.sin(2 * np.pi * H) * S, S, V,
                      0.25 * xx / w, 0.25 * yy / h], -1).reshape(-1, 6)
    lab = _kmeans(feats, K)
    # clusters that differ only by position (same colour) are one surface: merge them (uniform areas stay whole)
    col = feats[:, :4]
    cent = {j: col[lab == j].mean(0) for j in np.unique(lab)}
    keys = sorted(cent)
    parent = {j: j for j in keys}
    find = lambda j: j if parent[j] == j else find(parent[j])
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if np.abs(cent[a] - cent[b]).max() < 0.06:
                parent[find(b)] = find(a)
    lab = np.vectorize(find)(lab).reshape(h, w)

    background = ((S < 0.13) & (V > 0.70)) | (V < 0.13)       # white plate / dark gaps
    plate_frac = float(((S < 0.13) & (V > 0.70)).mean())
    border = np.zeros((h, w), bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    for j in np.unique(lab):
        m = lab == j
        if m.any() and (m & border).sum() / max(border.sum(), 1) > 0.25 and m.mean() > 0.15:
            background |= m                                     # table / placemat cluster

    boxes = []
    for j in np.unique(lab):
        m = (lab == j) & ~background
        for pts in _components(m):
            if len(pts) < MIN_AREA * h * w:
                continue
            y1, x1 = pts.min(0)
            y2, x2 = pts.max(0) + 1
            boxes.append({"box": [x1, y1, x2, y2], "pix": len(pts), "pts": pts})
    # merge regions that substantially overlap or are contained in each other (one food split into colours)
    boxes.sort(key=lambda b: -b["pix"])
    merged = []
    for b in boxes:
        for m in merged:
            iou, contain = _box_iou(b["box"], m["box"])
            if iou > 0.45 or contain > 0.80:
                m["box"] = [min(m["box"][0], b["box"][0]), min(m["box"][1], b["box"][1]),
                            max(m["box"][2], b["box"][2]), max(m["box"][3], b["box"][3])]
                m["pix"] += b["pix"]
                m["pts"] = np.concatenate([m["pts"], b["pts"]])
                break
        else:
            merged.append(b)
    regions = []
    for m in merged[:MAX_REGIONS]:
        x1, y1, x2, y2 = m["box"]
        mask = np.zeros((h, w), bool)
        mask[m["pts"][:, 0], m["pts"][:, 1]] = True
        regions.append({"bbox": {"x": x1 / w, "y": y1 / h, "w": (x2 - x1) / w, "h": (y2 - y1) / h},
                        "area_frac": round(m["pix"] / (h * w), 4), "mask_small": mask})
    return {"regions": regions, "plate_area_frac": round(plate_frac, 4) if plate_frac > 0.08 else None}
