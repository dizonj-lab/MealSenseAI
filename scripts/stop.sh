#!/usr/bin/env bash
# Stop MealSenseAI.  ./scripts/stop.sh          keep all data (default)
#                    ./scripts/stop.sh --wipe   also DELETE the database and uploaded photos
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-}" = "--wipe" ]; then
  read -rp "Delete ALL MealSenseAI data (database, photos)? Type yes: " ok
  [ "$ok" = yes ] && docker compose down -v --remove-orphans && echo "stopped and data deleted"
else
  docker compose down --remove-orphans && echo "stopped (data kept in Docker volumes)"
fi
