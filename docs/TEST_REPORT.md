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
6. **Development home-server hosting** (Cloudflare Tunnel, host hardening) is in the repository only. It was
   partly tested earlier (hardened stack, rate limits, backup/restore), not against real Cloudflare or Tailscale accounts.
