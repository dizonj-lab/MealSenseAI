#!/usr/bin/env bash
# Deploy / update MealSenseAI on the home server (run as your normal user, from anywhere).
#   ./infrastructure/home-server/deploy.sh          # app only
#   SLM=1 ./infrastructure/home-server/deploy.sh    # plus Ollama on the GPU
set -euo pipefail
cd "$(dirname "$0")/../.."
umask 077
[ -f .env ] || cp .env.example .env
setkv() { grep -q "^$1=" .env && sed -i "s#^$1=.*#$1=$2#" .env || echo "$1=$2" >> .env; }
getkv() { sed -n "s/^$1=//p" .env | tail -1; }

# secrets: generated once, never committed (.env is git-ignored, chmod 600)
case "$(getkv JWT_SECRET)" in ""|replace-with-*|change-me*) setkv JWT_SECRET "$(openssl rand -hex 32)";; esac
if ! docker volume inspect mealsenseai_pgdata >/dev/null 2>&1; then
  case "$(getkv POSTGRES_PASSWORD)" in ""|mealsense) setkv POSTGRES_PASSWORD "$(openssl rand -hex 24)";; esac
fi
setkv COMPOSE_FILE "docker-compose.yml:docker-compose.home.yml"
setkv APP_CPUS "${APP_CPUS:-8}"
if [ "${SLM:-0}" = 1 ]; then setkv OLLAMA_URL "http://ollama:11434"; setkv COMPOSE_PROFILES slm; fi
if [ -z "$(getkv CLOUDFLARE_TUNNEL_TOKEN)" ]; then
  read -rsp "Paste the Cloudflare Tunnel token (Zero Trust > Networks > Tunnels): " TOKEN; echo
  setkv CLOUDFLARE_TUNNEL_TOKEN "$TOKEN"
fi
chmod 600 .env

git pull --ff-only || echo "(git pull skipped)"
docker compose up -d --build --wait
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
PORT="$(getkv HTTP_PORT)"; PORT="${PORT:-8080}"
curl -fsS "http://127.0.0.1:$PORT/api/v1/health" && echo
echo "Local: http://127.0.0.1:$PORT   Public: your Cloudflare hostname (protected by Cloudflare Access)"
