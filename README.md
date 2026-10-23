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

## What the AI actually is (honest scope)
| Component | Implementation | Limits |
|---|---|---|
| Recognition | MediaPipe **EfficientNet-Lite0** (ImageNet-1k, ~40 food classes) + **EfficientDet-Lite0** (COCO, 10 food classes, bounding boxes) | General-purpose models; **most Singapore dishes are not recognisable**, so use the description or manual entry. Scores are raw, **not calibrated**; the UI shows strong / moderate / weak. |
| Portions | Typical-serving priors (±50%), area ratio against a detected plate/bowl when a reference is selected (±35%), grams you enter (±15%) | **No volume or depth measurement** from two photos. |
| Nutrition | 81-record table (`datasets/nutrition/foods.json`): USDA FDC-style values plus Singapore HPB hawker dishes | Values are **transcribed approximations** (`transcribed_unverified`); replace them with a verified import before relying on them. |
| Glucose insight | Composition-based: available carbs, sugar, fibre, glycemic load only when published GI covers ≥70% of the carbs, else UNCERTAIN | Does not predict an individual's glucose response. |
| SLM | Ollama (text only): description parsing, provisional matches labeled *unverified*, grounded explanations | Never used for nutrient numbers or vision. |
| Evaluation | `ml/evaluation/evaluate.py` stores accuracy, precision, recall, F1, latency and throughput as Experiments | **No accuracy has been measured yet** (Food-101 was not available in the build environment). |

User corrections (confirm, edit food, edit portion, add, remove) are saved with the original prediction so they can be used for evaluation later.

## Layout
`backend/app/{api,core,models,schemas,services}` · `frontend/src/{pages,components,lib}` · `ml/{models,evaluation}` · `datasets/nutrition` · `infrastructure/Dockerfile`
