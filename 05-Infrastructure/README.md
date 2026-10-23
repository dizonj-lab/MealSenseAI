# 05 · Infrastructure (local Docker)

Everything runs on one machine with Docker Compose. Logical services match the infrastructure-layer slide:

| Service | Image | Role |
|---|---|---|
| `proxy` | nginx 1.27 | Reverse proxy, single entry point on **http://localhost:8080** |
| `app` | `infrastructure/Dockerfile` (Ubuntu 24.04, Python 3.12) | Web UI + FastAPI API + vision inference (YOLO11n-seg, fine-tuned EfficientNet-B0, MediaPipe) on CPU |
| `db` | postgres 16 | Users, health profiles, meals, corrections, inference logs, experiments |
| `redis` | redis 7 | Cache for nutrition lookups and SLM responses |
| `ollama` (profile `slm`) | ollama/ollama 0.12.6 | Optional local SLM for explanations |
| volumes | `pgdata`, `redisdata`, `uploads`, `ollama` | Persistent data; `uploads` is the local image (object) store |
| `./ml/models` (bind, read-only) | — | Model store: retrain, then `docker compose restart app` |

## Run
```bash
git clone https://github.com/dizonj-lab/MealSenseAI.git && cd MealSenseAI
git checkout claude/mealsenseai-mvp
cp .env.example .env                          # optional: JWT_SECRET, POSTGRES_PASSWORD, HTTP_PORT
docker compose up -d --build                  # first build ~5-10 min
open http://localhost:8080                    # phone on the same Wi-Fi: http://<your-PC-IP>:8080
docker compose exec app python -m app.seed    # optional demo user: demo@mealsense.ai / demo12345
```

**SLM options**
- You already run Ollama on the host: nothing to do. The app calls `http://host.docker.internal:11434` and picks an installed text model.
- Run it in Docker instead: set `OLLAMA_URL=http://ollama:11434` in `.env`, then `docker compose --profile slm up -d` (this pulls `qwen2.5:1.5b`; change it with `OLLAMA_PULL_MODEL`).
- No Ollama at all: the app shows "Vision only" and uses the rule-based explanations.

## Operate
```bash
docker compose ps                  # health of every service
docker compose logs -f app         # API / inference logs
docker compose restart app         # reload models after retraining
docker compose down                # stop (data kept)
docker compose down -v             # stop and DELETE all data
```
