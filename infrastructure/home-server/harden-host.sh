#!/usr/bin/env bash
# Host hardening for the home server (Ubuntu 24.04). Safe to re-run.
#   sudo ./harden-host.sh                 # firewall, SSH, auto-updates, fail2ban, Docker defaults, Tailscale
# Nothing here opens a port to the internet: public traffic arrives only through the outbound Cloudflare Tunnel.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
ADMIN_USER="${SUDO_USER:-$(logname 2>/dev/null || echo root)}"
LAN_CIDR="${LAN_CIDR:-$(ip -o -f inet route show scope link | awk '!/docker|br-|tailscale/ {print $1; exit}')}"
LAN_ALLOW_PORTS="${LAN_ALLOW_PORTS:-}"   # e.g. "3000,8443": existing CEREBRO ports that LAN devices must still reach
echo "==> admin user: $ADMIN_USER   LAN: ${LAN_CIDR:-unknown}"

echo "==> packages"
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q ufw fail2ban unattended-upgrades restic curl jq >/dev/null

echo "==> automatic security updates (reboot at 04:30 only if a kernel update requires it)"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
CONF
cat > /etc/apt/apt.conf.d/52mealsense-unattended <<'CONF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:30";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
CONF

echo "==> Tailscale (private admin network)"
if ! command -v tailscale >/dev/null; then curl -fsSL https://tailscale.com/install.sh | sh; fi
tailscale status >/dev/null 2>&1 || echo "   -> run 'sudo tailscale up --ssh' and log in, then re-run this script"

echo "==> firewall: deny all inbound except SSH from LAN and anything over Tailscale (existing rules are kept)"
ufw default deny incoming
ufw default allow outgoing
[ -n "$LAN_CIDR" ] && ufw allow from "$LAN_CIDR" to any port 22 proto tcp comment "SSH from LAN"
ufw allow in on tailscale0 comment "Tailscale admin"
for p in ${LAN_ALLOW_PORTS//,/ }; do ufw allow from "$LAN_CIDR" to any port "$p" proto tcp comment "LAN service"; done
ufw --force enable
ufw status verbose | sed -n '1,20p'

echo "==> SSH: keys only, no root login"
KEYS="$(getent passwd "$ADMIN_USER" | cut -d: -f6)/.ssh/authorized_keys"
if [ -s "$KEYS" ]; then
  cat > /etc/ssh/sshd_config.d/60-mealsense-hardening.conf <<'CONF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
X11Forwarding no
MaxAuthTries 3
CONF
  sshd -t && systemctl reload ssh
  echo "   keys-only SSH enabled"
else
  echo "   SKIPPED: $KEYS is empty. Add your SSH public key first (ssh-copy-id), then re-run, so you are not locked out."
fi

echo "==> fail2ban for SSH"
cat > /etc/fail2ban/jail.d/sshd.local <<'CONF'
[sshd]
enabled = true
maxretry = 4
bantime = 1h
CONF
systemctl enable --now fail2ban >/dev/null && systemctl restart fail2ban

echo "==> Docker daemon defaults (merged into /etc/docker/daemon.json)"
mkdir -p /etc/docker
[ -s /etc/docker/daemon.json ] || echo '{}' > /etc/docker/daemon.json
jq '. + {"live-restore": true, "no-new-privileges": true, "log-driver": "json-file",
         "log-opts": {"max-size": "10m", "max-file": "5"}}' /etc/docker/daemon.json > /tmp/daemon.json
mv /tmp/daemon.json /etc/docker/daemon.json
systemctl restart docker

echo "==> done. Verify from ANOTHER machine that nothing answers on your public IP (see HOME-SERVER.md, step 8)."
