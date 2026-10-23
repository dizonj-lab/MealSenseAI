#!/usr/bin/env bash
# End-to-end acceptance run on THIS machine: start -> tests 1,3-8 -> restart -> test 9 (persistence).
#   ./scripts/acceptance.sh [--offline] [--gpu] [--image path/to/unseen-food.jpg]
#   --offline : backend and database run without any internet access (acceptance test 10)
set -euo pipefail
cd "$(dirname "$0")/.."
FILES=(-f docker-compose.yml); ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --offline) FILES+=(-f docker-compose.offline.yml);; --gpu) FILES+=(-f docker-compose.gpu.yml);;
  --image) ARGS+=(--image "$2"); shift;; *) echo "unknown option $1"; exit 1;; esac; shift; done
[ -f .env ] || ./scripts/start.sh >/dev/null   # creates .env on first run
C=(docker compose "${FILES[@]}")
PORT="$(sed -n 's/^HTTP_PORT=//p' .env)"; PORT="${PORT:-8080}"
"${C[@]}" up -d --wait
python3 scripts/acceptance_test.py run --url "http://localhost:$PORT" "${ARGS[@]}"
echo "==> restarting all containers (down + up, volumes kept)"
"${C[@]}" down && "${C[@]}" up -d --wait
python3 scripts/acceptance_test.py verify --url "http://localhost:$PORT"
echo "Acceptance tests passed. Results: test-results/acceptance_run.json, test-results/acceptance_verify.json"
