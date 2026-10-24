# Deploying v0.8.0 to Buddy (not yet approved; do not run until approved)

**Scope:** minimalist landing page, server-side onboarding check, onboarding fields, and the grounded Meal Advisor with
server-side conversations. No model, GPU, Ollama or Cloudflare changes. **No new environment variables.**
Email verification is out of scope.

Code: branch `claude/mealsenseai-mvp`. The last commit before this work is **`152852d`** (rollback target).

## 1. What changes in the database (migration `0005`, additive only)
| Change | Effect on existing data |
|---|---|
| `health_profiles.age_range`, `health_profiles.other_goal` (nullable) | none |
| new tables `chat_threads`, `chat_messages` | none |

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
git fetch origin claude/mealsenseai-mvp && git checkout claude/mealsenseai-mvp && git pull
docker compose <same -f files> build backend frontend
docker compose <same -f files> up -d backend frontend      # db, ollama, volumes and the tunnel keep running
docker compose <same -f files> logs --tail=50 backend      # expect "Running upgrade 0004 -> 0005"
curl -s https://mealsense.xtangent.ai/api/v1/health        # expect "version":"0.8.0"
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
v0.8.0 only *adds* columns and tables, so v0.7 code runs on the migrated database:
```bash
git checkout 152852d
docker compose <same -f files> build backend frontend && docker compose <same -f files> up -d backend frontend
```
Optional, only if you need to remove the new schema (this deletes stored Advisor conversations):
```bash
docker compose exec backend alembic downgrade 0004
```
Restore the backup only if something went wrong with data:
`docker compose exec -T db psql -U mealsense mealsenseai < ~/mealsense-backup-YYYY-MM-DD.sql`.

## 6. Test evidence (sandbox, CPU, no Ollama, no GPU)
| Check | Result |
|---|---|
| pytest | **31 passed** (incl. onboarding access matrix and 8 assistant test groups) |
| Phone UI flow, light and dark | **PASS**, no JS errors (landing → register → onboarding → multi-food meal → advisor sheet → advisor → about) |
| Labelled assistant evaluation (`test-results/advisor_eval.json`) | **38/38**; unsupported-claim rate 0.0; reply latency mean 13 ms, p95 18 ms (rule engine) |
| Not measured here | SLM latency, input/output tokens, tokens/s, SLM rejection rate, GPU utilisation: run step 4 on Buddy |

The labelled set was written alongside the implementation and two real defects it found were fixed, so it is a
regression check, not an independent benchmark.
