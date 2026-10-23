# MealSenseAI

An intelligent meal recording system that uses computer vision and pattern recognition to identify food items from
images, estimate portion sizes, calculate nutritional content, and generate personalised recommendations based on the
user's health profile, dietary goals and conditions such as diabetes.

*NUS Graduate Certificate — Problem Solving using Pattern Recognition (PRS) practice module.*

## Quick start (CPU, any computer with Docker)
```bash
./scripts/start.sh --demo        # builds on first run (internet needed only for the build), then http://localhost:8080
                                 # demo login: demo@mealsense.ai / demo12345
./scripts/acceptance.sh          # acceptance tests, incl. restart persistence (add --offline to cut internet access)
./scripts/stop.sh                # stop (data kept)
```
GPU (optional, NVIDIA): `./scripts/start.sh --gpu`. Details: [docs/INSTALL_AND_TROUBLESHOOTING.md](docs/INSTALL_AND_TROUBLESHOOTING.md).

## What it does
Login and onboarding → health profile (diabetes context, consent-based) → meal photo → **EXP-002 food classifier
(320 classes, top-3 candidates)** → confirm or override → portion estimate with manual correction → nutrition with
provenance (exact / proxy / none) → diabetes-aware insights, meal advisory and activity what-if → history and dashboard.
The UI labels each value as a *model prediction*, *your input*, an *estimate* or *unvalidated guidance*.

| Document | Content |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Containers, 10-stage pipeline, code map, data model |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | How to use the app |
| [docs/INSTALL_AND_TROUBLESHOOTING.md](docs/INSTALL_AND_TROUBLESHOOTING.md) | Prerequisites, install, configuration, troubleshooting |
| [docs/MODEL_AND_LIMITATIONS.md](docs/MODEL_AND_LIMITATIONS.md) | EXP-002 model card, metric provenance, nutrition provenance, limitations |
| [docs/TEST_REPORT.md](docs/TEST_REPORT.md) | Actual test results and outstanding issues |
| [database/schema.sql](database/schema.sql) | Database schema (created by Alembic migrations in `backend/migrations/`) |
| [08-Deployment/HOME-SERVER.md](08-Deployment/HOME-SERVER.md) | Development hosting on the Ubuntu GPU server (Cloudflare Tunnel, hardening, backups) |

## Repository layout
`backend/` FastAPI + migrations + tests · `frontend/` React UI + nginx · `ml/models/exp002/` deployed model and
evidence · `ml/export/` export and parity tools · `ml/training/` dataset and training pipeline ·
`datasets/nutrition/` reference nutrition data · `scripts/` start/stop/test/acceptance/packaging ·
`docker-compose*.yml` deployment variants · `0x-*/` project report sections.

## Disclaimer
Educational estimates only. MealSenseAI does not diagnose, predict an individual's blood glucose, or replace advice
from a doctor, dietitian or diabetes care team.
