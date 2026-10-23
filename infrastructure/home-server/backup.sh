#!/usr/bin/env bash
# Nightly encrypted backups: Postgres dump + uploaded images -> restic (local 2nd NVMe, optional off-site).
# Config: /etc/mealsense-backup.env (chmod 600), see HOME-SERVER.md. Run by mealsense-backup.timer.
set -euo pipefail
set -a; . /etc/mealsense-backup.env; set +a
: "${REPO_DIR:?}" "${RESTIC_REPOSITORY:?}" "${RESTIC_PASSWORD_FILE:?}"
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
ping_hc() { [ -n "${HEALTHCHECK_URL:-}" ] && curl -fsS -m 10 "$HEALTHCHECK_URL$1" >/dev/null || true; }
ping_hc /start
cd "$REPO_DIR"
docker compose exec -T db pg_dump -U mealsense -Fc mealsenseai > "$STAGE/mealsenseai.dump"
docker compose exec -T backend tar -czf - -C /data . > "$STAGE/uploads.tgz"   # uploads volume, via the app container
cp .env "$STAGE/env.backup"
restic snapshots >/dev/null 2>&1 || restic init
restic backup --tag mealsenseai "$STAGE"
restic forget --tag mealsenseai --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
if [ -n "${RESTIC_REPOSITORY_2:-}" ]; then   # off-site copy (e.g. s3:..., b2:...)
  RESTIC_REPOSITORY="$RESTIC_REPOSITORY_2" restic snapshots >/dev/null 2>&1 || RESTIC_REPOSITORY="$RESTIC_REPOSITORY_2" restic init
  RESTIC_REPOSITORY="$RESTIC_REPOSITORY_2" restic backup --tag mealsenseai "$STAGE"
  RESTIC_REPOSITORY="$RESTIC_REPOSITORY_2" restic forget --tag mealsenseai --keep-daily 7 --keep-weekly 4 --prune
fi
ping_hc ""
echo "backup ok $(date -Is)"
