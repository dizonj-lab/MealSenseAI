"""Stage 2: food recognition with verified pretrained MediaPipe models (CPU, TFLite).

- EfficientNet-Lite0 image classifier trained on ImageNet-1k (~45 food-related classes).
- EfficientDet-Lite0 object detector trained on COCO-2017 (10 food classes, bounding boxes).
These are general-purpose models, NOT food-specialised: most Singapore dishes are outside
their vocabulary. Scores are raw softmax/sigmoid outputs and are NOT calibrated probabilities.
"""
import logging
import threading
import time

import numpy as np
from PIL import Image

from app.core.config import settings

log = logging.getLogger(__name__)

# model label -> nutrition table key
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
    "hot pot": None, "chocolate sauce": None, "dough": None,  # food, but no reliable composition match
}
COCO_FOOD = {
    "banana": "banana", "apple": "apple", "sandwich": "sandwich", "orange": "orange",
    "broccoli": "broccoli", "carrot": "carrot", "hot dog": "hot_dog", "pizza": "pizza",
    "donut": "donut", "cake": "chocolate_cake",
}
COCO_CONTAINERS = {"bowl", "cup", "wine glass", "bottle", "dining table", "fork", "knife", "spoon"}

MODELS = {
    "classifier": {"name": "EfficientNet-Lite0", "version": "mediapipe-float32-latest",
                   "file": "efficientnet_lite0.tflite", "trained_on": "ImageNet-1k",
                   "task": "image classification", "food_classes": sum(1 for v in IMAGENET_FOOD.values() if v)},
    "detector": {"name": "EfficientDet-Lite0", "version": "mediapipe-float32-latest",
                 "file": "efficientdet_lite0.tflite", "trained_on": "COCO-2017",
                 "task": "object detection", "food_classes": len(COCO_FOOD)},
}
CLS_MIN = 0.12
DET_MIN = 0.35

_lock = threading.Lock()
_cls = _det = None
_load_error: str | None = None


def _load():
    global _cls, _det, _load_error
    if _cls is not None or _load_error:
        return
    try:
        from mediapipe.tasks.python import BaseOptions, vision as mpv
        d = settings.models_dir
        _cls = mpv.ImageClassifier.create_from_options(mpv.ImageClassifierOptions(
            base_options=BaseOptions(model_asset_path=str(d / MODELS["classifier"]["file"])), max_results=10))
        _det = mpv.ObjectDetector.create_from_options(mpv.ObjectDetectorOptions(
            base_options=BaseOptions(model_asset_path=str(d / MODELS["detector"]["file"])),
            max_results=15, score_threshold=0.25))
    except Exception as e:  # missing files / runtime libs
        _load_error = f"{type(e).__name__}: {e}"
        log.exception("vision models failed to load")


def close():
    global _cls, _det
    with _lock:
        for m in (_cls, _det):
            if m is not None:
                m.close()
        _cls = _det = None


def status() -> dict:
    with _lock:
        _load()
    return {"available": _cls is not None, "error": _load_error, "models": MODELS}


def score_band(score: float) -> str:
    return "strong" if score >= 0.6 else "moderate" if score >= 0.3 else "weak"


def analyze(path: str, view: str) -> dict:
    import mediapipe as mp

    with _lock:
        _load()
        if _cls is None:
            return {"view": view, "ok": False, "error": _load_error, "items": [], "top_labels": []}
        img = Image.open(path).convert("RGB")
        w, h = img.size
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(img))
        t0 = time.perf_counter()
        cls = _cls.classify(mp_img).classifications[0].categories
        t1 = time.perf_counter()
        dets = _det.detect(mp_img).detections
        t2 = time.perf_counter()

    items, containers = [], []
    for d in dets:
        c = d.categories[0]
        b = d.bounding_box
        box = {"x": b.origin_x / w, "y": b.origin_y / h, "w": b.width / w, "h": b.height / h}
        if c.category_name in COCO_FOOD and c.score >= DET_MIN:
            items.append({"model_label": c.category_name, "nutrition_key": COCO_FOOD[c.category_name],
                          "score": round(float(c.score), 3), "bbox": box, "model": "detector", "view": view})
        elif c.category_name in COCO_CONTAINERS and c.score >= DET_MIN:
            containers.append({"label": c.category_name, "score": round(float(c.score), 3), "bbox": box})
    for c in cls:
        if c.category_name in IMAGENET_FOOD and c.score >= CLS_MIN:
            items.append({"model_label": c.category_name, "nutrition_key": IMAGENET_FOOD[c.category_name],
                          "score": round(float(c.score), 3), "bbox": None, "model": "classifier", "view": view})
    return {
        "view": view, "ok": True, "items": items, "containers": containers,
        "top_labels": [{"label": c.category_name, "score": round(float(c.score), 3)} for c in cls[:5]],
        "latency_ms": {"classifier": round((t1 - t0) * 1000, 1), "detector": round((t2 - t1) * 1000, 1)},
    }


def merge(results: list[dict]) -> list[dict]:
    """Merge predictions of the same food across models and views; keep the best evidence."""
    merged: dict[str, dict] = {}
    for r in results:
        for it in r["items"]:
            k = it["nutrition_key"] or f"unmapped:{it['model_label']}"
            cur = merged.get(k)
            if cur is None:
                merged[k] = {**it, "views": [it["view"]], "evidence": [it]}
                continue
            cur["evidence"].append(it)
            if it["view"] not in cur["views"]:
                cur["views"].append(it["view"])
            if it["bbox"] and not cur["bbox"]:
                cur["bbox"], cur["view"] = it["bbox"], it["view"]
            if it["score"] > cur["score"]:
                cur.update(score=it["score"], model_label=it["model_label"], model=it["model"])
    return sorted(merged.values(), key=lambda x: -x["score"])
