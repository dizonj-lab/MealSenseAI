"""Stages 3-4 of the inference pipeline: food instance detection and food classification.

Stage 4 — classification (primary): MealSenseAI EXP-002, EfficientNet-B0 fine-tuned on Food-101 + FoodSG,
  320 canonical classes. Runs as ONNX (exported from best_model.pth; parity evidence in
  ml/models/exp002/evidence/onnx_parity.json) with the exact evaluation preprocessing (services/preprocess.py).
  The whole photo is classified (as in evaluation) and the top-3 candidates are returned for confirmation.
Stage 3 — detection (supporting): YOLO11n-seg (COCO, ONNX) outlines food items and dish containers. Crops of
  detected items are classified too, so a second, different dish in the same photo can be proposed.
Inference device: CUDA when onnxruntime exposes it (GPU image) and INFERENCE_DEVICE allows it, else CPU.
Models are loaded once at startup. Scores are raw softmax outputs, NOT calibrated probabilities.
"""
import ast
import json
import logging
import os
import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from app.core.config import settings
from app.services.preprocess import to_input

log = logging.getLogger(__name__)

COCO_FOOD = {"banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake"}
COCO_DISH_CONTAINERS = {"bowl", "cup", "wine glass"}
COCO_REFERENCE = {"dining table", "bowl", "fork", "knife", "spoon"}
DET_MIN = 0.30
# Defaults of the admin settings vision.* (services/tuning.py); analyze() reads the live values.
UNKNOWN_MIN = 0.45       # a region whose top-1 is below this is shown as "unidentified" instead of forcing a class
MIN_ITEM_AREA = 0.03     # smaller segmentation regions are only offered as possible items (noise / garnish)
PROPOSE_MIN = 0.20       # below this the photo's top-1 is not added automatically; the user picks from the top-3
MAX_UNKNOWN = 3          # unidentified regions listed for naming; further weak regions become suggestions
WHOLE_DISH = 0.70        # whole-photo top-1 at/above this = single-dish photo (47% of single dishes, 2.5% of mixed plates)
CROP_MIN = 0.60          # a crop proposes an extra item only when confident and different from the photo's top-3
PALETTE = [(20, 184, 166), (14, 165, 233), (245, 158, 11), (16, 185, 129), (139, 92, 246), (244, 63, 94)]

_lock = threading.RLock()
_state: dict = {"loaded": False}
# The live classifier: the built-in EXP-002, or a model package an admin promoted at the model gate
# (services/gate.py). A shadow model runs beside it on the same crops, for comparison only.
_choice: dict = {"dir": None, "label": None, "shadow": None}
REQUIRED_CARD = ("name", "version", "num_classes", "classes")


def load_classifier(cdir: Path, opts=None, prov=None) -> dict:
    """Open a classifier package (model.onnx, class_mapping.json, model_card.json) and check that it is complete
    and self-consistent. Raises ValueError with a readable reason otherwise."""
    import onnxruntime as ort
    if opts is None:
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
    for f in ("model.onnx", "class_mapping.json", "model_card.json"):
        if not (cdir / f).is_file():
            raise ValueError(f"{f} is missing")
    card = json.loads((cdir / "model_card.json").read_text())
    missing = [k for k in REQUIRED_CARD if k not in card]
    if missing:
        raise ValueError(f"model_card.json lacks {', '.join(missing)}")
    taxonomy = json.loads((cdir / "class_mapping.json").read_text())
    sess = ort.InferenceSession(str(cdir / "model.onnx"), opts, providers=prov or _providers())
    n_out = sess.get_outputs()[0].shape[-1]
    if n_out != len(taxonomy) or sorted(taxonomy.values()) != list(range(len(taxonomy))) or card["num_classes"] != len(taxonomy):
        raise ValueError(f"taxonomy mismatch: model outputs {n_out}, taxonomy has {len(taxonomy)} classes, "
                         f"card says {card['num_classes']}")
    names = [None] * len(taxonomy)
    for name, i in taxonomy.items():
        names[i] = name
    by_id = {c["id"]: c for c in card["classes"]}
    return {"session": sess, "card": card, "names": names, "map": by_id, "dir": str(cdir)}


def use_model(cdir: Path | None, label: str | None) -> None:
    """Switch the live classifier (None = the built-in model). Takes effect for the next analysis."""
    with _lock:
        _choice.update(dir=cdir, label=label)
        _state["loaded"] = False


def set_shadow(cdir: Path | None, name: str | None) -> str | None:
    """Run a candidate beside the live model (None stops it). Returns an error message, or None."""
    with _lock:
        if cdir is None:
            _choice["shadow"] = None
            return None
        try:
            _choice["shadow"] = {**load_classifier(cdir), "name": name}
        except Exception as e:   # noqa: BLE001 - reported to the admin
            _choice["shadow"] = None
            return f"{type(e).__name__}: {e}"
    return None


def shadow_name() -> str | None:
    return (_choice.get("shadow") or {}).get("name")


def _shadow_top1(img: Image.Image) -> str | None:
    sh = _choice.get("shadow")
    if not sh:
        return None
    logits = sh["session"].run(None, {"input": to_input(img)})[0][0]
    return sh["names"][int(np.argmax(logits))]


def _providers() -> list[str]:
    import onnxruntime as ort
    want = os.environ.get("INFERENCE_DEVICE", "auto").lower()
    avail = ort.get_available_providers()
    if want in ("auto", "cuda") and "CUDAExecutionProvider" in avail:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if want == "cuda":
        log.warning("INFERENCE_DEVICE=cuda but CUDAExecutionProvider is unavailable; using CPU")
    return ["CPUExecutionProvider"]


def _load():
    if _state["loaded"]:
        return
    _state.update(loaded=True, seg=None, cls=None, errors={}, device="cpu")
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    prov = _providers()
    d = settings.models_dir
    choices = ([(Path(_choice["dir"]), _choice["label"])] if _choice["dir"] else []) + [(d / "exp002", None)]
    for cdir, label in choices:   # a promoted package first; the built-in model if it cannot load
        try:
            _state["cls"] = {**load_classifier(cdir, opts, prov), "promoted": label}
            _state["device"] = "cuda" if _state["cls"]["session"].get_providers()[0] == "CUDAExecutionProvider" else "cpu"
            break
        except Exception as e:
            _state["errors"]["classifier" if label is None else "promoted_model"] = f"{type(e).__name__}: {e}"
            log.exception("food classifier %s failed to load", cdir)
    seg_path = d / "yolo11n-seg.onnx"
    if seg_path.exists():
        try:
            s = ort.InferenceSession(str(seg_path), opts, providers=prov)
            names = ast.literal_eval(s.get_modelmeta().custom_metadata_map.get("names", "{}"))
            _state["seg"] = {"session": s, "names": names, "imgsz": s.get_inputs()[0].shape[2] or 640}
        except Exception as e:
            _state["errors"]["segmenter"] = str(e)
    else:
        _state["errors"]["segmenter"] = "yolo11n-seg.onnx not found (detection disabled; classification still works)"


def warmup():
    """Load models once at startup and run one inference so the first request is fast."""
    with _lock:
        _load()
        if _state["cls"]:
            _state["cls"]["session"].run(None, {"input": np.zeros((1, 3, 224, 224), np.float32)})


def close():
    with _lock:
        _state.clear()
        _state["loaded"] = False


def models() -> dict:
    with _lock:
        _load()
    out = {}
    if _state["cls"]:
        c = _state["cls"]["card"]
        m = (c.get("metrics") or {}).get("reported_by_developer") or {}
        out["classifier"] = {"name": c["name"], "version": c["version"], "trained_on": " + ".join(c.get("training_data") or []),
                             "task": f"food classification ({c['num_classes']} classes)", "food_classes": c["num_classes"], "stage": "4 · Food classification",
                             "device": _state["device"], "reported_metrics": {k: m[k] for k in ("top1_accuracy", "top3_accuracy", "macro_f1") if k in m} or None,
                             "metrics_source": m.get("source"), "sha256": ((c.get("files") or {}).get("best_model.pth") or {}).get("sha256"),
                             "promoted": _state["cls"].get("promoted"), "shadow": shadow_name()}
    if _state["seg"]:
        out["detector"] = {"name": "YOLO11n-seg", "version": "ultralytics-8.3 / ONNX", "trained_on": "COCO-2017",
                           "task": "instance segmentation", "food_classes": len(COCO_FOOD),
                           "stage": "3 · Food instance detection", "device": _state["device"]}
    return out


def status() -> dict:
    m = models()
    return {"available": "classifier" in m, "device": _state.get("device"),
            "error": "; ".join(f"{k}: {v}" for k, v in _state.get("errors", {}).items()) or None, "models": m}


def taxonomy_class(class_id: int) -> dict | None:
    with _lock:
        _load()
    c = _state.get("cls")
    if not c or not 0 <= class_id < len(c["names"]):
        return None
    meta = c["map"].get(class_id, {})
    return {"id": class_id, "name": c["names"][class_id], "nutrition_key": meta.get("nutrition_key"),
            "match": meta.get("match", "none")}


def search_taxonomy(q: str, limit: int = 15) -> list[dict]:
    import difflib
    with _lock:
        _load()
    c = _state.get("cls")
    if not c:
        return []
    ql = q.lower().strip()
    scored = sorted(((difflib.SequenceMatcher(None, ql, n).ratio() + (0.6 if ql and ql in n else 0), i)
                     for i, n in enumerate(c["names"])), reverse=True)
    return [taxonomy_class(i) for _, i in scored[:limit]]


def score_band(score: float) -> str:
    return "strong" if score >= 0.6 else "moderate" if score >= 0.3 else "weak"


# ---------------------------------------------------------------- classification
def classify(img: Image.Image, k: int = 3) -> list[dict]:
    return classify_fp(img, k)[0]


def classify_fp(img: Image.Image, k: int = 3) -> tuple[list[dict], list[float]]:
    """Top-k plus a fingerprint: sqrt of the class probabilities (unit length; cosine = Bhattacharyya
    coefficient). Used to recognise foods the user has named before (services/memory.py)."""
    c = _state["cls"]
    logits = c["session"].run(None, {"input": to_input(img)})[0][0]
    p = np.exp(logits - logits.max())
    p /= p.sum()
    fp = [round(float(v), 4) for v in np.sqrt(p)]
    out = []
    for i in p.argsort()[::-1][:k]:
        meta = c["map"].get(int(i), {})
        out.append({"class_id": int(i), "label": c["names"][i], "score": round(float(p[i]), 4),
                    "nutrition_key": meta.get("nutrition_key"), "match": meta.get("match", "none")})
    return out, fp


# ---------------------------------------------------------------- detection (YOLO-seg)
def _letterbox(img: Image.Image, size: int):
    r = min(size / img.width, size / img.height)
    nw, nh = round(img.width * r), round(img.height * r)
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    px, py = (size - nw) // 2, (size - nh) // 2
    canvas.paste(img.resize((nw, nh), Image.BILINEAR), (px, py))
    return np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0, r, px, py


def _nms(boxes: np.ndarray, scores: np.ndarray, iou: float = 0.5) -> list[int]:
    order, keep = scores.argsort()[::-1], []
    area = lambda b: (b[..., 2] - b[..., 0]) * (b[..., 3] - b[..., 1])
    while order.size:
        i = order[0]
        keep.append(int(i))
        rest = order[1:]
        xx1 = np.maximum(boxes[i, 0], boxes[rest, 0]); yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[rest, 2]); yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        order = rest[inter / (area(boxes[i]) + area(boxes[rest]) - inter + 1e-9) < iou]
    return keep


def _segment(img: Image.Image) -> list[dict]:
    seg = _state["seg"]
    size = seg["imgsz"]
    x, r, px, py = _letterbox(img, size)
    out0, protos = seg["session"].run(None, {seg["session"].get_inputs()[0].name: x})
    pred = out0[0].T
    nc = pred.shape[1] - 4 - protos.shape[1]
    cls_scores = pred[:, 4:4 + nc]
    cls_id, score = cls_scores.argmax(1), cls_scores.max(1)
    m = score >= 0.25
    pred, cls_id, score = pred[m], cls_id[m], score[m]
    if not len(pred):
        return []
    b = pred[:, :4]
    boxes = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2, b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1)
    keep = []
    for c in np.unique(cls_id):
        idx = np.where(cls_id == c)[0]
        keep += [idx[k] for k in _nms(boxes[idx], score[idx])]
    keep = sorted(keep, key=lambda i: -score[i])[:20]
    P = protos[0]
    mh, mw = P.shape[1:]
    out = []
    for i in keep:
        coef = pred[i, 4 + nc:]
        mask = 1 / (1 + np.exp(-(coef @ P.reshape(len(coef), -1)))).reshape(mh, mw)
        x1, y1, x2, y2 = boxes[i] * (mw / size)
        crop = np.zeros_like(mask)
        crop[max(int(y1), 0):int(np.ceil(y2)), max(int(x1), 0):int(np.ceil(x2))] = 1
        m_img = Image.fromarray((mask * crop * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)
        m_img = m_img.crop((px, py, px + round(img.width * r), py + round(img.height * r))).resize(img.size, Image.BILINEAR)
        mask_np = np.asarray(m_img) > 127
        bx = np.clip((boxes[i] - [px, py, px, py]) / r, 0, [img.width, img.height, img.width, img.height])
        out.append({"label": seg["names"].get(int(cls_id[i]), str(cls_id[i])), "score": float(score[i]),
                    "bbox": {"x": bx[0] / img.width, "y": bx[1] / img.height,
                             "w": (bx[2] - bx[0]) / img.width, "h": (bx[3] - bx[1]) / img.height},
                    "mask": mask_np, "area_frac": float(mask_np.mean())})
    return out


def _crop(img: Image.Image, box: dict, pad: float = 0.08) -> Image.Image:
    x1 = max(0, (box["x"] - pad * box["w"]) * img.width); y1 = max(0, (box["y"] - pad * box["h"]) * img.height)
    x2 = min(img.width, (box["x"] + box["w"] * (1 + pad)) * img.width); y2 = min(img.height, (box["y"] + box["h"] * (1 + pad)) * img.height)
    return img.crop((int(x1), int(y1), max(int(x2), int(x1) + 8), max(int(y2), int(y1) + 8)))


def _overlay(img: Image.Image, instances: list[dict], path: Path) -> None:
    base = img.convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for k, it in enumerate(i for i in instances if i.get("label_shown")):
        col = PALETTE[k % len(PALETTE)]
        if it.get("mask") is not None:
            layer.paste(Image.new("RGBA", img.size, col + (110,)), (0, 0), Image.fromarray((it["mask"] * 110).astype(np.uint8)))
        b = it["bbox"]
        xy = [b["x"] * img.width, b["y"] * img.height, (b["x"] + b["w"]) * img.width, (b["y"] + b["h"]) * img.height]
        draw.rectangle(xy, outline=col + (255,), width=3)
        draw.rectangle([xy[0], max(0, xy[1] - 18), xy[0] + 8 + 7 * len(it["label_shown"]), xy[1]], fill=col + (230,))
        draw.text((xy[0] + 4, max(0, xy[1] - 16)), it["label_shown"], fill=(255, 255, 255, 255))
    Image.alpha_composite(base, layer).convert("RGB").save(path, "JPEG", quality=88)


# ---------------------------------------------------------------- pipeline entry
def _crop_full(full: Image.Image, box: dict, pad: float = 0.12) -> Image.Image:
    return _crop(full, box, pad)


def _iou(a: dict, b: dict) -> tuple[float, float]:
    ax2, ay2, bx2, by2 = a["x"] + a["w"], a["y"] + a["h"], b["x"] + b["w"], b["y"] + b["h"]
    iw, ih = max(0, min(ax2, bx2) - max(a["x"], b["x"])), max(0, min(ay2, by2) - max(a["y"], b["y"]))
    inter = iw * ih
    return inter / (a["w"] * a["h"] + b["w"] * b["h"] - inter + 1e-9), inter / (min(a["w"] * a["h"], b["w"] * b["h"]) + 1e-9)


def _union(a: dict, b: dict) -> dict:
    x1, y1 = min(a["x"], b["x"]), min(a["y"], b["y"])
    return {"x": x1, "y": y1, "w": max(a["x"] + a["w"], b["x"] + b["w"]) - x1, "h": max(a["y"] + a["h"], b["y"] + b["h"]) - y1}


def analyze(path: str, view: str, original_path: str | None = None) -> dict:
    """Multi-food analysis: region proposals (colour segmentation + YOLO-seg) -> EXP-002 per crop -> items.

    Item kinds: "food" (top-1 >= UNKNOWN_MIN), "unknown" (weak region, user names it), "suggestion" (weak region
    inside a named food, offered but not counted), or a single "whole photo" item when no regions are found.
    """
    from app.services import tuning
    from app.services.proposals import propose
    UNKNOWN_MIN, WHOLE_DISH = tuning.get("vision.unknown_min"), tuning.get("vision.whole_dish")
    PROPOSE_MIN, MAX_UNKNOWN = tuning.get("vision.propose_min"), tuning.get("vision.max_unknown")
    with _lock:
        _load()
        if not _state["cls"]:
            return {"view": view, "ok": False, "error": status()["error"], "items": [], "instances": [], "top_labels": []}
        img = Image.open(path).convert("RGB")                     # display copy for segmentation
        full = (ImageOps.exif_transpose(Image.open(original_path)).convert("RGB")
                if original_path and Path(original_path).exists() else img)   # original for classification crops
        t0 = time.perf_counter()
        dets = [d for d in (_segment(img) if _state["seg"] else []) if d["score"] >= DET_MIN]
        prop = propose(img)
        t1 = time.perf_counter()
        whole, whole_fp = classify_fp(full)
        whole_shadow = _shadow_top1(full)
        regions = [{"bbox": r["bbox"], "area_frac": r["area_frac"], "source": "segmentation", "detector_label": None,
                    "detector_score": None, "has_mask": True} for r in prop["regions"]]
        inside = lambda r, box: (box["x"] <= r["bbox"]["x"] + r["bbox"]["w"] / 2 <= box["x"] + box["w"]
                                 and box["y"] <= r["bbox"]["y"] + r["bbox"]["h"] / 2 <= box["y"] + box["h"])
        for d in dets:   # a cup/bowl/glass is one dish: classify it whole and drop the fragments inside it
            if d["label"] in COCO_DISH_CONTAINERS and d["score"] >= 0.40:
                regions = [r for r in regions if not inside(r, d["bbox"])]
                regions.append({"bbox": d["bbox"], "area_frac": d["area_frac"], "source": f"yolo11n-seg {d['label']}",
                                "detector_label": d["label"], "detector_score": round(d["score"], 3), "has_mask": True})
            elif d["label"] in {"fork", "knife", "spoon"}:   # cutlery is not food
                regions = [r for r in regions if _iou(r["bbox"], d["bbox"])[1] < 0.5]
        containers = []
        for d in dets:
            if d["label"] in COCO_FOOD:
                match = next((r for r in regions if _iou(r["bbox"], d["bbox"])[0] > 0.5), None)
                if match:
                    match.update(detector_label=d["label"], detector_score=round(d["score"], 3))
                else:
                    regions.append({"bbox": d["bbox"], "area_frac": d["area_frac"], "source": "yolo11n-seg",
                                    "detector_label": d["label"], "detector_score": round(d["score"], 3), "has_mask": True})
            if d["label"] in COCO_DISH_CONTAINERS | COCO_REFERENCE:
                containers.append({"label": d["label"], "score": round(d["score"], 3), "bbox": d["bbox"],
                                   "area_frac": round(d["area_frac"], 4)})
        if prop["plate_area_frac"]:
            containers.append({"label": "dining table", "score": None, "source": "segmentation (white plate)",
                               "bbox": {"x": 0, "y": 0, "w": 1, "h": 1}, "area_frac": prop["plate_area_frac"]})
        for r in regions:
            piece = _crop_full(full, r["bbox"])
            r["top"], r["fp"] = classify_fp(piece)
            r["shadow"] = _shadow_top1(piece)
        # merge touching fragments that the classifier agrees on (one food split into colours)
        changed = True
        while changed:
            changed = False
            for i, a in enumerate(regions):
                for b in regions[i + 1:]:
                    if a["top"][0]["class_id"] == b["top"][0]["class_id"] and a["top"][0]["score"] >= UNKNOWN_MIN \
                            and b["top"][0]["score"] >= UNKNOWN_MIN and _iou(a["bbox"], b["bbox"])[1] > 0.05:
                        a["bbox"], a["area_frac"] = _union(a["bbox"], b["bbox"]), a["area_frac"] + b["area_frac"]
                        a["top"], a["fp"] = max((a["top"], a["fp"]), (b["top"], b["fp"]), key=lambda t: t[0][0]["score"])
                        regions.remove(b)
                        changed = True
                        break
                if changed:
                    break
        t2 = time.perf_counter()

    items = []
    # small = tiny box, or a tiny mask (masks undercount foods with white/dark parts removed as plate/shadow)
    small = lambda r: r["source"] == "segmentation" and (r["bbox"]["w"] * r["bbox"]["h"] < MIN_ITEM_AREA
                                                         or r["area_frac"] < MIN_ITEM_AREA / 2)
    named = [r for r in regions if r["top"][0]["score"] >= UNKNOWN_MIN and not small(r)]
    # unidentified fragments that touch a named food listed in their top-3 are part of that food
    for r in [r for r in regions if r not in named and not small(r)]:
        host = next((o for o in named if o["top"][0]["class_id"] in {c["class_id"] for c in r["top"]}
                     and _iou(o["bbox"], r["bbox"])[1] > 0.0), None)
        if host:
            host["bbox"], host["area_frac"] = _union(host["bbox"], r["bbox"]), host["area_frac"] + r["area_frac"]
            regions.remove(r)
    dominant = next((r for r in named if r["area_frac"] >= 0.80), None)   # one dish fills the photo
    for n, r in enumerate(sorted(regions, key=lambda r: (r["bbox"]["y"], r["bbox"]["x"])), 1):
        top = r["top"][0]
        if r in named and (dominant is None or r is dominant):
            kind = "food"
        else:
            inside = any(o is not r and _iou(r["bbox"], o["bbox"])[1] > 0.6 and o["area_frac"] > r["area_frac"] for o in named)
            kind = "suggestion" if (inside or small(r) or dominant is not None) else "unknown"
        items.append({"region_id": f"{view}-{n}", "kind": kind, "model_label": top["label"] if kind == "food" else None,
                      "class_id": top["class_id"] if kind == "food" else None,
                      "nutrition_key": top["nutrition_key"] if kind == "food" else None,
                      "match": top["match"] if kind == "food" else "none", "score": top["score"], "candidates": r["top"],
                      "bbox": r["bbox"], "area_frac": r["area_frac"], "instance": r["source"],
                      "detector_label": r["detector_label"], "detector_score": r["detector_score"],
                      "has_mask": r["has_mask"], "view": view, "model": "classifier", "fingerprint": r["fp"],
                      "shadow_label": r.get("shadow")})
    wc = whole[0]
    if wc["score"] >= 0.60 and not any(i["kind"] == "food" and i["class_id"] == wc["class_id"] for i in items):
        # the photo as a whole is confidently one class that no single region captured: give it to the largest
        # region that lists it among its top-3, or add it as a whole-photo item
        hosts = [i for i in items if i["kind"] != "food" and any(c["class_id"] == wc["class_id"] for c in i["candidates"])]
        host = max(hosts, key=lambda i: i["area_frac"]) if hosts else None
        if host:
            host.update(kind="food", model_label=wc["label"], class_id=wc["class_id"], nutrition_key=wc["nutrition_key"],
                        match=wc["match"], score=wc["score"], candidates=whole, instance=host["instance"] + " + whole-photo agreement",
                        shadow_label=whole_shadow)
        elif wc["score"] >= 0.60 and len([i for i in items if i["kind"] == "food"]) <= 1:
            items.insert(0, {"region_id": f"{view}-0", "kind": "food", "model_label": wc["label"], "class_id": wc["class_id"],
                             "nutrition_key": wc["nutrition_key"], "match": wc["match"], "score": wc["score"],
                             "candidates": whole, "bbox": None, "area_frac": 1.0, "instance": "whole photo",
                             "detector_label": None, "detector_score": None, "has_mask": False, "view": view, "model": "classifier", "fingerprint": whole_fp,
                             "shadow_label": whole_shadow})
    if whole[0]["score"] >= WHOLE_DISH and any(i["kind"] == "food" and i["class_id"] == whole[0]["class_id"] for i in items):
        for i in items:   # single-dish photo: other regions are offered as possible extra items (one tap to add)
            if i["kind"] == "unknown" or (i["kind"] == "food" and i["class_id"] != whole[0]["class_id"]):
                i.update(kind="suggestion", model_label=None, class_id=None, nutrition_key=None, match="none")
    unknown = sorted((i for i in items if i["kind"] == "unknown"), key=lambda i: -i["area_frac"])
    for i in unknown[MAX_UNKNOWN:]:   # keep the review short: the largest unidentified regions are listed, the rest offered
        i["kind"] = "suggestion"
    if not any(i["kind"] == "food" for i in items):
        # no region was identifiable: a confident whole-photo class becomes the item (single-dish photo) and the
        # weak regions are offered as possible extra items; otherwise the weak regions stay "unidentified"
        if whole[0]["score"] >= PROPOSE_MIN:
            for i in items:
                i["kind"] = "suggestion"
            items.insert(0, {"region_id": f"{view}-0", "kind": "food", "model_label": whole[0]["label"],
                             "class_id": whole[0]["class_id"], "nutrition_key": whole[0]["nutrition_key"],
                             "match": whole[0]["match"], "score": whole[0]["score"], "candidates": whole, "bbox": None,
                             "area_frac": 1.0, "instance": "whole photo", "detector_label": None, "detector_score": None,
                             "has_mask": False, "view": view, "model": "classifier", "fingerprint": whole_fp,
                             "shadow_label": whole_shadow})
    return {
        "view": view, "ok": True, "items": items, "containers": containers, "overlay_path": None,
        "instances": [{"label": i["model_label"] or "unidentified", "kind": i["kind"], "score": i["score"],
                       "area_frac": i["area_frac"], "source": i["instance"]} for i in items],
        "top_labels": [{"label": c["label"], "score": c["score"], "class_id": c["class_id"]} for c in whole],
        "latency_ms": {"detector": round((t1 - t0) * 1000, 1), "classifier": round((t2 - t1) * 1000, 1)},
        "device": _state["device"], "regions": len(regions),
    }


def merge(results: list[dict]) -> list[dict]:
    """Items are itemised from the first photo that yields food; other views only add foods not already present."""
    out, seen = [], set()
    for r in results:
        for it in r["items"]:
            if out and it["kind"] == "food" and it["class_id"] in seen and it["view"] != out[0]["view"]:
                continue
            out.append({**it, "views": [it["view"]], "instances": 1})
            if it["kind"] == "food":
                seen.add(it["class_id"])
    return out
