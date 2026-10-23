# MealSenseAI — Architecture

## Containers (Docker Compose)

```
 Browser (phone / laptop)
        │ HTTP :8080
 ┌──────▼──────────────────────┐
 │ frontend  (nginx 1.27)      │  React + TypeScript UI (static build), reverse proxy for /api, rate limits,
 │ frontend/Dockerfile         │  security headers. Single entry point.
 └──────┬──────────────────────┘
        │ /api/v1/*
 ┌──────▼──────────────────────┐
 │ backend   (Python 3.12)     │  FastAPI REST API (OpenAPI at /docs), Alembic migrations on start,
 │ backend/Dockerfile          │  EXP-002 food classifier + YOLO11n-seg (ONNX Runtime, CPU default / CUDA optional),
 │                             │  portions, nutrition mapping, diabetes-aware insights, forecast.
 └──────┬──────────────────────┘
        │ SQL                         volumes:  pgdata  (database)
 ┌──────▼──────────────────────┐                uploads (meal photos)
 │ db        (PostgreSQL 16)   │
 └─────────────────────────────┘
 Optional profiles:  cache → Redis 7   ·   slm → Ollama (local language model for explanations)
```

Deliberately not split further: one backend process holds the API and the models. Models load once at start-up and take
about 12 ms per photo on a CPU. No message queue or separate model server is needed at MVP scale.

| Concern | Choice |
|---|---|
| Inference device | `INFERENCE_DEVICE=auto` (default): CUDA if the GPU image and an NVIDIA GPU are present, otherwise CPU. `docker-compose.gpu.yml` builds the `gpu` target with `onnxruntime-gpu`. |
| Model files | Copied into the backend image at build time (`ml/models/exp002/`, `ml/models/yolo11n-seg.onnx`). Nothing is downloaded at runtime. |
| Database schema | Alembic migrations in `backend/migrations/` run on every start (idempotent). Snapshot: `database/schema.sql`. |
| Reference data | `datasets/nutrition/foods.json` (281 records, provenance per record) and `ml/models/exp002/nutrition_map.json` (class to nutrition record). |
| External services | None required. The optional SLM (Ollama) is local; when it is absent, the rule-based explanations are used. |
| Security | bcrypt password hashes, JWT bearer tokens, owner-only photo access, non-root backend container, nginx rate limits. |

## Inference pipeline (10 stages, shown live in the UI)

| # | Stage | Implementation | Output type |
|---|---|---|---|
| 1 | Meal capture | Camera or upload (top view plus optional side view), optional description, reference object, serving note | user input |
| 2 | Image pre-processing | Validation, EXIF orientation, originals kept; a ≤1024 px display copy | — |
| 3 | Food instance detection | YOLO11n-seg (COCO) outlines food items and bowls or cups; a supporting step | model prediction |
| 4 | Food classification | **EXP-002 EfficientNet-B0, 320 classes**, whole photo with the exact evaluation preprocessing, **top-3 candidates**. Confident crops (≥0.60) can propose a second dish. Below 0.20 nothing is auto-added and the user picks. | model prediction |
| 5 | Portion estimation | Typical-serving prior (±50%), mask-area ratio against a plate or bowl (±35%), or grams entered by the user (±15%) | estimate / user input |
| 6 | Nutrition mapping | Class to record via `nutrition_map.json`: **exact**, **proxy** ("approximated using …") or **none** (user chooses) | nutritional estimate |
| 7 | Meal aggregation | Sums; glycaemic load only when published GI covers ≥70% of the carbohydrate | nutritional estimate |
| 8 | AI contextualisation | Optional local SLM explanation of the numbers; otherwise the rule engine | unvalidated guidance |
| 9 | Recommendations | Rule-based and goal-aware: diabetes cautions, meal advisory, what-if activity forecast | unvalidated guidance |
| 10 | Application output | Editable review: confirm, override (top-3 or search), change portion, add or remove; corrections are logged | — |

**Human in the loop:** every model output can be overridden. The original prediction is stored next to the user's
final choice (`meal_foods.original_prediction`, `meal_foods.taxonomy_class`, `corrections`). This creates labelled
data for future evaluation.

## Code map

```
backend/app/
  api/        auth, users (profile), meals (capture/analyze/edit/confirm/forecast/history), dashboard, ai (models, taxonomy)
  core/       config, db, migrate (Alembic runner), security (JWT/bcrypt), cache
  models/     SQLAlchemy tables: users, health_profiles, meals, meal_foods, corrections, inference_logs, experiments
  services/   preprocess (exact EXP-002 transform), vision (classifier + detector), portion, nutrition,
              insights (glucose/energy/recommendations), forecast (activity what-if), analysis (orchestrator), slm
backend/migrations/   0001 initial schema, 0002 taxonomy_class
frontend/src/         pages (Dashboard, Capture, History, Insights, Profile, AI Model Insights, Settings), components
ml/models/exp002/     best_model.pth (source of truth), model.onnx, class_mapping.json, preprocessing.py,
                      nutrition_map.json, model_card.json, evidence/
ml/export/            export_exp002.py (ONNX + parity evidence), build_nutrition_map.py, build_model_card.py
```

## Data model (PostgreSQL)

`users` 1–1 `health_profiles` (health fields stored only with consent) · `users` 1–n `meals` 1–n `meal_foods`
(label, taxonomy class, nutrition key, match type, grams, portion method and uncertainty, nutrients, source, original
prediction) · `corrections` (before/after of every user edit) · `inference_logs` (model, device, latency) ·
`experiments` (reported metrics and parity evidence). The full DDL is in `database/schema.sql`.
