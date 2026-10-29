"""Write ml/models/exp002/model_card.json: identity, checksums, taxonomy, preprocessing, metrics with provenance."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "ml/models/exp002"


def sha(p):
    return hashlib.sha256((M / p).read_bytes()).hexdigest()


tax = json.loads((M / "class_mapping.json").read_text())
nmap = json.loads((M / "nutrition_map.json").read_text())
card = {
    "name": "MealSenseAI EXP-002 EfficientNet-B0",
    "version": "EXP-002_FineTuning",
    "task": "food image classification (320 canonical classes)",
    "architecture": "torchvision efficientnet_b0, classifier[1] = Linear(1280, 320)",
    "lineage": "EXP-001_UnifiedFood (ImageNet-initialised) -> EXP-002 partial fine-tuning (last 3 feature blocks + head)",
    "training_data": ["Food-101", "FoodSG"],
    "files": {
        "best_model.pth": {"sha256": sha("best_model.pth"), "role": "source of truth (PyTorch state_dict)"},
        "model.onnx": {"sha256": sha("model.onnx"), "role": "runtime artefact exported by ml/export/export_exp002.py"},
        "class_mapping.json": {"sha256": sha("class_mapping.json"), "role": "canonical taxonomy (class name -> class id)"},
    },
    "num_classes": len(tax),
    "classes": [{"id": i, "name": n, **{k: nmap[n][k] for k in ("nutrition_key", "match")}}
                for n, i in sorted(tax.items(), key=lambda kv: kv[1])],
    "input": {"resize": 256, "size": 224, "layout": "NCHW", "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225],
              "implementation": "backend/app/services/preprocess.py (bit-identical to preprocessing.py; see evidence)"},
    "metrics": {
        "reported_by_developer": {"top1_accuracy": 0.7063, "top3_accuracy": 0.8566, "macro_f1": 0.6668,
                                  "source": "EXP-002 test set (45,800 images), evaluated on Buddy's GPU; evidence/training/EXP-002_FineTuning/evaluation"},
        "checkpoint_metadata": {"epoch": 5, "validation_macro_f1": 0.6628635553920498,
                                "source": "stored inside best_model.pth"},
        "measured_in_this_package": "see evidence/onnx_parity.json (runtime equivalence, not accuracy)",
    },
    "score_calibrated": False,
    "auto_accept_min_score": 0.5,
    "evidence": ["evidence/onnx_parity.json", "evidence/nutrition_coverage.json", "evidence/train_finetune.py"],
}
(M / "model_card.json").write_text(json.dumps(card, indent=1, ensure_ascii=False))
print("model_card.json written:", card["num_classes"], "classes")
