"""Export EXP-002 (torchvision EfficientNet-B0, 320 classes) to ONNX and record equivalence evidence.

No retraining. Loads the checkpoint with weights_only=True, preserves the class-ID taxonomy exactly,
and measures on real images:
  1. preprocessing parity: app's PIL/NumPy port vs torchvision evaluation transform (max abs diff)
  2. model parity: ONNX Runtime logits vs PyTorch logits (max abs diff, top-1 / top-3 agreement)
Usage (training venv): python ml/export/export_exp002.py [image_dir ...]
"""
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import torch.nn as nn
from PIL import Image, ImageOps
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "ml/models/exp002"
sys.path.insert(0, str(ROOT / "backend"))
from app.services.preprocess import to_input  # noqa: E402  (runtime implementation under test)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    taxonomy = json.loads((M / "class_mapping.json").read_text())
    n = len(taxonomy)
    assert sorted(taxonomy.values()) == list(range(n)), "class IDs must be contiguous"
    ck = torch.load(M / "best_model.pth", map_location="cpu", weights_only=True)
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, n)
    model.load_state_dict(ck["model_state_dict"], strict=True)
    model.eval()

    onnx_path = M / "model.onnx"
    torch.onnx.export(model, torch.randn(1, 3, 224, 224), onnx_path, input_names=["input"], output_names=["logits"],
                      dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17, dynamo=False)
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    tv = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
                             transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    dirs = [Path(a) for a in sys.argv[1:]] or [ROOT / "backend/tests/fixtures"]
    imgs = sorted(p for d in dirs for p in d.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    pre_diff, logit_diff, top1, top3, lat = 0.0, 0.0, 0, 0, []
    for p in imgs:
        im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        x_tv = tv(im).unsqueeze(0)
        x_np = to_input(im)
        pre_diff = max(pre_diff, float(np.abs(x_tv.numpy() - x_np).max()))
        with torch.no_grad():
            lt = model(x_tv).numpy()[0]
        t0 = time.perf_counter()
        lo = sess.run(None, {"input": x_np})[0][0]
        lat.append((time.perf_counter() - t0) * 1000)
        logit_diff = max(logit_diff, float(np.abs(lt - lo).max()))
        top1 += int(lt.argmax() == lo.argmax())
        top3 += int(set(lt.argsort()[-3:]) == set(lo.argsort()[-3:]))
    parity = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "images": len(imgs),
        "image_sources": [str(d.relative_to(ROOT)) if d.is_relative_to(ROOT) else str(d) for d in dirs],
        "preprocessing_max_abs_diff": pre_diff, "logits_max_abs_diff": logit_diff,
        "top1_agreement": top1 / len(imgs), "top3_set_agreement": top3 / len(imgs),
        "onnxruntime_cpu_latency_ms_avg": round(sum(lat) / len(lat), 2),
        "torch": torch.__version__, "onnxruntime": ort.__version__, "python": platform.python_version(),
    }
    (M / "evidence").mkdir(exist_ok=True)
    (M / "evidence/onnx_parity.json").write_text(json.dumps(parity, indent=2))
    print(json.dumps(parity, indent=2))
    print("sha256 best_model.pth", sha256(M / "best_model.pth"))
    print("sha256 model.onnx     ", sha256(onnx_path))


if __name__ == "__main__":
    main()
