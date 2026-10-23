#!/usr/bin/env bash
# Restore the latest (or a given) snapshot into the running stack.  sudo ./restore.sh [snapshot-id]
set -euo pipefail
set -a; . /etc/mealsense-backup.env; set +a
SNAP="${1:-latest}"; OUT="$(mktemp -d)"; trap 'rm -rf "$OUT"' EXIT
restic restore "$SNAP" --tag mealsenseai --target "$OUT"
DUMP="$(find "$OUT" -name mealsenseai.dump)"; TGZ="$(find "$OUT" -name uploads.tgz)"
cd "$REPO_DIR"
docker compose exec -T db pg_restore -U mealsense -d mealsenseai --clean --if-exists < "$DUMP"
docker compose exec -T app tar -xzf - -C /data < "$TGZ"
docker compose restart app
echo "restored snapshot $SNAP"
