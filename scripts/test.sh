#!/usr/bin/env bash
# Builds the stack, runs API tests (pytest) and the mobile UI flow (Playwright) in an isolated environment.
#   ./scripts/test.sh            run tests, then tear everything down
#   KEEP=1 ./scripts/test.sh     keep the test stack running at http://localhost:8081 (seeded demo user)
set -euo pipefail
cd "$(dirname "$0")/.."
C=(docker compose -f docker-compose.test.yml --profile tests)
cleanup() { [ "${KEEP:-0}" = 1 ] || "${C[@]}" down -v --remove-orphans >/dev/null 2>&1; }
trap cleanup EXIT
mkdir -p test-results

echo "==> build images"
[ "${SKIP_BUILD:-0}" = 1 ] || "${C[@]}" build
echo "==> start db, backend, frontend"
docker compose -f docker-compose.test.yml up -d --wait frontend
echo "==> API + pipeline tests (pytest)"
"${C[@]}" run --rm api-tests
echo "==> mobile UI end-to-end (Playwright via reverse proxy)"
"${C[@]}" run --rm e2e
echo "==> health"
curl -fsS "http://localhost:${TEST_HTTP_PORT:-8081}/api/v1/health"; echo
if [ "${KEEP:-0}" = 1 ]; then
  docker compose -f docker-compose.test.yml exec -T backend python -m app.seed
  echo "Test stack running at http://localhost:${TEST_HTTP_PORT:-8081} (stop: docker compose -f docker-compose.test.yml down -v)"
fi
echo "ALL TESTS PASSED — screenshots in test-results/screenshots/"
