"""Stage 1: image validation and preprocessing. Originals are retained untouched."""
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:  # HEIC support is optional
    pass

MAX_SIDE = 1024
ALLOWED = {"JPEG", "PNG", "WEBP", "HEIF", "MPO"}


class ImageError(ValueError):
    pass


def process(raw: bytes, out_dir: Path, view: str) -> dict:
    try:
        img = Image.open(io.BytesIO(raw))
        fmt = img.format
        img.load()
    except (UnidentifiedImageError, OSError):
        raise ImageError(f"{view}: file is not a readable image")
    if fmt not in ALLOWED:
        raise ImageError(f"{view}: unsupported format {fmt}")

    out_dir.mkdir(parents=True, exist_ok=True)
    ext = {"JPEG": "jpg", "MPO": "jpg", "PNG": "png", "WEBP": "webp", "HEIF": "heic"}[fmt]
    orig_path = out_dir / f"{view}_original.{ext}"
    orig_path.write_bytes(raw)

    orig_size = img.size
    exif_orientation = img.getexif().get(0x0112, 1)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    proc_path = out_dir / f"{view}.jpg"
    img.save(proc_path, "JPEG", quality=90)

    arr = np.asarray(img.convert("L"), dtype=np.float32)
    brightness = float(arr.mean())
    lap = arr[1:-1, 1:-1] * -4 + arr[:-2, 1:-1] + arr[2:, 1:-1] + arr[1:-1, :-2] + arr[1:-1, 2:]
    sharpness = float(lap.var())
    warnings = []
    if min(orig_size) < 224:
        warnings.append("Low resolution; recognition may be unreliable")
    if brightness < 40:
        warnings.append("Image is very dark")
    elif brightness > 235:
        warnings.append("Image is overexposed")
    if sharpness < 20:
        warnings.append("Image appears blurry")
    return {
        "view": view, "path": str(proc_path), "original_path": str(orig_path), "format": fmt,
        "original_size": list(orig_size), "processed_size": list(img.size),
        "orientation_corrected": exif_orientation != 1,
        "quality": {"brightness": round(brightness, 1), "sharpness": round(sharpness, 1)},
        "warnings": warnings,
    }
