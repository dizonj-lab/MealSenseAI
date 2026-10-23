# 05 · Infrastructure

| Service | Build | Role |
|---|---|---|
| `frontend` | `frontend/Dockerfile` (node build → nginx 1.27) | React UI and reverse proxy, port **8080** |
| `backend` | `backend/Dockerfile` (`cpu` default, `gpu` optional) | FastAPI, EXP-002 classifier, YOLO-seg, nutrition and insights, Alembic migrations |
| `db` | postgres:16-alpine | Persistent data (volume `pgdata`) |
| `init-perms` | backend image | One-shot fix of photo-volume ownership (volume `uploads`) |
| `redis` (profile `cache`), `ollama` (profile `slm`) | official images | Optional |

Compose files:
- `docker-compose.yml`: CPU default.
- `docker-compose.gpu.yml`: NVIDIA option.
- `docker-compose.offline.yml`: verification with no internet access.
- `docker-compose.test.yml`: isolated test stack.
- `docker-compose.home.yml`: home-server hosting behind Cloudflare Tunnel; see `08-Deployment/HOME-SERVER.md`.

Run with `./scripts/start.sh [--gpu] [--demo]` and stop with `./scripts/stop.sh`. Details: `docs/INSTALL_AND_TROUBLESHOOTING.md`.
