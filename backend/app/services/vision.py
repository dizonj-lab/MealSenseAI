"""Stages 3-4 of the inference pipeline: food instance detection (segmentation) and per-instance classification.

Stage 3 — instance detection/segmentation
  YOLO11n-seg (COCO-2017, ONNX via onnxruntime): instance masks + boxes for 10 COCO food classes and the
  containers (bowl, cup, plate-like table) that hold dishes. Fallback: EfficientDet-Lite0 (boxes only).
Stage 4 — classification of each instance crop
  Fine-tuned food classifier (ml/models/food_classifier/model.onnx, from ml/training) when present,
  otherwise EfficientNet-Lite0 ImageNet-1k (~40 food classes).
Scores are raw softmax/sigmoid outputs, NOT calibrated probabilities.
"""
import ast
import json
import logging
import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from app.core.config import settings

log = logging.getLogger(__name__)

# ImageNet label -> nutrition table key (None = food but no reliable composition match)
IMAGENET_FOOD = {
    "pizza": "pizza", "cheeseburger": "cheeseburger", "hotdog": "hot_dog", "burrito": "burrito",
    "bagel": "bagel", "pretzel": "pretzel", "French loaf": "french_bread", "ice cream": "ice_cream",
    "guacamole": "guacamole", "carbonara": "carbonara", "mashed potato": "mashed_potato",
    "head cabbage": "cabbage", "broccoli": "broccoli", "cauliflower": "cauliflower",
    "zucchini": "zucchini", "spaghetti squash": "butternut_squash", "acorn squash": "butternut_squash",
    "butternut squash": "butternut_squash", "cucumber": "cucumber", "artichoke": "artichoke",
    "bell pepper": "bell_pepper", "mushroom": "mushroom", "Granny Smith": "apple",
    "strawberry": "strawberry", "orange": "orange", "lemon": "lemon", "fig": "fig",
    "pineapple": "pineapple", "banana": "banana", "jackfruit": "jackfruit",
    "custard apple": "custard_apple", "pomegranate": "pomegranate", "meat loaf": "meat_loaf",
    "potpie": "pot_pie", "red wine": "red_wine", "espresso": "coffee_black", "eggnog": "eggnog",
    "consomme": "consomme", "trifle": "trifle", "corn": "corn", "ear": "corn",
    "hot pot": None, "chocolate sauce": None, "dough": None,
}
COCO_FOOD = {
    "banana": "banana", "apple": "apple", "sandwich": "sandwich", "orange": "orange",
    "broccoli": "broccoli", "carrot": "carrot", "hot dog": "hot_dog", "pizza": "pizza",
    "donut": "donut", "cake": "chocolate_cake",
}
COCO_DISH_CONTAINERS = {"bowl", "cup", "wine glass"}  # their contents get classified
COCO_REFERENCE = {"dining table", "bowl", "fork", "knife", "spoon"}
DET_MIN = 0.30
IMAGENET_MIN = 0.12
FINETUNED_MIN = 0.70  # closed-set model: below this, defer to the open-vocabulary ImageNet classifier
SCENE_MIN = {"imagenet": 0.30, "finetuned": 0.75}
PALETTE = [(20, 184, 166), (14, 165, 233), (245, 158, 11), (16, 185, 129), (139, 92, 246), (244, 63, 94)]

_lock = threading.RLock()
_state: dict = {"loaded": False}


# ---------------------------------------------------------------- model loading
def _load():
    if _state["loaded"]:
        return
    _state.update(loaded=True, seg=None, det=None, cls=None, ft=None, errors={})
    d = settings.models_dir
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    seg_path = d / "yolo11n-seg.onnx"
    if seg_path.exists():
        try:
            s = ort.InferenceSession(str(seg_path), opts, providers=["CPUExecutionProvider"])
            names = ast.literal_eval(s.get_modelmeta().custom_metadata_map.get("names", "{}"))
            _state["seg"] = {"session": s, "names": names, "imgsz": s.get_inputs()[0].shape[2] or 640}
        except Exception as e:
            _state["errors"]["segmenter"] = str(e)
    ft_dir = d / "food_classifier"
    if (ft_dir / "model.onnx").exists():
        try:
            card = json.loads((ft_dir / "model_card.json").read_text())
            _state["ft"] = {"session": ort.InferenceSession(str(ft_dir / "model.onnx"), opts,
                                                            providers=["CPUExecutionProvider"]), "card": card}
        except Exception as e:
            _state["errors"]["finetuned"] = str(e)
    try:
        from mediapipe.tasks.python import BaseOptions, vision as mpv
        _state["cls"] = mpv.ImageClassifier.create_from_options(mpv.ImageClassifierOptions(
            base_options=BaseOptions(model_asset_path=str(d / "efficientnet_lite0.tflite")), max_results=10))
        if _state["seg"] is None:
            _state["det"] = mpv.ObjectDetector.create_from_options(mpv.ObjectDetectorOptions(
                base_options=BaseOptions(model_asset_path=str(d / "efficientdet_lite0.tflite")),
                max_results=15, score_threshold=0.25))
    except Exception as e:
        _state["errors"]["mediapipe"] = f"{type(e).__name__}: {e}"
        log.exception("MediaPipe models failed to load")


def close():
    with _lock:
        for k in ("cls", "det"):
            if _state.get(k) is not None:
                _state[k].close()
        _state.clear()
        _state["loaded"] = False


def models() -> dict:
    """Active model descriptors (for UI, persistence and the AI insights page)."""
    with _lock:
        _load()
    out = {}
    if _state["seg"]:
        out["detector"] = {"name": "YOLO11n-seg", "version": "ultralytics-8.3 / ONNX", "trained_on": "COCO-2017",
                           "task": "instance segmentation", "food_classes": len(COCO_FOOD),
                           "stage": "3 · Food instance detection"}
    elif _state["det"]:
        out["detector"] = {"name": "EfficientDet-Lite0", "version": "mediapipe-float32-latest", "trained_on": "COCO-2017",
                           "task": "object detection (boxes only)", "food_classes": len(COCO_FOOD),
                           "stage": "3 · Food instance detection"}
    if _state["ft"]:
        c = _state["ft"]["card"]
        out["classifier"] = {"name": c["name"], "version": c["version"], "trained_on": "+".join(c["dataset"]["sources"]),
                             "task": c["task"], "food_classes": len(c["classes"]), "stage": "4 · Food classification",
                             "test_metrics": {k: v for k, v in c["test_metrics"].items() if isinstance(v, (int, float))},
                             "dataset_hash": c["dataset"]["hash"]}
    if _state["cls"]:
        out["classifier_imagenet"] = {"name": "EfficientNet-Lite0", "version": "mediapipe-float32-latest",
                                      "trained_on": "ImageNet-1k", "task": "image classification",
                                      "food_classes": sum(1 for v in IMAGENET_FOOD.values() if v),
                                      "stage": "4 · Food classification" + (" (fallback)" if _state["ft"] else "")}
    return out


def status() -> dict:
    m = models()
    return {"available": "detector" in m and ("classifier" in m or "classifier_imagenet" in m),
            "error": "; ".join(f"{k}: {v}" for k, v in _state["errors"].items()) or None, "models": m}


def score_band(score: float) -> str:
    return "strong" if score >= 0.6 else "moderate" if score >= 0.3 else "weak"


# ---------------------------------------------------------------- stage 3: instances
def _letterbox(img: Image.Image, size: int):
    r = min(size / img.width, size / img.height)
    nw, nh = round(img.width * r), round(img.height * r)
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    px, py = (size - nw) // 2, (size - nh) // 2
    canvas.paste(img.resize((nw, nh), Image.BILINEAR), (px, py))
    return np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0, r, px, py


def _nms(boxes: np.ndarray, scores: np.ndarray, iou: float = 0.5) -> list[int]:
    order, keep = scores.argsort()[::-1], []
    while order.size:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0]); yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2]); yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        area = lambda b: (b[..., 2] - b[..., 0]) * (b[..., 3] - b[..., 1])
        order = order[1:][inter / (area(boxes[i]) + area(boxes[order[1:]]) - inter + 1e-9) < iou]
    return keep


def _segment(img: Image.Image) -> list[dict]:
    seg = _state["seg"]
    size = seg["imgsz"]
    x, r, px, py = _letterbox(img, size)
    out0, protos = seg["session"].run(None, {seg["session"].get_inputs()[0].name: x})
    pred = out0[0].T  # (8400, 4 + nc + 32)
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
    for c in np.unique(cls_id):  # class-wise NMS
        idx = np.where(cls_id == c)[0]
        keep += [idx[k] for k in _nms(boxes[idx], score[idx])]
    keep = sorted(keep, key=lambda i: -score[i])[:20]
    P = protos[0]  # (32, mh, mw)
    mh, mw = P.shape[1:]
    out = []
    for i in keep:
        coef = pred[i, 4 + nc:]
        mask = 1 / (1 + np.exp(-(coef @ P.reshape(len(coef), -1)))).reshape(mh, mw)
        x1, y1, x2, y2 = boxes[i] * (mw / size)
        crop = np.zeros_like(mask)
        crop[max(int(y1), 0):int(np.ceil(y2)), max(int(x1), 0):int(np.ceil(x2))] = 1
        mask = mask * crop
        # back to original image coordinates
        m_img = Image.fromarray((mask * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)
        m_img = m_img.crop((px, py, px + round(img.width * r), py + round(img.height * r))).resize(img.size, Image.BILINEAR)
        mask_np = np.asarray(m_img) > 127
        bx = (boxes[i] - [px, py, px, py]) / r
        bx = np.clip(bx, 0, [img.width, img.height, img.width, img.height])
        out.append({"label": seg["names"].get(int(cls_id[i]), str(cls_id[i])), "score": float(score[i]),
                    "bbox": {"x": bx[0] / img.width, "y": bx[1] / img.height,
                             "w": (bx[2] - bx[0]) / img.width, "h": (bx[3] - bx[1]) / img.height},
                    "mask": mask_np, "area_frac": float(mask_np.mean())})
    return out


def _detect_boxes(img: Image.Image) -> list[dict]:
    import mediapipe as mp
    res = _state["det"].detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(img)))
    out = []
    for d in res.detections:
        b, c = d.bounding_box, d.categories[0]
        box = {"x": b.origin_x / img.width, "y": b.origin_y / img.height, "w": b.width / img.width, "h": b.height / img.height}
        out.append({"label": c.category_name, "score": float(c.score), "bbox": box, "mask": None,
                    "area_frac": box["w"] * box["h"]})
    return out


# ---------------------------------------------------------------- stage 4: classification
def _classify(crop: Image.Image) -> dict:
    """Top-5 food candidates for one crop: fine-tuned model first, ImageNet model when it is not confident."""
    if _state["ft"]:
        c = _classify_finetuned(crop)
        if c["top"][0]["score"] >= FINETUNED_MIN or not _state["cls"]:
            return c
        im = _classify_imagenet(crop)
        im["deferred_from"] = {"model_name": c["model_name"], "top": c["top"][:3]}
        return im
    return _classify_imagenet(crop)


def _classify_finetuned(crop: Image.Image) -> dict:
    ft = _state["ft"]
    inp = ft["card"]["input"]
    s = inp["resize"] / min(crop.size)
    im = crop.resize((max(inp["size"], round(crop.width * s)), max(inp["size"], round(crop.height * s))), Image.BILINEAR)
    l, t = (im.width - inp["size"]) // 2, (im.height - inp["size"]) // 2
    arr = np.asarray(im.crop((l, t, l + inp["size"], t + inp["size"])), dtype=np.float32) / 255.0
    arr = ((arr - inp["mean"]) / inp["std"]).transpose(2, 0, 1)[None].astype(np.float32)
    logits = ft["session"].run(None, {"input": arr})[0][0]
    p = np.exp(logits - logits.max()); p /= p.sum()
    classes = ft["card"]["classes"]
    top = [{"label": classes[i]["name"], "nutrition_key": classes[i]["nutrition_key"], "score": round(float(p[i]), 3)}
           for i in p.argsort()[::-1][:5]]
    return {"model": "finetuned", "model_name": ft["card"]["name"], "top": top, "min_score": FINETUNED_MIN}


def _classify_imagenet(crop: Image.Image) -> dict:
    import mediapipe as mp
    cats = _state["cls"].classify(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(crop))).classifications[0].categories
    top = [{"label": c.category_name, "nutrition_key": IMAGENET_FOOD.get(c.category_name),
            "is_food": c.category_name in IMAGENET_FOOD, "score": round(float(c.score), 3)} for c in cats]
    return {"model": "imagenet", "model_name": "EfficientNet-Lite0", "top": top[:5], "all": top, "min_score": IMAGENET_MIN}


def _best_food(c: dict, min_score: float | None = None) -> dict | None:
    thr = c["min_score"] if min_score is None else min_score
    pool = c.get("all", c["top"])
    for t in pool:
        if (c["model"] == "finetuned" or t.get("is_food")) and t["score"] >= thr:
            return t
        if c["model"] == "finetuned":
            break  # closed-set model: only accept its top-1
    return None


def _crop(img: Image.Image, box: dict, pad: float = 0.08) -> Image.Image:
    x1 = max(0, (box["x"] - pad * box["w"]) * img.width); y1 = max(0, (box["y"] - pad * box["h"]) * img.height)
    x2 = min(img.width, (box["x"] + box["w"] * (1 + pad)) * img.width); y2 = min(img.height, (box["y"] + box["h"] * (1 + pad)) * img.height)
    return img.crop((int(x1), int(y1), max(int(x2), int(x1) + 8), max(int(y2), int(y1) + 8)))


def _overlay(img: Image.Image, instances: list[dict], path: Path) -> None:
    base = img.convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for k, it in enumerate(i for i in instances if i.get("food")):
        col = PALETTE[k % len(PALETTE)]
        if it.get("mask") is not None:
            m = Image.fromarray((it["mask"] * 110).astype(np.uint8))
            layer.paste(Image.new("RGBA", img.size, col + (110,)), (0, 0), m)
        b = it["bbox"]
        xy = [b["x"] * img.width, b["y"] * img.height, (b["x"] + b["w"]) * img.width, (b["y"] + b["h"]) * img.height]
        draw.rectangle(xy, outline=col + (255,), width=3)
        draw.rectangle([xy[0], max(0, xy[1] - 18), xy[0] + 8 + 7 * len(it["food"]["label"]), xy[1]], fill=col + (230,))
        draw.text((xy[0] + 4, max(0, xy[1] - 16)), it["food"]["label"], fill=(255, 255, 255, 255))
    Image.alpha_composite(base, layer).convert("RGB").save(path, "JPEG", quality=88)


# ---------------------------------------------------------------- pipeline entry
def analyze(path: str, view: str) -> dict:
    with _lock:
        _load()
        if not (_state["seg"] or _state["det"]) or not (_state["cls"] or _state["ft"]):
            return {"view": view, "ok": False, "error": status()["error"], "items": [], "instances": [], "top_labels": []}
        img = Image.open(path).convert("RGB")
        t0 = time.perf_counter()
        dets = _segment(img) if _state["seg"] else _detect_boxes(img)
        t1 = time.perf_counter()

        instances = []
        for d in dets:
            if d["score"] < DET_MIN:
                continue
            kind = "food" if d["label"] in COCO_FOOD else "container" if d["label"] in COCO_DISH_CONTAINERS else \
                "reference" if d["label"] in COCO_REFERENCE else None
            if kind:
                instances.append({**d, "kind": kind})
        scene = {"label": "whole image", "score": 1.0, "bbox": {"x": 0, "y": 0, "w": 1, "h": 1}, "mask": None,
                 "area_frac": 1.0, "kind": "scene"}
        items = []
        for inst in instances + [scene]:
            if inst["kind"] == "reference":
                continue
            c = _classify(img if inst["kind"] == "scene" else _crop(img, inst["bbox"]))
            inst["classification"] = {k: c[k] for k in ("model", "model_name", "top")}
            if c.get("deferred_from"):
                inst["classification"]["deferred_from"] = c["deferred_from"]
            if inst["kind"] == "food":
                best = _best_food(c)
                if c["model"] == "finetuned" and best and best["nutrition_key"]:
                    food = {"label": best["label"], "nutrition_key": best["nutrition_key"], "score": best["score"],
                            "source": "classifier"}
                else:  # detector label is the most reliable evidence for COCO food classes
                    food = {"label": inst["label"], "nutrition_key": COCO_FOOD[inst["label"]], "score": inst["score"],
                            "source": "detector"}
            else:
                best = _best_food(c, SCENE_MIN[c["model"]] if inst["kind"] == "scene" else None)
                food = best and {"label": best["label"], "nutrition_key": best["nutrition_key"], "score": best["score"],
                                 "source": "classifier"}
            inst["food"] = food
            if food:
                items.append({"model_label": food["label"], "nutrition_key": food["nutrition_key"], "score": food["score"],
                              "bbox": None if inst["kind"] == "scene" else inst["bbox"], "area_frac": inst["area_frac"],
                              "instance": inst["kind"], "detector_label": inst["label"], "detector_score": round(inst["score"], 3),
                              "has_mask": inst["mask"] is not None,
                              "model": "detector" if food["source"] == "detector" else "classifier",
                              "model_name": (models()["detector"]["name"] if food["source"] == "detector" else c["model_name"]),
                              "classifier_top": c["top"][:3], "deferred_from": c.get("deferred_from"), "view": view})
        t2 = time.perf_counter()
        overlay = str(Path(path).with_name(f"{view}_overlay.jpg"))
        _overlay(img, instances, Path(overlay))

    refs = [{"label": i["label"], "score": round(i["score"], 3), "bbox": i["bbox"], "area_frac": round(i["area_frac"], 4)}
            for i in instances if i["kind"] in ("reference", "container")]
    return {
        "view": view, "ok": True, "items": items, "containers": refs, "overlay_path": overlay,
        "instances": [{"label": i["label"], "kind": i["kind"], "score": round(i["score"], 3),
                       "area_frac": round(i["area_frac"], 4), "food": i.get("food")} for i in instances],
        "top_labels": [{"label": t["label"], "score": t["score"]} for t in scene["classification"]["top"]],
        "latency_ms": {"detector": round((t1 - t0) * 1000, 1), "classifier": round((t2 - t1) * 1000, 1)},
    }


def merge(results: list[dict]) -> list[dict]:
    """Merge the same food across instances and views; keep the best evidence."""
    merged: dict[str, dict] = {}
    for r in results:
        for it in r["items"]:
            k = it["nutrition_key"] or f"unmapped:{it['model_label']}"
            cur = merged.get(k)
            if cur is None:
                merged[k] = {**it, "views": [it["view"]], "evidence": [it], "instances": 1}
                continue
            cur["evidence"].append(it)
            if it["view"] not in cur["views"]:
                cur["views"].append(it["view"])
            elif it["instance"] != "scene" and cur["instance"] != "scene":
                cur["instances"] += 1  # e.g. two bananas in the same photo
            if it["bbox"] and not cur["bbox"]:
                cur.update(bbox=it["bbox"], area_frac=it["area_frac"], view=it["view"], instance=it["instance"])
            if it["score"] > cur["score"]:
                cur.update(score=it["score"], model_label=it["model_label"], model=it["model"], model_name=it["model_name"])
    return sorted(merged.values(), key=lambda x: -x["score"])
