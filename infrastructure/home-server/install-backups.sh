#!/usr/bin/env bash
# sudo ./install-backups.sh /srv/backup   (a folder on the SECOND NVMe)
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
DEST="${1:?usage: sudo ./install-backups.sh /path/on/second/nvme}"
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
mkdir -p /opt/mealsense "$DEST/restic"; chmod 700 "$DEST"
install -m 750 "$HERE/backup.sh" "$HERE/restore.sh" /opt/mealsense/
[ -f /etc/mealsense-backup.key ] || { openssl rand -base64 48 > /etc/mealsense-backup.key; chmod 600 /etc/mealsense-backup.key; }
if [ ! -f /etc/mealsense-backup.env ]; then
  cat > /etc/mealsense-backup.env <<CONF
REPO_DIR=$REPO
RESTIC_REPOSITORY=$DEST/restic
RESTIC_PASSWORD_FILE=/etc/mealsense-backup.key
# Off-site copy (recommended), e.g. Backblaze B2 S3-compatible:
# RESTIC_REPOSITORY_2=s3:https://s3.us-west-004.backblazeb2.com/your-bucket/mealsense
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# Dead-man alert if a backup does not run (https://healthchecks.io, free):
# HEALTHCHECK_URL=https://hc-ping.com/your-uuid
CONF
  chmod 600 /etc/mealsense-backup.env
fi
install -m 644 "$HERE/mealsense-backup.service" "$HERE/mealsense-backup.timer" /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now mealsense-backup.timer
systemctl start mealsense-backup.service && journalctl -u mealsense-backup.service -n 5 --no-pager
echo "IMPORTANT: copy /etc/mealsense-backup.key to your password manager. Without it backups cannot be restored."
