# 08 · Deployment

Local single-machine deployment with Docker Compose: see `05-Infrastructure/README.md`.

Checklist before a demo:
1. `./infrastructure/test.sh` passes.
2. `.env` has a real `JWT_SECRET` and `POSTGRES_PASSWORD`.
3. `docker compose up -d --build`, then `docker compose ps` shows every service healthy.
4. `curl http://localhost:8080/api/v1/health` returns `"vision": true` (and `"slm": true` if Ollama is used).
5. To use it from a phone: same Wi-Fi network, `http://<PC-IP>:8080`. The camera picker works over plain HTTP because it uses a file input.

## Home server
Step-by-step hosting on your own Ubuntu server, with Cloudflare Tunnel and Access, hardening, GPU, backups and a risk register: [HOME-SERVER.md](HOME-SERVER.md).
