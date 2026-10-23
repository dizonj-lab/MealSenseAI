# Home-server hosting runbook (Ubuntu 24.04, Threadripper + RTX 5060 Ti)

Public access goes **only** through an outbound Cloudflare Tunnel, behind a Cloudflare Access login. Your router has
**no port forwards**, and the app listens only on `127.0.0.1`. You administer the server over Tailscale.

```
Grader's browser ─► Cloudflare (HTTPS, WAF, DDoS, Access e-mail login) ◄─ outbound tunnel ─ cloudflared ─► nginx ─► app ─► Postgres/Redis
You (anywhere) ──► Tailscale (private, encrypted) ──► SSH / http://127.0.0.1:8080
Router: zero port forwards, UPnP off.   CEREBRO: separate Compose project and networks, never joined to MealSenseAI's.
```

Time needed: about 2 hours. Cost: a domain (~US$10/yr). Optional: Backblaze B2 off-site backup (<US$1/mo) and a UPS (~S$250–350 one-off).

---

## Step 0 — Before you start (10 min)
1. **Router:** log in and confirm there are **no port forwards** to this server, and **turn UPnP off**. UPnP lets software open ports silently.
2. **SSH key:** from your laptop, run `ssh-copy-id <you>@<server-LAN-IP>`. Check that `ssh <you>@<server>` logs in without a password.
3. **Code on the server:**
   ```bash
   git clone https://github.com/dizonj-lab/MealSenseAI.git ~/mealsenseai && cd ~/mealsenseai
   git checkout claude/mealsenseai-mvp
   ```

## Step 1 — Harden the host (15 min)
```bash
cd ~/mealsenseai/infrastructure/home-server
sudo LAN_ALLOW_PORTS="" ./harden-host.sh      # list any CEREBRO ports LAN devices must still reach, e.g. "3000,8443"
sudo tailscale up --ssh                        # log in with the link it prints (free personal plan)
sudo ./harden-host.sh                          # re-run once: now also enables keys-only SSH
```
This sets up:
- a firewall that denies all inbound traffic except SSH from your LAN and Tailscale;
- keys-only SSH with no root login;
- fail2ban;
- automatic security updates (a reboot at 04:30 only when needed);
- Docker logging limits and `no-new-privileges` as the default.

Install Tailscale on your laptop and phone as well. From then on, administer the server via `ssh <you>@<server-tailscale-name>`.

## Step 2 — GPU for Ollama and training (10 min)
```bash
nvidia-smi                       # needs driver 570+ for RTX 50-series; if missing: sudo ubuntu-drivers install --gpgpu && sudo reboot
sudo ./setup-gpu.sh              # NVIDIA Container Toolkit; ends with "GPU available to Docker"
```
Training now uses CUDA automatically: `ml/training/train.py` prints `device=cuda (bf16 autocast)`. On 32 cores, set `num_workers: 12` in `ml/training/config.yaml`.

## Step 3 — Domain and Cloudflare Tunnel (20 min)
1. Create a free Cloudflare account. Buy a domain in **Domain Registration**, or move an existing one to Cloudflare.
2. **Zero Trust → Networks → Tunnels → Create tunnel → Cloudflared**, name it `home-server`, and **copy the token**. Skip the install command shown; Docker runs cloudflared.
3. In the same tunnel, open **Public hostnames → Add**: subdomain `mealsense`, your domain, service type `HTTP`, URL `proxy:80`.

## Step 4 — Cloudflare Access: only invited people reach the app (10 min)
**Zero Trust → Access → Applications → Add → Self-hosted**:
- Application domain `mealsense.<your-domain>`, session duration 24h.
- Policy **Allow**: Emails ending in `nus.edu.sg`, plus your own e-mail. Login method: **One-time PIN** (no setup needed).
- Add a second application for `mealsense.<your-domain>/api/v1/health` with policy **Bypass → Everyone**, so the uptime monitor can reach the health check.

**Security → WAF:** keep the managed rules on. Add a rate-limiting rule: 100 requests per minute per IP on `/api/`.

## Step 5 — Deploy (10 min, first build is longer)
```bash
cd ~/mealsenseai
SLM=1 ./infrastructure/home-server/deploy.sh   # paste the tunnel token when asked; SLM=1 also runs Ollama on the GPU
docker compose exec app python -m app.seed      # optional demo account demo@mealsense.ai / demo12345
```
`deploy.sh` does the following:
- generates `JWT_SECRET` and the database password (stored in `.env`, chmod 600, never committed);
- selects the hardened home override (`docker-compose.home.yml`);
- builds and starts the stack, then checks the health endpoint.

Run it again whenever you want to update. It pulls, rebuilds and restarts.

## Step 6 — Backups (10 min)
Use a folder on the **second NVMe**:
```bash
sudo mkdir -p /srv/backup     # mount point of the 2nd NVMe, or any folder on it
sudo ./infrastructure/home-server/install-backups.sh /srv/backup
```
- **Every night at 03:15:** a Postgres dump, the uploaded photos and `.env` are backed up with restic. Backups are encrypted and kept for 7 daily, 4 weekly and 6 monthly snapshots.
- **Save `/etc/mealsense-backup.key` in your password manager.** Without it the backups can't be restored.
- **Off-site copy (recommended):** create a Backblaze B2 bucket and an app key, then uncomment the `RESTIC_REPOSITORY_2` and key lines in `/etc/mealsense-backup.env`.
- **Restore:** `sudo /opt/mealsense/restore.sh` (latest snapshot) or `sudo /opt/mealsense/restore.sh <snapshot-id>`. Do a test restore once.

## Step 7 — Monitoring and alerts (10 min)
- **Uptime:** in UptimeRobot or healthchecks.io (free), monitor `https://mealsense.<domain>/api/v1/health` every 5 min and alert by e-mail or push.
- **Backups:** create a healthchecks.io check and put its URL in `HEALTHCHECK_URL` in `/etc/mealsense-backup.env`. You're alerted if a nightly backup doesn't run.
- **Tunnel:** in Cloudflare, go to **Notifications → Add → Tunnel health alert**.

## Step 8 — Verify the exposure (5 min) — do this every time you change network settings
- **From your phone on mobile data (not your Wi-Fi):**
  - `https://mealsense.<domain>` shows the Cloudflare Access login, not the app;
  - after the e-mail PIN, the app loads.
- **From any machine:** scan your home public IP with https://www.shodan.io/host/<your-public-IP> or an online port scanner. **No ports should be open.**
- **On the server:**
  - `sudo ss -tlnp | grep -v 127.0.0` shows no MealSenseAI ports on public interfaces;
  - `sudo ufw status` shows deny (incoming) as the default.

## Step 9 — Keep CEREBRO isolated
- Keep CEREBRO in its own folder and Compose project. **Never** attach its containers to `mealsenseai_*` networks, and never mount MealSenseAI volumes.
- If CEREBRO goes public too, give it its **own** Access application and policy. Don't make it a path under MealSenseAI's hostname.
- Docker-published ports **bypass UFW**. Bind CEREBRO's published ports to `127.0.0.1:` (or the Tailscale IP) the same way.

---

## Risk register

| # | Risk | Mitigation (implemented / step) | Residual | Further mitigation |
|---|---|---|---|---|
| 1 | Home IP and open ports attacked from the internet | No port forwards, UPnP off, outbound-only tunnel, UFW default-deny, app bound to 127.0.0.1 (Steps 0, 1, 3, 8) | Very low | Scan for open ports after any router change (Step 8) |
| 2 | Strangers using the app or brute-forcing logins | Cloudflare Access e-mail PIN in front of everything; app login; nginx rate limits (10/min on auth, 20/min on analysis); Cloudflare WAF and rate rule (Step 4) | Low | Narrow the Access policy to named e-mails during grading |
| 3 | App vulnerability leads to compromise | Containers drop all Linux capabilities except a short list, `no-new-privileges`, read-only proxy, memory/CPU/PID limits, internal network with **no internet egress** for app, DB and Redis, automatic OS updates | Low | Rebuild monthly (`deploy.sh`) to pick up base-image fixes |
| 4 | A compromise spreads to CEREBRO or the host | Separate Docker networks/projects (Step 9), non-root SSH, keys only, fail2ban | Low–medium (Docker is root-equivalent) | For stronger isolation, move the public stacks into a KVM VM later |
| 5 | Admin access stolen | SSH keys only, Tailscale (device-authenticated), no SSH on the internet, MFA on the Cloudflare and Tailscale accounts | Low | Turn on MFA on GitHub too; keep the Tailscale ACL default |
| 6 | Secrets leak | Generated secrets in `.env` (chmod 600, git-ignored); tunnel token never in git; backup key stored separately | Low | Rotate the tunnel token in Cloudflare if exposed |
| 7 | Data loss (disk failure, mistakes) | Nightly encrypted restic backups to the second NVMe, plus an off-site copy; tested restore script; uptime and backup alerts (Steps 6, 7) | Low | Test-restore once a month |
| 8 | Power cut or ISP outage during grading | Containers restart automatically; uptime alert; **NUS can always run it themselves**: `docker compose up` on any laptop (README) | Medium for the hosted URL | UPS with automatic shutdown; optional fallback copy on AWS Lightsail (~US$20/mo) during grading week |
| 9 | Personal health data (PDPA) | Demo accounts only; health fields need consent and are minimised; no third-party AI calls (local models only) | Low | Don't invite real patients; add a privacy note to the login page |
| 10 | ISP terms on residential hosting | Outbound tunnel, low traffic, no inbound ports | Low | Check your ISP's acceptable-use policy |
| 11 | GPU and training workloads slowing the demo | App limited to `APP_CPUS` cores and 4 GB of RAM; train outside grading hours | Low | Pause training during grading slots |

## Day-to-day commands
```bash
docker compose ps                     # health of every service
docker compose logs -f app            # application logs
./infrastructure/home-server/deploy.sh   # update to the latest code
sudo systemctl list-timers mealsense-backup.timer
sudo /opt/mealsense/restore.sh        # restore from the latest backup
```
