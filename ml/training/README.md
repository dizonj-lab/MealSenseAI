# Dataset pre-processing & training pipeline

Implements the *MealSenseAI Dataset Pre-processing and Training Pipeline* diagram. It uses a separate
environment, so the app itself only needs `onnxruntime`.

```bash
python3.12 -m venv .venv-train && .venv-train/bin/pip install -r ml/training/requirements.txt
cd ml/training
../../.venv-train/bin/python prepare_dataset.py            # stages 1-4, 6, 7, 10
../../.venv-train/bin/python train.py                      # stages 5, 6, 8, 9 + ONNX export
../../.venv-train/bin/python export_yolo_seg.py            # instance segmentation model for inference stage 3
```
Restart the app afterwards. It loads `ml/models/food_classifier/` and records the test metrics as an Experiment,
which appears on the **AI Model Insights** page.

| Diagram stage | Where | What |
|---|---|---|
| 1 Data sources | `config.yaml → dataset.sources` | Food-101 (`food-101/images`), FoodSG-233, own images, each as a folder per class |
| 2 Ingestion & validation | `prepare_dataset.py: ingest, validate` | registers source, version and listing hash; integrity (`verify` + decode), format filter, min size, exact (SHA-1) and near (dHash) duplicates, missing labels |
| 3 Label harmonisation | `class_map.json`, `harmonise` | normalises names, maps equivalents (e.g. `hainanese_chicken_rice → chicken_rice`), removes ambiguous labels, merges classes; selects 20–30 MVP classes, Singapore dishes first |
| 4 Image pre-processing | `preprocess` | EXIF orientation, RGB, uniform-border trim, shorter side resized to 256 px (aspect kept); 224 crop and ImageNet mean/std applied at load time |
| 5 Augmentation (train only) | `train.py: transforms` | rotation ±20°, horizontal flip, random crop/zoom, brightness/contrast, colour jitter |
| 6 Balancing | `report.json → balancing`, `train.balancing` | class distribution plot, imbalance ratio, class weights; strategy is weighted sampler, class-weighted loss or oversampling |
| 7 Split | `split` | stratified 70/15/15 with a fixed seed; duplicates are removed before splitting, so none leak across splits |
| 8 Transfer learning | `train.py` | ImageNet EfficientNet-B0 (timm): train the head with the backbone frozen, then fine-tune the last 3 blocks; label smoothing, early stopping on validation macro-F1 |
| 9 Evaluation | `evaluate.py` | accuracy, macro precision/recall/F1, per-class metrics, confusion matrix (PNG + JSON), top-5, latency |
| 10 Training-ready dataset | `datasets/processed/<name>-v<version>/` | processed images, `train/val/test.csv` manifests, `classes.json` (label → nutrition key), `report.json` (configs, validation stats), dataset SHA-256 |
