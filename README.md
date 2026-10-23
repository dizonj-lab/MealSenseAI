# MealSenseAI

An intelligent meal recording system that uses computer vision and pattern recognition to identify food items from images, estimate portion sizes, calculate nutritional content and generate personalised recommendations based on the user's health profile, dietary goals and conditions such as diabetes.

*NUS Graduate Certificate — Problem Solving using Pattern Recognition (PRS) practice module, Group 31. Due 30 Oct 2026.*

## MVP

Photo-based meal logging: **capture (top/side view) → food recognition → portion estimate → user correction → sourced nutrition → glucose & energy insights → history**. Self-hosted, CPU-only, no paid services.

## Quick start (local Ubuntu)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
sudo apt install -y libegl1 libgles2 libgl1 postgresql redis-server   # MediaPipe needs EGL libs
./ml/models/fetch_models.sh
cp .env.example .env            # set JWT_SECRET
sudo -u postgres psql -c "CREATE USER mealsense WITH PASSWORD 'mealsense';" -c "CREATE DATABASE mealsenseai OWNER mealsense;"
(cd frontend && npm ci && npm run build)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open http://localhost:8000 (use your LAN IP from a phone). API docs: `/docs`. Frontend dev server: `cd frontend && npm run dev` (port 5173, proxies `/api`).

**Docker:** `cp .env.example .env && docker compose up --build` (Postgres, Redis, app; uses Ollama on the host via `host.docker.internal`).

**Ollama (optional):** `ollama pull qwen2.5:3b` (any text model works; set `OLLAMA_MODEL` to pin one). Without it, the app uses rule-based fallbacks and says so in the UI.

## Tests
```bash
sudo -u postgres psql -c "CREATE DATABASE mealsenseai_test OWNER mealsense;"
cd backend && pytest -q                                          # API + pipeline tests
python tests/e2e/ui_flow.py http://localhost:8000 /tmp/shots     # mobile UI flow (Playwright)
python ../ml/evaluation/evaluate.py /path/to/food-101/images     # accuracy/P/R/F1 on labeled data
```

## Inference pipeline (see `02-Solution Architecture/`)
| # | Stage | Implementation |
|---|---|---|
| 1 | Meal capture | Mobile camera or upload: top view plus optional side view, description, reference object, serving note |
| 2 | Image pre-processing | Validation, EXIF orientation, RGB, resize to ≤1024 px, originals retained |
| 3 | Food instance detection | **YOLO11n-seg** (COCO, ONNX) instance masks for 10 COCO food classes plus dish containers (bowl, cup); EfficientDet-Lite0 fallback (boxes only) |
| 4 | Food classification | Each instance crop (and the whole image) is classified by the **fine-tuned EfficientNet-B0** from `ml/training`, falling back to ImageNet EfficientNet-Lite0 |
| 5 | Portion estimation | Typical-serving priors (±50%), mask-area ratio against a detected plate or bowl (±35%), instance counts, grams you enter (±15%). **No volume measurement.** |
| 6 | Nutrition mapping | Deterministic lookup in the sourced composition table (`datasets/nutrition/foods.json`, 82 records) |
| 7 | Meal aggregation | Item totals; glycemic load only when published GI covers ≥70% of the carbohydrate |
| 8 | AI contextualisation | Local Ollama SLM explains the computed numbers and your goals; it never produces nutrient values |
| 9 | Recommendations | Rule-based and goal-aware, educational only |
| 10 | Application output | Editable review (confirm, edit food, edit portion, remove, add) with original predictions kept for evaluation |

Training pipeline (`ml/training/`, see its README): validation → label harmonisation → pre-processing → augmentation →
balancing → stratified 70/15/15 split → transfer learning → evaluation (accuracy, P/R/F1, confusion matrix, top-5) → ONNX export.

## Honest scope
- Scores are raw model outputs, **not calibrated**; the UI labels them strong / moderate / weak.
- The COCO detector only knows 10 foods. Hawker dishes therefore depend on the fine-tuned classifier and on its training classes.
- Nutrition values are transcribed approximations (`transcribed_unverified`); replace them with a verified import.
- No personal glucose prediction, no clinical targets, no medication advice.

User corrections (confirm, edit food, edit portion, add, remove) are saved with the original prediction so they can be used for evaluation later.

## Layout
`backend/app/{api,core,models,schemas,services}` · `frontend/src/{pages,components,lib}` · `ml/{models,evaluation}` · `datasets/nutrition` · `infrastructure/Dockerfile`
