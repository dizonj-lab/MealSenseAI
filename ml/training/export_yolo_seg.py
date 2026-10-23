"""Export the YOLO11n-seg (COCO) instance segmentation model to ONNX for the app (onnxruntime, no torch at runtime).
Usage: python ml/training/export_yolo_seg.py [--weights ml/models/yolo11n-seg.pt]
Weights: https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-seg.pt (AGPL-3.0)
To use a food-specific segmenter, fine-tune with Ultralytics on a food segmentation dataset (e.g. FoodSeg103)
and export the same way; the app reads class names from the ONNX metadata.
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]

ap = argparse.ArgumentParser()
ap.add_argument("--weights", default=str(ROOT / "ml/models/yolo11n-seg.pt"))
a = ap.parse_args()
out = YOLO(a.weights).export(format="onnx", imgsz=640, opset=17, simplify=False, dynamic=False)
dst = ROOT / "ml/models" / Path(out).name
if Path(out).resolve() != dst.resolve():
    shutil.copy(out, dst)
print("exported", dst)
