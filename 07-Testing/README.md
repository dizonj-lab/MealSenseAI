# 07 · Testing

| Command | What it checks |
|---|---|
| `./scripts/acceptance.sh [--offline] [--image photo.jpg]` | NUS acceptance tests 1, 3–10 against the real Compose stack, including restart persistence and the offline mode |
| `./scripts/test.sh` | Isolated stack: 15 pytest API/pipeline tests and a Playwright phone-sized UI flow through nginx |
| `cd backend && pytest -q` | API tests without Docker (needs local Postgres with a `mealsenseai_test` database) |
| `python ml/export/export_exp002.py <image dirs>` | ONNX vs PyTorch parity and exact-preprocessing evidence |
| `python ml/evaluation/evaluate.py <labelled dir>` | Pipeline accuracy on labelled photos |

Actual results from this build: `docs/TEST_REPORT.md`.
