# Test report — MealSenseAI MVP with EXP-002 (23 Oct 2026)

Every result below comes from an actual execution. Raw outputs are in `evidence/tests/` in the submission package
(`test-results/` in the repository).

## Test environment
| Item | Value |
|---|---|
| Host | Ubuntu 24.04.5 LTS (cloud container), 4 vCPU, 15 GB RAM, **no GPU** |
| Docker | Engine 29.9.1, Compose v5.6.0 |
| Independence check | The submission zip was unpacked into a separate directory. All MealSenseAI images and volumes were deleted, every image was rebuilt **from the package only**, and the app was started with `./scripts/start.sh --demo`. |
| Sandbox caveat | This environment reaches the internet only through an inspecting proxy, so the image builds ran with that proxy's CA certificate injected by a sandbox-only wrapper. The shipped Dockerfiles were otherwise used unchanged. A normal machine builds without this. |

## NUS acceptance tests
| # | Test | Result | Evidence |
|---|---|---|---|
| 1 | Deploy on Ubuntu using Docker Compose | **PASS** (CPU) | `start.sh`: frontend, backend and db healthy; `/api/v1/health` → `database: true, vision: true` |
| 2 | Deploy independently on a CPU-only machine | **PASS**, simulated | Fresh build and run from the unpacked package on a CPU-only host. This was the same physical host as development, with images and volumes wiped, not a second computer. |
| 3 | Model loading and taxonomy alignment | **PASS** | EXP-002 loaded once at start-up on CPU; model outputs 320 classes and the taxonomy has 320 contiguous IDs; every ID resolves to its canonical name (pytest); `chicken rice` = id 63; checkpoint SHA-256 `4c9b30c0…` |
| 4 | Upload an unseen food image | **PASS** | `coffee.png` (scikit-image sample photo, not from Food-101/FoodSG) |
| 5 | Display top-three predictions | **PASS** | API and UI: *kopi teh milo* 97.2%, *lobster bisque* 1.1%, *chawanmushi* 0.6%. Browser test asserts three candidate buttons. |
| 6 | Confirm or override the food | **PASS** | Override to candidate 2 then back (API and UI); original prediction preserved; correction logged |
| 7 | Nutrition and health-insight workflow | **PASS** | Portion corrected to 250 g (tagged *Your input*); 130 kcal from a **proxy** record "Kopi" (`transcribed_unverified`); glucose level UNCERTAIN (no GI coverage); 3 recommendations; forecast includes the hypoglycaemia caution for a type 2 profile |
| 8 | Save and retrieve meal history | **PASS** | Meal confirmed; first in history; dashboard totals updated |
| 9 | Restart containers, data persists | **PASS** | `docker compose down` + `up`: login, meal, nutrition totals and photo (HTTP 200) intact |
| 10 | Operation without the development workstation | **PASS** | Run from the package only; with `--offline` the backend and database have **no internet access** (DNS resolution fails inside the backend), and tests 1–9 still pass |

Extra check: a held-out Food-101 photo (`1063878.jpg`, sushi; possibly seen in training) gave *sushi* 99.5%, then
*bruschetta* 0.1% and *falafel* 0.1%. The workflow passed with an **exact** nutrition match.

## Other executed tests
| Test | Result |
|---|---|
| pytest (in container, from package) | **15 passed**: health, auth, consent minimisation, model/taxonomy alignment, top-3 + override + add-by-candidate, blank image → *uncertain* (no fabricated food), manual entry + corrections + recalculation, capture validation, portion maths, 7 forecast tests |
| Playwright phone-sized UI flow via nginx | **PASS**, no JavaScript errors: register → 4-step onboarding → capture → 10-stage analysis → top-3 override → portion edit → add food → save → forecast → history → dashboard → AI insights → desktop view |
| ONNX runtime parity (601 images) | Preprocessing max abs diff **0.0**; logits max abs diff **1.35e-4**; top-1 and top-3 agreement **100%**; ≈12 ms CPU per photo |
| Database migrations | Fresh DB → `0002`. A legacy DB created without migrations is stamped `0001` and upgraded to `0002` with data kept; re-running is idempotent |
| Legacy photo volume owned by root | Fixed automatically by `init-perms`; the non-root backend can read and write |
| Nutrition coverage of 320 classes | 247 exact, 66 proxy, 7 none (`evidence/model/nutrition_coverage.json`) |

## Multi-food recognition and health-intelligence update (23 Oct 2026)
Executed locally (CPU, Python venv + PostgreSQL 16, built frontend via `vite preview`). Docker images were **not**
rebuilt for this update (no new dependencies were added).

| Test | Result |
|---|---|
| pytest | **18 passed** (adds multi-food items/rename/merge/restore, blank photo, portion simulator, glucose readings, personalised insights) |
| Playwright phone flow, `coffee.png` | **PASS**, no JS errors: 1 box; top-3 override; portion simulator (−70 g row), reading 140 mg/dL shown as 7.8 mmol/L; apply; save |
| Playwright phone flow, `multi_food_plate.jpg` | **PASS**, no JS errors: 3 numbered boxes; 2 unidentified items named via search; 2 merged; composition charts; simulator; save blocked until all items named, then saved |

**Detection benchmark** (`ml/evaluation/multifood_eval.py`, seed 11, evaluated after tuning on seed 7): 100 **synthetic**
plates built from Food-101 *test* images (pizza/sushi/steak, 2–3 per plate, 263 items). Synthetic composites have clean
edges and no overlap; these are **not** real-meal results.

| Metric (IoU ≥ 0.5, class-agnostic) | Value |
|---|---|
| TP / FP / FN | 180 / 61 / 83 |
| Precision / Recall / AP50 | 0.747 / 0.684 / 0.592 |
| Matched items: top-1 / top-3 | 0.561 / 0.750 |
| Per-class F1 (pizza / sushi / steak) | 0.926 / 0.586 / 0.192 — steak crops are mostly "unidentified" or *sirloin steak*/*filet mignon* |
| Latency per photo (CPU) | mean 260 ms, p50 262 ms, p95 320 ms |
| Single-dish photos (75) | 43 show exactly one item (38 correct); mean 1.37 extra items per photo |

Not measured: real multi-food photos (no labelled set available; the breakfast acceptance photo was not supplied),
segmentation-mask quality, the uncertainty band's coverage, and any glucose accuracy (the simulation is illustrative).

## Custom foods, food memory and training samples (24 Oct 2026)
| Test | Result |
|---|---|
| pytest | **20 passed** (adds custom food → name item → same photo recognised from memory; owner-only custom foods; training consent) |
| Phone UI flow, `multi_food_plate.jpg` | **PASS**, no JS errors: item named by creating a custom food (portion + nutrients, blanks stay unknown); re-captured photo shows "Known from your earlier label" |
| Fingerprint threshold check | sqrt-probability fingerprints, cosine ≥ 0.70: 94/120 held-out Food-101 photos matched, **all correct** (3 classes, 3 remembered photos each; steak 24/40). Small test — precision with many foods is not measured. |
| Export (`ml/export/export_training_samples.py`) | Ran on the test database: 1 consented sample cropped to `user_labels/<class>/`, manifest + summary listing classes not in EXP-002 |

## v0.8.0: onboarding enforcement, minimalist UI, grounded assistant (24 Oct 2026)
| Test | Result |
|---|---|
| pytest | **31 passed**: onboarding access matrix (11 feature endpoints → 403 until onboarded; 401 without login); assistant: meal retrieval and multi-food, actual raw scores, carb arithmetic, hypothetical not saved, follow-up “yes”, server-side thread and clearing, unnamed/low-confidence clarifying questions, measured vs estimated glucose, medication/diagnosis/urgent safety, prompt injection, cross-user isolation, SLM reply validation (hallucinated number rejected) |
| Phone UI flow, light and dark | **PASS**, no JS errors |
| Labelled assistant set (38 cases, `ml/evaluation/advisor_eval.py`) | **38/38**, unsupported-claim rate 0.0, latency mean 13 ms / p95 18 ms (rule engine; SLM offline in sandbox) |
| Not measured | SLM latency/tokens/throughput, SLM rejection rate, GPU utilisation (need Ollama/GPU on Buddy; see `docs/DEPLOY.md`) |

## v0.9.0: friendly Meal Advisor personality (24 Oct 2026)
| Test | Result |
|---|---|
| pytest | **41 passed**; personality tests: greetings and opener rotation, friendly food identification naming only foods in the meal, multi-turn food conversation (nasi lemak → skip rice → add egg, arithmetic from food-table records), missed-food Add action (nothing claimed before the tap), mystery dish, crystal-ball question, unsupported request, missing nutrients not invented, careful tone for type 1 (no jokes/emoji), serious tone for emergency/medication/diagnosis, openers contain no numbers |
| Phone UI flow, light and dark | **PASS**, no JS errors, including “You missed my sausage!” → Add → meal page updated |
| Not measured | Language-model wording with the persona (Ollama not available here); its replies still pass the same number/food/safety validation |

## v0.13.0–0.13.1: training-data governance, admin area, meal composition (28 Oct 2026)
Executed locally (CPU, Python venv + PostgreSQL 16, built frontend served by the backend, Playwright Chromium). Docker
images were **not** rebuilt here (no Docker daemon in this environment; no new dependencies were added).

| Test | Result |
|---|---|
| pytest | **56 passed** (adds 9 governance tests): admin routes 401/403 for others, revoking takes effect with the same token; verification link (bound to the address, not usable as a session); consent per sample and withdrawal; an implausible pizza→salad-style relabel flagged for implausibility and carbohydrate safety; own duplicate rejected, self-confirmation noted, new-account flag; freeze → exclude contributor (new version supersedes) → export honouring a later withdrawal; settings validation and reset; prompt versions and rollback; model gate: safety regression fails, broken package refused, shadow agreement 100% (same model), promotion blocked until enough shadow data, promoted package serves recognition, rollback, different test set fails |
| Migration 0007 | Applied to a fresh database and to the populated local demo database (meals kept). Carrying consent over for samples shared before 0.13 is in the migration but was not exercised: that database had none |
| `ml/evaluation/gate_report.py` | Ran on a 150-image, 3-class sample: report written with test-set SHA-256 and per-group accuracy. The real gate test set (all safety groups) is **not built yet** |
| Admin UI (Playwright, desktop 1440 px and phone 390 px) | **PASS**, no JS errors, no horizontal overflow on any of the 7 tabs; a plain account sees no Admin menu and is redirected from `/admin` |
| Meal composition (Playwright, light, dark and phone) | **PASS**, no JS errors: single dish and a multi-food meal; food-by-food rows only for several foods; amber when a meal passes its share of a limit; saturated fat shown as missing when a food lacks it |
| Not re-run for 0.13.x | `./scripts/acceptance.sh` (Docker acceptance, incl. restart persistence and `--offline`), the containerised pytest and the Playwright e2e flow in `backend/tests/e2e`. **Run these on the submission machine before submitting.** |

## Not tested / outstanding
1. **GPU path:** the `gpu` image (CUDA 12.8, cuDNN 9, onnxruntime-gpu) was **not built or run**: no GPU and
   insufficient disk in the test environment. CUDA auto-selection is implemented with a CPU fallback, but is unverified.
2. **A physically separate computer, macOS, Windows/WSL and Apple Silicon:** not tested. Independence was simulated on
   the same host.
3. **Model accuracy:** the developer-reported 70.63% / 85.66% / 66.68% was **not re-measured** here, because the
   datasets are excluded. Only runtime equivalence with the checkpoint was measured.
4. **Nutrition values** are transcribed or approximate (unverified); 7 classes have no record.
5. **Optional components** (Redis cache profile, Ollama SLM profile) were not exercised in this run; the app ran
   with both absent.
6. **Verification emails** need SMTP; sending was not exercised (links were verified directly in tests).
7. **Training on user data** has not happened yet: no real dataset version has been exported, trained or gated.
8. **Development home-server hosting** (Cloudflare Tunnel, host hardening) is in the repository only. It was
   partly tested earlier (hardened stack, rate limits, backup/restore), not against real Cloudflare or Tailscale accounts.

## v0.13.2: mark a food on the photo (28 Oct 2026)
Executed locally (CPU, Python venv + PostgreSQL 16, built frontend served by the backend, Playwright Chromium).

| Test | Result |
|---|---|
| pytest | **59 passed** (adds 3 region tests): a box drawn over the pizza on the test plate becomes a drawn item whose top three include pizza, and survives re-analysis; an item added by description gets a box and keeps its name; too-small, out-of-range and missing-view boxes refused (422); another user's meal 404 |
| Draw a box, desktop mouse (1280 px) | **PASS**: Add missing food → Mark it on the photo → drag → new item 4 *pizza* (107 g), selected; no JS errors, no horizontal overflow |
| Draw a box, phone touch (iPhone 13 profile, pointer events) | **PASS**: touch drag → new item *pizza*, scrolled into view and selected; no JS errors, no horizontal overflow |
| Meal composition (v0.13.1 chart) | Renders in the review page under **Meal composition** (collapsed in Simple view) |

## v0.13.3: image names per Compose project (28 Oct 2026)

| Test | Result |
|---|---|
| `docker compose config` | Not run here (no Docker in this environment). Checked by reading: the default project resolves to the unchanged `mealsenseai/…:local` names; `COMPOSE_PROJECT_NAME=mealsense-acceptance` resolves to `mealsense-acceptance/…:local` |
| Fresh-database startup (v0.13.2 code) | **PASS**: all 7 migrations applied to an empty PostgreSQL 16 database and the API started |

## v0.13.4: insights collapsed by default (28 Oct 2026)

| Test | Result |
|---|---|
| Meal page (Playwright, desktop 1280 px and iPhone 13) | **PASS**, no JS errors, no horizontal overflow: eight insight rows closed under **Insights**, each with its one-line summary |
| Type check and build | **PASS** (no backend change) |

## v0.13.5: pick found regions; memory for drawn boxes (28 Oct 2026)

| Test | Result |
|---|---|
| pytest | **60 passed** (adds 1): a box drawn over a weak region, named as a custom food, is recognised from memory when the same box is drawn on a new photo of the plate (origin memory, similarity ≥ 0.7, model guess kept) |
| Pick a found region (Playwright, desktop and iPhone 13; a sushi photo with 9 hidden regions) | **PASS**: 9 and 8 dotted outlines shown; + Add adds the region as an item; no JS errors, no horizontal overflow |
| Draw a box (regression) | **PASS** on desktop mouse and phone touch |

## v0.13.6: marking hint in both themes (28 Oct 2026)

| Test | Result |
|---|---|
| Marking hint (Playwright, iPhone 13, light and dark) | **PASS**: dark text on light grey in light mode, light text on dark navy in dark mode, brand outline in both |

## v0.13.7: choose unidentified foods in the Meal Advisor (28 Oct 2026)

| Test | Result |
|---|---|
| pytest | **62 passed** (adds 2): name buttons only for the unidentified items and only with the region's own guesses; the button's request names the item; "you missed something" offers Mark it on the photo; a found-but-unlisted region is offered and restored |
| Advisor flow (Playwright, desktop and iPhone 13) | **PASS**: "What are the unidentified items?" → six name buttons for two items; tapping one names the item; "You missed something" → Mark it on the photo closes the advisor and opens marking mode; no JS errors, no horizontal overflow |

## v0.13.8: borrowed GI for dishes without a published value (28 Oct 2026)

| Test | Result |
|---|---|
| pytest | **64 passed** (adds 2): the rules pick the staple (chicken rice → white rice, char kway teow → noodles, roti prata → white bread, teh tarik → sweetened drink) and leave "no noodles", cereal prawns, water, black coffee and plain chicken alone; a published GI is never replaced; a chicken rice meal gets GL = 73 × available carbs / 100, a level, and a labelled reason. One expectation changed on purpose: kaya toast + egg + kopi is now rated unhealthy (borrowed GL 34.4 ≥ 20) |
| Meal page (Playwright, iPhone 13) | **PASS**: chicken rice + teh tarik shows HIGH, "glycaemic load ≈66.3" with an info tip, and per-food "≈53.3 (GI borrowed from white rice)"; no JS errors, no horizontal overflow |

## v0.13.9: presentation video kit (29 Oct 2026)

| Test | Result |
|---|---|
| `voice.py mine → build → splice` with synthetic stand-ins (tones for the voice lines, colour-bar takes `01-05.mp4`, `16.mp4`, `17-25.mov`) | **PASS**: final cut in script order, 1920×1080, 30 fps, AAC 48 kHz stereo; video 48.30 s, audio 48.32 s (padded to picture, no drift) |
| `record.mjs` with the full script's scenes (short lines) against the local app | **PASS**: all 21 screen and card scenes ran; a box dragged on the photo added item 4 and a tap on a guess named it; cards fit 1080p |
| Not run here | The Buddy run with the real demo stack, the Kokoro preview and your own recordings |

## v0.13.12: aligned with the submitted proposal (29 Oct 2026)

| Test | Result |
|---|---|
| Report build (`node docs/report/build_report.js`) and LibreOffice render | **PASS**: 21 pages, tables and the renamed pipeline figure fit |
| `node --check demo/record.mjs`, narration JSON parses | **PASS** |
| App | No change; tests not re-run |

## v0.13.13: meal explanations validated (29 Oct 2026)

| Test | Result |
|---|---|
| pytest | **65 passed** (adds 1): an SLM explanation with a number not in the facts is stored as `rejected` with the failing numbers, its text is not shown, and the rule-based recommendations remain |
| Frontend typecheck | PASS |
| Not run here | The Buddy run with the real model; expect most explanations from qwen2.5:1.5b to be rejected (1 of 6 passed in E6) |

## v0.13.18: declarations; training and configuration scenes (29 Oct 2026)

| Test | Result |
|---|---|
| `record.mjs` training and settings scenes against the local app (admin granted with `app.tools.admin`) | **PASS**: the training card with both charts fits 1080p; the settings scene runs 68 s for a 68 s line, pointing at the thresholds, memory match, model, temperature and time limit, then the prompts page |
| Report build and render | **PASS**: declarations tables fit |
| Not run here | `DEMO_SLM=1` against the live Ollama on Buddy |

## v0.13.19: TF-IDF and embedding evaluations (29 Oct 2026)

| Test | Result |
|---|---|
| `app.tools.tfidf_eval` on the local food table | **Ran**: results above (`docs/report/tfidf_eval.json`) |
| `embedding_eval.py` analysis functions on synthetic clusters | **PASS**: perfect labels give NMI = ARI = 1; random labels ARI ≈ 0; silhouette matches a direct computation |
| Not run here | `embedding_eval.py` on the real test images (needs Buddy, PyTorch and the datasets) |

## v0.13.20: final presentation kit (29 Oct 2026)

| Test | Result |
|---|---|
| `voice.py mine → build → splice` with stand-in takes (two full-screen, two corner) | **PASS**: corner window in the demo stretch, held between lines; final video 16.17 s, audio 16.17 s (no drift) |
| `record.mjs` with every new figure scene against the local app | **PASS**: all scenes ran; figures fit 1080p and stay clear of the presenter's corner |
| Not run here | The Buddy run with the real takes |

## v0.13.21: video build fix (30 Oct 2026)

| Test | Result |
|---|---|
| `wipe` as an ordinary user on a folder owned by root (Docker stubbed) | **PASS**: plain `rm` refused, falls back to removing it through the voice container; script carries on |
| `wipe` on the user's own folder | **PASS**: removed directly, no container |
| `bash -n demo/run.sh` | **PASS** |
| Not run here | The Buddy run with the real takes (no Docker daemon in this environment) |

## v0.13.22: title, statistics and closing cards (30 Oct 2026)

| Test | Result |
|---|---|
| Title card + a 25 s stand-in camera take with both statistic cards + closing card, joined with `-c copy` | **PASS**: 5 s + 25 s + 7 s = 37.0 s video, 37.02 s audio; every piece 1920×1080, 30 fps, square pixels, 48 kHz stereo |
| Frames from that cut | **PASS**: title card; first card only at 4 s into the take; both cards at 10 s; closing card |
| `run.sh splice` with Docker stubbed | **PASS**: picks the latest build, copies the current script into it, runs the splice; refuses a folder without recordings |
| Not run here | The Buddy re-splice with the real takes |

## v0.13.23: statistics as slides (30 Oct 2026)

| Test | Result |
|---|---|
| "burden" stand-in take (first number at 1.4 s) | **PASS**: whole take is the slide, take in the lower-right corner, both cards fade in; 24.97 s video, 24.99 s audio |
| A 40 s stand-in take with its number at 31.6 s | **PASS**: full screen, then fades to the slide; 39.97 s video, 39.99 s audio |
| Both joined with `-c copy` | **PASS**: 65.0 s, no drift |
| Not run here | The Buddy re-splice with the real takes |
