# 04 · Machine Learning

- **Deployed classifier:** `ml/models/exp002/`. EXP-002 EfficientNet-B0, 320 classes (Food-101 + FoodSG), checkpoint,
  ONNX export, taxonomy, nutrition map, model card and evidence. See `docs/MODEL_AND_LIMITATIONS.md`.
- **Export and equivalence evidence:** `ml/export/export_exp002.py`, `build_nutrition_map.py`, `build_model_card.py`
- **Supporting detector:** `ml/models/yolo11n-seg.onnx` (COCO), with `ml/training/export_yolo_seg.py`
- **Dataset and training pipeline** (validation, harmonisation, augmentation, balancing, split, transfer learning,
  evaluation): `ml/training/`
- **Pipeline evaluation on labelled images:** `ml/evaluation/evaluate.py`
- **Nutrition reference data:** `datasets/nutrition/`. Group nutrition CSVs are in `FINAL FOOD DATASET/` (not used by the app).
