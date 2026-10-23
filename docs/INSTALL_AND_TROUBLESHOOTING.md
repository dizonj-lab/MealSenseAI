# Installation and troubleshooting

## Prerequisites
| Item | Requirement |
|---|---|
| OS | Ubuntu 22.04/24.04, macOS 13+ (Apple Silicon or Intel), or Windows 11 with WSL2 |
| Docker | Docker Engine 24+ with Compose v2.24+ (`docker compose version`), or Docker Desktop |
| Hardware | 2 CPU cores, 4 GB RAM, 5 GB free disk. **No GPU needed.** |
| Network | Needed **only to build** the images the first time (base images, Python and npm packages). Running the app needs no internet. |
| Tools | `bash`, `curl`, `python3` (only for `scripts/acceptance_test.py`) |

## Install and run (CPU, default)
```bash
cd MealSenseAI-NUS-Submission        # or the repository root
./scripts/start.sh --demo            # first run builds images (about 5–10 min), creates .env, seeds a demo account
# open http://localhost:8080   (demo@mealsense.ai / demo12345)
./scripts/stop.sh                    # stop, keep data
./scripts/stop.sh --wipe             # stop and delete all data
```
To do it by hand: `cp .env.example .env`, edit `JWT_SECRET`, then `docker compose up -d --build`.

## Optional: NVIDIA GPU (development workstation)
Requires an NVIDIA driver (570+ for RTX 50-series) and the NVIDIA Container Toolkit.
```bash
./scripts/start.sh --gpu --rebuild
docker compose logs backend | grep -i device     # AI Model Insights shows "Inference device: CUDA"
```
If CUDA is unavailable, the backend falls back to CPU automatically.

## Verify (acceptance tests)
```bash
./scripts/acceptance.sh                    # tests 1, 3–9 incl. restart persistence; results in test-results/
./scripts/acceptance.sh --offline          # same, with backend and database cut off from the internet (test 10)
./scripts/acceptance.sh --image my_food.jpg   # use your own unseen food photo
./scripts/test.sh                          # developer suite: 15 API tests + phone-sized browser test (pulls a Playwright image)
```

## Configuration (`.env`)
| Variable | Default | Purpose |
|---|---|---|
| `HTTP_PORT` | 8080 | Port for the web app |
| `HTTP_BIND` | 0.0.0.0 | Set `127.0.0.1` to block other devices on the network |
| `JWT_SECRET` | random (start.sh) | Signs login tokens; keep it secret |
| `POSTGRES_PASSWORD` | mealsense | Database password; set it before the first start |
| `INFERENCE_DEVICE` | auto | `auto`, `cpu` or `cuda` |
| `REDIS_URL` | (empty) | Optional cache: `redis://redis:6379/0` together with `--profile cache` |
| `OLLAMA_URL` | unreachable | Optional local SLM for explanations (`--profile slm`, `http://ollama:11434`) |

## Troubleshooting
| Symptom | Fix |
|---|---|
| `port is already allocated` | Set `HTTP_PORT=8090` in `.env`, then `./scripts/start.sh` and open :8090 |
| `docker: command not found` / `permission denied ... docker.sock` | Install Docker, or `sudo usermod -aG docker $USER` and log in again |
| Build fails at `pip install` or `npm ci` | Internet or proxy needed for the first build; retry. Behind a corporate proxy, set `HTTP(S)_PROXY` for Docker |
| `service "backend" is unhealthy` | `docker compose logs backend`. Common causes: database not ready (wait and run start.sh again) or a changed `POSTGRES_PASSWORD` after the first start (restore it, or `./scripts/stop.sh --wipe`) |
| App loads but "Vision only" / analysis fails | `curl localhost:8080/api/v1/health` should show `"vision": true`; otherwise check the logs for model-file errors and rebuild with `./scripts/start.sh --rebuild` |
| Apple Silicon build is slow or fails | Docker Desktop: enable "Use Rosetta for x86/amd64 emulation" and run `DOCKER_DEFAULT_PLATFORM=linux/amd64 ./scripts/start.sh --rebuild` |
| Phone cannot open the app | Same Wi-Fi network; use the computer's LAN IP; allow port 8080 in the firewall |
| Camera button opens the gallery only | Some desktop browsers have no camera capture; use **Upload**, or a phone |
| Reset everything | `./scripts/stop.sh --wipe` then `./scripts/start.sh --demo` |

## Data and backups
Data lives in the Docker volumes `mealsenseai_pgdata` (database) and `mealsenseai_uploads` (photos).
Back up the database with `docker compose exec -T db pg_dump -U mealsense -Fc mealsenseai > backup.dump`.
