# Model, data provenance and limitations

## The model: EXP-002

| Item | Value |
|---|---|
| Architecture | torchvision `efficientnet_b0`, classifier `Linear(1280, 320)` |
| Lineage | EXP-001 (ImageNet-initialised, unified Food-101 + FoodSG taxonomy), then EXP-002 partial fine-tuning (last 3 feature blocks + head, 5 epochs). **Not retrained for deployment.** |
| Classes | 320 canonical classes, IDs 0–319, taxonomy file `ml/models/exp002/class_mapping.json` (unchanged, SHA-256 `05d355e9…`) |
| Checkpoint | `ml/models/exp002/best_model.pth`, SHA-256 `4c9b30c057f893fc6e955282e73dc2767dede0d365a2cad500e4334d950ff2f6` |
| Runtime artefact | `model.onnx`, exported from the checkpoint by `ml/export/export_exp002.py` (opset 17) |
| Preprocessing | Resize 256 (shorter side) → centre crop 224 → ImageNet mean/std, as in `preprocessing.py` |

### Metrics and where each number comes from
| Metric | Value | Provenance |
|---|---|---|
| Top-1 accuracy | 70.63% | Reported by the developer from the EXP-002 evaluation. The evaluation evidence files are on the development workstation and were not in the model archive. |
| Top-3 accuracy | 85.66% | Same as above |
| Macro-F1 | 66.68% | Same as above |
| Validation macro-F1 | 66.29% | Stored inside `best_model.pth` (epoch 5) |
| Runtime equivalence | Preprocessing max abs diff **0.0**, logits max abs diff **1.35e-4**, top-1 and top-3 agreement **100%** on 601 images | **Measured** in this package (`evidence/onnx_parity.json`): ONNX Runtime + `services/preprocess.py` against PyTorch + torchvision |
| CPU latency | ≈12 ms per photo (classifier only, ONNX Runtime, 4-vCPU sandbox) | Measured |

The parity images include a Food-101 subset that the model probably saw in training. They show that the deployed
runtime reproduces the checkpoint; they are **not** an accuracy measurement.

## Nutrition data provenance
| Source | Records | Status |
|---|---|---|
| USDA FoodData Central-style values (generic foods) | part of 82 original records | `transcribed_unverified` |
| Singapore HPB Energy & Nutrient Composition (hawker dishes, per-serving converted to per 100 g) | part of 82 | `transcribed_unverified` |
| MealSenseAI approximations added for EXP-002 coverage (typical recipes) | 199 | `approximate_unverified` |

Class mapping (`nutrition_map.json`): **247 exact**, **66 proxy** (nearest food, shown as "approximated using …"),
**7 none** (bruschetta, cheese plate, drunken prawn, escargots, foie gras, seaweed snack, shrimp and grits). These need a
manual choice.

## How the UI separates kinds of information
| Tag in the UI | Meaning |
|---|---|
| **Model prediction** | Classifier candidates and raw scores (uncalibrated softmax) |
| **Your input** | Values the user entered, e.g. weighed grams |
| **Estimate** | Portions from typical servings or area ratios, and nutrients from reference tables |
| **Unvalidated guidance** | Recommendations, meal advisory, activity forecast; educational, not clinically validated |

## Limitations
1. **Accuracy:** roughly 3 in 10 photos get a wrong top-1 class (developer-reported top-1 70.6%), and about 14% miss
   all top-3 candidates. Users must confirm. Visually similar hawker dishes (noodle soups, rice plates) are the
   typical confusions.
2. **Closed vocabulary:** foods outside the 320 classes are always mislabelled as the nearest class. Below a 0.20 score
   nothing is auto-added; between 0.20 and 0.50 the item is marked "low confidence — please check".
3. **Scores are not calibrated** probabilities and must not be read as "% sure".
4. **Mixed plates:** the model classifies the whole photo (as in its training). Detection crops can add a second dish
   only for COCO-detectable regions with a confident, different class. Mixed rice (cai fan) is not decomposed.
5. **Portions are estimates.** Photos without a calibrated scale or depth cannot measure volume (±35–50% bands).
   Entering grams is the accurate path.
6. **Nutrition values are unverified** transcriptions or approximations. Replace them with a verified import (e.g.
   HPB SG FoodID, USDA FDC) before any clinical use.
7. **Glucose and forecast** use population-average physiology (relative index, not mmol/L). They do not predict an
   individual's glucose response, do not model insulin dosing (type 1), and are not medical advice.
8. **Accuracy evidence is reported, not reproduced here:** the original datasets are excluded from this package, so
   EXP-002 accuracy cannot be re-measured without them. `ml/evaluation/evaluate.py` re-measures it on a labelled folder.
9. **GPU path:** the `gpu` image target (CUDA 12.8 + cuDNN 9 + onnxruntime-gpu) has not been built or run in the test
   environment (no GPU, insufficient disk). CPU is the tested default.
10. **YOLO11n-seg licence:** Ultralytics YOLO is AGPL-3.0. Distributing or serving the app publicly with it requires
    AGPL-compatible terms. Detection is optional; deleting `yolo11n-seg.onnx` disables it, and classification still works.
