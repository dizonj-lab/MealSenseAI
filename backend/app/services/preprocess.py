"""Exact port of the EXP-002 evaluation transform (ml/models/exp002/preprocessing.py) without torch:

    Resize(256) -> CenterCrop(224) -> ToTensor() -> Normalize(ImageNet mean/std)

Mirrors torchvision's PIL code path: shorter side to 256 with int() truncation for the longer side,
bilinear (antialiased) PIL resize, round()-based centre-crop offsets. Equivalence with torchvision is
measured by ml/export/export_exp002.py and recorded in ml/models/exp002/evidence/onnx_parity.json.
"""
import numpy as np
from PIL import Image

RESIZE, CROP = 256, 224
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def resize_shorter(img: Image.Image, size: int = RESIZE) -> Image.Image:
    w, h = img.size
    short, long = (w, h) if w <= h else (h, w)
    if short == size:
        return img
    new_short, new_long = size, int(size * long / short)
    new_w, new_h = (new_short, new_long) if w <= h else (new_long, new_short)
    return img.resize((new_w, new_h), Image.BILINEAR)


def center_crop(img: Image.Image, size: int = CROP) -> Image.Image:
    w, h = img.size
    top, left = int(round((h - size) / 2.0)), int(round((w - size) / 2.0))
    return img.crop((left, top, left + size, top + size))


def to_input(img: Image.Image) -> np.ndarray:
    """PIL RGB image -> float32 NCHW tensor, identical to the evaluation transform."""
    x = np.asarray(center_crop(resize_shorter(img.convert("RGB"))), dtype=np.float32) / 255.0
    return ((x - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)
