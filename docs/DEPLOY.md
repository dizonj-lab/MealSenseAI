# Deploying v0.8.0 – v0.11.0 to Buddy (not yet approved; do not run until approved)

The steps below deploy everything up to v0.11.0. Expect `"version":"0.11.0"` from the health check.

| Version | What it adds | Migration | New environment variables |
|---|---|---|---|
| 0.8.0 | minimalist landing, server-side onboarding, grounded Meal Advisor with server-side conversations | 0005 | none |
| 0.9.0 | friendly Meal Advisor personality | none | none |
| 0.10.0 | glucose charts in mmol/L (pre-meal reading + estimated rise; personal calibration from your readings) | none | none |
| 0.11.0 | contact form (stored, emailed to `CONTACT_TO`), draft notices removed, LinkedIn link | 0006 | optional `SMTP_*`, `CONTACT_TO` |

No model, GPU, Ollama or Cloudflare changes. Email verification is out of scope.

### Contact form email (optional, free)
Messages are always saved in the database. To also receive them by email, add these to Buddy's `.env` (they are new
variables; no existing secret changes). Use a mail account you already own, e.g. a Gmail address with an
[app password](https://support.google.com/accounts/answer/185833); Outlook.com accounts may refuse SMTP password
logins. No paid service is needed.
```
CONTACT_TO=joel.dizon@live.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_FROM=you@gmail.com
```
Without them, read messages with `docker compose exec backend python -m app.services.mailer`.

Code: branch `mealsenseai-mvp`. The last commit before this work is **`152852d`** (rollback target).

## 1. What changes in the database (migrations `0005`, `0006`, additive only)
| Change | Effect on existing data |
|---|---|
| `health_profiles.age_range`, `health_profiles.other_goal` (nullable) | none |
| new tables `chat_threads`, `chat_messages` | none |
| new table `contact_messages` (0006) | none |

The migration runs automatically when the backend starts (`upgrade_db()`), exactly as 0001–0004 did.
Existing accounts, meals, photos, custom foods and training samples are untouched.

**Behaviour change for existing accounts:** onboarding is now enforced by the server. An account that never finished
onboarding gets `403 onboarding_required` from feature endpoints, and the app sends it to the onboarding screen.
Accounts that finished onboarding are unaffected. Advisor history kept in the browser by v0.7 is not migrated;
conversations start fresh, on the server.

## 2. Before deploying (on Buddy, in the MealSenseAI folder)
```bash
docker compose ls                                  # note the compose files/project Buddy uses today
git status && git log --oneline -1                 # note the commit currently deployed
docker compose exec db pg_dump -U mealsense mealsenseai > ~/mealsense-backup-$(date +%F).sql   # database backup
```

## 3. Deploy
Use the **same compose files and flags Buddy uses today** (for example `-f docker-compose.yml -f docker-compose.home.yml
-f docker-compose.gpu.yml` and `--profile slm` if Ollama runs in compose). The commands only rebuild the two app images.
They never remove volumes.
```bash
git fetch origin mealsenseai-mvp && git checkout mealsenseai-mvp && git pull
docker compose <same -f files> build backend frontend
docker compose <same -f files> up -d backend frontend      # db, ollama, volumes and the tunnel keep running
docker compose <same -f files> logs --tail=50 backend      # expect "Running upgrade 0004 -> 0005" and "0005 -> 0006"
curl -s https://mealsense.xtangent.ai/api/v1/health        # expect "version":"0.11.0"
```
Never run `docker compose down -v` or `docker volume rm` (they delete data).

## 4. Verify on Buddy (measurements only possible there)
```bash
# labelled assistant evaluation: creates a throwaway test account, ~40 cases, measures SLM tokens/throughput and GPU
python3 ml/evaluation/advisor_eval.py --base https://mealsense.xtangent.ai --out test-results/advisor_eval_buddy.json
```
It needs `httpx` (`pip install httpx`) on the machine running it, and `nvidia-smi` on Buddy for GPU sampling. The test
account it creates (`eval…@mealsense.ai`) can be deleted from Settings after logging in, or kept as evidence.

## 5. Rollback
v0.8.0–v0.11.0 only *add* columns and tables, so v0.7 code runs on the migrated database:
```bash
git checkout 152852d
docker compose <same -f files> build backend frontend && docker compose <same -f files> up -d backend frontend
```
Optional, only if you need to remove the new schema (this deletes stored Advisor conversations):
```bash
docker compose exec backend alembic downgrade 0004   # removes 0006 and 0005
```
Rolling back only v0.11.0 instead: check out `25e1345` (v0.10.0) and optionally `alembic downgrade 0005` (deletes stored contact messages).
Restore the backup only if something went wrong with data:
`docker compose exec -T db psql -U mealsense mealsenseai < ~/mealsense-backup-YYYY-MM-DD.sql`.

## 6. Test evidence (sandbox, CPU, no Ollama, no GPU)
| Check | Result |
|---|---|
| pytest | **47 passed** (incl. onboarding access matrix, assistant and personality tests, mmol/L scale and calibration, contact form with mocked SMTP) |
| Phone UI flow, light and dark | **PASS**, no JS errors (landing → contact form → creator → register → onboarding → multi-food meal → mmol/L charts → advisor → about) |
| Labelled assistant evaluation (`test-results/advisor_eval.json`) | **38/38**; unsupported-claim rate 0.0; reply latency mean 13 ms, p95 18 ms (rule engine) |
| Not measured here | SLM latency, input/output tokens, tokens/s, SLM rejection rate, GPU utilisation: run step 4 on Buddy |

The labelled set was written alongside the implementation and two real defects it found were fixed, so it is a
regression check, not an independent benchmark.
