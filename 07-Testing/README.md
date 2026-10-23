# 07 · Testing

## One-command test environment (Docker)
```bash
./infrastructure/test.sh            # build, run all tests, tear down
KEEP=1 ./infrastructure/test.sh     # ...and keep the test stack at http://localhost:8081 with a seeded demo user
```
It uses a separate Compose project (`mealsenseai-test`) with throwaway databases (tmpfs), so it never touches your real data.

| Step | What it checks |
|---|---|
| `api-tests` (pytest, 7 tests) | health; register/login/401s; consent-based data minimisation; **real model inference** on a photo; unsupported image → manual entry; edit portion/food → recalculation; add/remove; confirm; history; dashboard; corrections log; owner-only images; capture validation; portion maths (box/mask ratio, instance counts) |
| `e2e` (Playwright, Chromium, 390×844 phone viewport) | register → onboarding (4 steps) → capture with photo + description → 10-stage analysis → edit portion → add food → save → history → dashboard → AI insights → nutrition insights → menu drawer → desktop login and meal view, all **through the nginx proxy**; fails on any JS error |
| health | DB, Redis, vision models loaded |

Screenshots: `test-results/screenshots/`.

## Model evaluation
- Classifier (held-out test split): `ml/training/train.py` writes `metrics.json` and `confusion_matrix.png`.
- Whole pipeline: `python ml/evaluation/evaluate.py datasets/processed/<ds> --manifest test.csv`.
Results are stored as Experiments and shown on the **AI Model Insights** page.

## Without Docker
`cd backend && pytest -q` (needs local Postgres with a `mealsenseai_test` database), then
`python tests/e2e/ui_flow.py http://localhost:8000 /tmp/shots`.
