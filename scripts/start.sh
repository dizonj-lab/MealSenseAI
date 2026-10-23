#!/usr/bin/env bash
# Start MealSenseAI.  ./scripts/start.sh [--gpu] [--demo] [--rebuild]
#   --gpu      use the NVIDIA GPU (needs NVIDIA Container Toolkit); CPU is the default
#   --demo     create the demo account demo@mealsense.ai / demo12345 with sample meals
#   --rebuild  rebuild images (after pulling new code)
set -euo pipefail
cd "$(dirname "$0")/.."
FILES=(-f docker-compose.yml); DEMO=0; BUILD=()
for a in "$@"; do case "$a" in
  --gpu) FILES+=(-f docker-compose.gpu.yml);; --demo) DEMO=1;; --rebuild) BUILD=(--build);;
  *) echo "unknown option $a"; exit 1;; esac; done
command -v docker >/dev/null || { echo "Docker is not installed (see README > Prerequisites)"; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose v2 is required"; exit 1; }
if [ ! -f .env ]; then
  cp .env.example .env
  secret() { head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
  sed -i.bak "s/^JWT_SECRET=.*/JWT_SECRET=$(secret)/" .env && rm -f .env.bak
  echo "created .env with a random JWT_SECRET"
fi
C=(docker compose "${FILES[@]}")
[ ${#BUILD[@]} -gt 0 ] || docker image inspect mealsenseai/backend:local >/dev/null 2>&1 || BUILD=(--build)
PORT="$(sed -n 's/^HTTP_PORT=//p' .env)"; PORT="${PORT:-8080}"
"${C[@]}" down --remove-orphans >/dev/null 2>&1 || true   # also removes containers of older versions (data volumes are kept)
HOLDER="$(docker ps --filter "publish=$PORT" --format '{{.Names}}' | head -1)"
if [ -n "$HOLDER" ] || (command -v lsof >/dev/null && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1); then
  echo "Port $PORT is already in use${HOLDER:+ by container '$HOLDER'}."
  echo "Stop it (docker stop ${HOLDER:-<name>}) or choose another port: echo HTTP_PORT=8090 >> .env"; exit 1
fi
"${C[@]}" up -d "${BUILD[@]}" --wait
"${C[@]}" ps --format "table {{.Service}}\t{{.Status}}"
curl -fsS "http://127.0.0.1:$PORT/api/v1/health" && echo
[ "$DEMO" = 1 ] && "${C[@]}" exec -T backend python -m app.seed
echo "MealSenseAI is running: http://localhost:$PORT   (stop with ./scripts/stop.sh)"
