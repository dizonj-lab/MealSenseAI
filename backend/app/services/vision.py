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
PROPOSE_MIN = 0.20       # below this the photo's top-1 is not added automatically; the user picks from the top-3
CROP_MIN = 0.60          # a crop proposes an extra item only when confident and different from the photo's top-3
PALETTE = [(20, 184, 166), (14, 165, 233), (245, 158, 11), (16, 185, 129), (139, 92, 246), (244, 63, 94)]

_lock = threading.RLock()
_state: dict = {"loaded": False}


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
    cdir = d / "exp002"
    try:
        card = json.loads((cdir / "model_card.json").read_text())
        taxonomy = json.loads((cdir / "class_mapping.json").read_text())
        sess = ort.InferenceSession(str(cdir / "model.onnx"), opts, providers=prov)
        n_out = sess.get_outputs()[0].shape[-1]
        if n_out != len(taxonomy) or sorted(taxonomy.values()) != list(range(len(taxonomy))):
            raise ValueError(f"taxonomy mismatch: model outputs {n_out}, taxonomy has {len(taxonomy)} classes")
        names = [None] * len(taxonomy)
        for name, i in taxonomy.items():
            names[i] = name
        by_id = {c["id"]: c for c in card["classes"]}
        _state["cls"] = {"session": sess, "card": card, "names": names, "map": by_id}
        _state["device"] = "cuda" if sess.get_providers()[0] == "CUDAExecutionProvider" else "cpu"
    except Exception as e:
        _state["errors"]["classifier"] = f"{type(e).__name__}: {e}"
        log.exception("food classifier failed to load")
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
        m = c["metrics"]["reported_by_developer"]
        out["classifier"] = {"name": c["name"], "version": c["version"], "trained_on": " + ".join(c["training_data"]),
                             "task": f"food classification ({c['num_classes']} classes)", "food_classes": c["num_classes"], "stage": "4 · Food classification",
                             "device": _state["device"], "reported_metrics": {k: m[k] for k in ("top1_accuracy", "top3_accuracy", "macro_f1")},
                             "metrics_source": m["source"], "sha256": c["files"]["best_model.pth"]["sha256"]}
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
    c = _state["cls"]
    logits = c["session"].run(None, {"input": to_input(img)})[0][0]
    p = np.exp(logits - logits.max())
    p /= p.sum()
    out = []
    for i in p.argsort()[::-1][:k]:
        meta = c["map"].get(int(i), {})
        out.append({"class_id": int(i), "label": c["names"][i], "score": round(float(p[i]), 4),
                    "nutrition_key": meta.get("nutrition_key"), "match": meta.get("match", "none")})
    return out


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
def analyze(path: str, view: str, original_path: str | None = None) -> dict:
    """Classify the photo (evaluation preprocessing on the original upload) and propose extra items from crops."""
    with _lock:
        _load()
        if not _state["cls"]:
            return {"view": view, "ok": False, "error": status()["error"], "items": [], "instances": [], "top_labels": []}
        # display copy (orientation-corrected, <=1024 px) for detection, crops and overlay: fast on any photo size
        img = Image.open(path).convert("RGB")
        # whole-photo classification on the original upload, exactly as in EXP-002 evaluation
        full = (ImageOps.exif_transpose(Image.open(original_path)).convert("RGB")
                if original_path and Path(original_path).exists() else img)
        t0 = time.perf_counter()
        dets = [d for d in (_segment(img) if _state["seg"] else []) if d["score"] >= DET_MIN]
        t1 = time.perf_counter()
        top3 = classify(full)
        items = [{"model_label": top3[0]["label"], "class_id": top3[0]["class_id"], "nutrition_key": top3[0]["nutrition_key"],
                  "match": top3[0]["match"], "score": top3[0]["score"], "candidates": top3, "bbox": None, "area_frac": 1.0,
                  "instance": "whole photo", "has_mask": False, "view": view, "model": "classifier"}]
        seen = {c["class_id"] for c in top3}
        instances = []
        for d in dets:
            kind = "food" if d["label"] in COCO_FOOD else "container" if d["label"] in COCO_DISH_CONTAINERS else \
                "reference" if d["label"] in COCO_REFERENCE else None
            if not kind:
                continue
            inst = {**d, "kind": kind}
            instances.append(inst)
            if kind == "reference":
                continue
            c3 = classify(_crop(img, d["bbox"]))
            inst["top"] = c3
            if c3[0]["score"] >= CROP_MIN and c3[0]["class_id"] not in seen:
                seen.add(c3[0]["class_id"])
                inst["label_shown"] = c3[0]["label"]
                items.append({"model_label": c3[0]["label"], "class_id": c3[0]["class_id"], "nutrition_key": c3[0]["nutrition_key"],
                              "match": c3[0]["match"], "score": c3[0]["score"], "candidates": c3, "bbox": d["bbox"],
                              "area_frac": d["area_frac"], "instance": d["label"], "has_mask": True, "view": view,
                              "model": "classifier"})
            elif c3[0]["class_id"] in {c["class_id"] for c in top3}:
                inst["label_shown"] = c3[0]["label"]
        t2 = time.perf_counter()
        overlay = str(Path(path).with_name(f"{view}_overlay.jpg"))
        _overlay(img, instances, Path(overlay))
    refs = [{"label": i["label"], "score": round(i["score"], 3), "bbox": i["bbox"], "area_frac": round(i["area_frac"], 4)}
            for i in instances if i["kind"] in ("reference", "container")]
    return {
        "view": view, "ok": True, "items": items, "containers": refs, "overlay_path": overlay,
        "instances": [{"label": i["label"], "kind": i["kind"], "score": round(i["score"], 3), "area_frac": round(i["area_frac"], 4),
                       "top": (i.get("top") or [None])[0]} for i in instances],
        "top_labels": [{"label": c["label"], "score": c["score"], "class_id": c["class_id"]} for c in top3],
        "latency_ms": {"detector": round((t1 - t0) * 1000, 1), "classifier": round((t2 - t1) * 1000, 1)},
        "device": _state["device"],
    }


def merge(results: list[dict]) -> list[dict]:
    """Merge the same class across views (top & side photo); keep the strongest evidence and its candidates."""
    merged: dict[int, dict] = {}
    for r in results:
        for it in r["items"]:
            cur = merged.get(it["class_id"])
            if cur is None:
                merged[it["class_id"]] = {**it, "views": [it["view"]], "instances": 1}
                continue
            if it["view"] not in cur["views"]:
                cur["views"].append(it["view"])
            if it["score"] > cur["score"]:
                cur.update({k: it[k] for k in ("score", "candidates", "view")})
            if it["bbox"] and not cur["bbox"]:
                cur.update(bbox=it["bbox"], area_frac=it["area_frac"], has_mask=it["has_mask"], instance=it["instance"])
    return sorted(merged.values(), key=lambda x: -x["score"])
