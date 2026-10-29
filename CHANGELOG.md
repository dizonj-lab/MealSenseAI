# Changelog

High-level changes per release. The running version is shown next to the logo and on the About page.

## v0.13.20 — Final presentation kit (no app change)

- `demo/narration-final.json`: 23 segments, about 11 minutes of speech (12–13 with the demo): opening on camera,
  the live demo, how the system was evaluated and what the results mean, the system design, limits and close.
  Lines are `camera` (full screen) or `pip` (the presenter's video in the bottom-right corner over the demo).
- `voice.py`: `mine` cuts each take's audio and, for `pip` lines, its video at the same speech bounds (lip sync
  kept); `splice` overlays the presenter on the demo stretches, holding the last frame between lines, and fades
  between pieces; the recording script names every take `NN.mp4` and says full screen or corner.
- `record.mjs`: scenes for the new segments (review + marking, portion + walk, and full-screen report figures for
  the evaluation and the design), kept clear of the presenter's corner. `run.sh` mounts `docs/report/charts` into
  the recording container (the figure scenes failed there before).

## v0.13.19 — TF-IDF and embedding evaluations (no app change)

- `python -m app.tools.tfidf_eval`: character 3–5-gram TF-IDF with cosine 1-nearest-neighbour for food names,
  against the fuzzy lookup, on the 15 unknown names and on 480 held-out aliases (leave one alias out). Result in
  `docs/report/tfidf_eval.json`: on held-out aliases 320 correct / 75 wrong / 85 no match at cosine ≥ 0.6, against
  108 / 24 / 348 for the lookup; on the 15 names 10 / 2 / 3 against 7 / 4 / 4 (language model 4 / 6 / 5).
- `ml/evaluation/embedding_eval.py` (run on the training machine): the classifier's 1280-value features for a
  stratified test sample; PCA explained variance and k-NN accuracy after reduction, cosine k-NN (k = 1, 5, 10) next
  to the linear head, k-means against the labels (NMI, ARI, purity), silhouette, and 2-D PCA points. NumPy only.

## v0.13.18 — Declarations; training and configuration in the video (no app change)

- Report: a Declarations section (AI tools used and what they produced, datasets and third-party sources with terms
  and citations, the author's scope of work with evidence), with highlighted placeholders for the author to
  complete; a model-configuration table; nutrition approximations corrected to 204 records.
- Video (`narration-full.json`, `record.mjs`): the model line is shortened and followed by "Training the model"
  (data audit, split, two-stage training, results and calibration, over the report's training charts) and, after
  "Learning safely", "Configuring the models" (admin settings and versioned prompts, paced to the narration).
  `run.sh` gives the demo account the admin role; `DEMO_SLM=1` lets the demo use the live stack's Ollama
  (`docker-compose.demo-slm.yml`). Recording files after line 19 are renumbered.
- `model_card.json`: the metrics source now points to the training evidence.

## v0.13.17 — Training evidence (no app change)

- `ml/models/exp002/evidence/training/`: EXP-001 and EXP-002 configuration, environment, training history, test
  evaluation (overall, per dataset, classification report, calibration, confusion matrix), data cleaning and split
  summaries, from the training run on Buddy. `docs/report/derive_training_evidence.py` copies them and derives
  per-class F1, per-dataset results, top confusions and confidence bands (`derived_summary.json`).
- Report: E1 is now measured evidence (45,800 test images); new figures for training curves, calibration (ECE 2.35%)
  and per-class F1. Corrected the data split: Food-101 official test + 10% validation, FoodSG-233 80/10/10
  (232,713 / 28,155 / 45,800), not the 70/15/15 in the proposal and `ml/training/config.yaml`.

## v0.13.16 — Report wording (no app change)

- `docs/report/build_report.js`: paragraphs rewritten in plain, first-person report language, limited to each
  section's topic; figures and tables unchanged.

## v0.13.15 — For anyone, diabetes first (no app change)

- Positioning in the report, slides and video script: MealSenseAI serves anyone, with or without a health condition
  (the profile's goals already cover wellness, weight, heart health and balanced eating); diabetes stays the first
  focus, as proposed. Narration: the value and closing lines; the value card adds a "for anyone" line.

## v0.13.14 — Individual project wording (no app change)

- Report cover, slide covers and the video script: an individual project (no group); "we/our" became "I/my" in the
  three narration lines that used it (gap, pricing, model).

## v0.13.13 — Meal explanations are validated

- The local SLM's meal explanation (stage 8) now passes the Meal Advisor's validator before it is shown: every number
  must come from the meal's facts (±1 or 2%), no new food names, no unsafe statements. A failing explanation is not
  shown (`source: "rejected"`, with the check stored for audit); the rule-based results stay. Found by the E6
  benchmark on Buddy, where 5 of 6 explanations contained a number of their own.
- Test: an explanation stating an unsupported number is rejected and the recommendations remain (65 tests).

## v0.13.12 — Aligned with the submitted proposal (no app change)

- Report, slides and video script harmonised with the proposal of 30 September 2026: pricing is freemium with a
  subscription at S$3.99/month (Singapore) and S$2.99/month (ASEAN), replacing S$4.90/S$39; MVP users are people with
  Type 1 and Type 2 diabetes; competitors and the IDF market scenario are the proposal's; the pipeline chart uses the
  proposal's ten stage names.
- Report: a data section (FoodSG-233 + Food-101, 70/15/15), a "proposed vs built" table, and the proposal's
  validation measures against the results, including the gap: portion error (MAE) has not been measured.
- `demo/`: pricing line, pricing card and sources updated.

## v0.13.11 — Final report sources (no app change)

- `docs/report/`: the figure script (`make_charts.py`, ten charts from the evidence files and the app's own models),
  the Word report builder (`build_report.js`) and the generated charts. The language-model section fills in from
  `slm_eval.json` when it is added.

## v0.13.10 — Language model evaluation (no app change)

- `python -m app.tools.slm_eval` measures the local SLM on fixed inputs with known answers: description parsing
  (20, against the rule-based splitter), unknown-name matching (15, 10 in the table and 5 absent, against the fuzzy
  lookup), meal explanations (6, number grounding by the advisor's validator) and Meal Advisor rewording (8 drafts,
  validator pass rate), with latency and tokens per second. Read-only: no call log, no cache.

## v0.13.9 — Presentation video kit (no app change)

- `demo/narration-full.json`: a 26-line, ~12-minute presentation in two halves (business case with pricing; system
  design with the technical use cases). Lines are marked **camera** (the presenter) or **screen** (the app demo).
- `run.sh script` writes `RECORDING-SCRIPT.md`; `run.sh mine` takes the presenter's own files (audio for screen
  lines, video for camera lines, `01-05.mp4` for one take of several lines), records only the screen scenes timed to
  that voice, and `voice.py splice` joins everything in script order at 1080p/30 fps/-16 LUFS with audio padded to
  picture (no lip-sync drift). The demo stretches are also written separately for manual editing.
- `record.mjs` scenes are a registry chosen by the script; new scenes: marking a missed food on the photo, and title
  cards for the burden, the gap, value, pricing, architecture, pipeline, model, multi-food, nutrition/GI, the glucose
  model, the grounded advisor, safe learning and quality. Key takeaways is opened now that it is collapsed (0.13.4).
- `demo/SOURCES.md` lists the source of every figure in the script.

## v0.13.8 — Glycaemic load for more local dishes

- 229 of 286 foods have no published GI, so most meals showed "Glycaemic load not estimated". A food without one now
  borrows the GI of its main carbohydrate by fixed rules in `services/nutrition.py` (`GI_RULES`): rice dishes → white
  rice, noodle dishes → udon, breads and roti → white bread, sweetened drinks → sugar-sweetened soft drink, and so on.
  78 foods are covered; the rest (meat, vegetables, most kueh and fruit) stay unestimated.
- Where a choice exists the higher-GI staple is used, so a borrowed value errs towards a higher glycaemic load.
  "No noodles" in a name, and drinks under 4 g carbohydrate per 100 g (water, black coffee, wine, beer), never borrow.
- Shown as "glycaemic load ≈…" with the food it was borrowed from (Key takeaways, Meal composition, the reasoning).
  The same GI feeds the forecast. A published GI is never replaced. No language model is involved.
- A meal's rating can change: kaya toast with sweetened kopi now has a high glycaemic load and is rated unhealthy.

## v0.13.7 — Name unidentified foods from the Meal Advisor

- Asking about the unidentified (unknown, unnamed) items lists each item's own top guesses and offers buttons:
  **"Unidentified food 1 is pizza"** names it (only guesses with a food-table record; nothing invented),
  **Add region …** adds a region the detector found but did not list, and **Mark it on the photo** opens marking mode
  on the meal page (`/meals/{id}?mark=1`). "You missed something" without a named food offers the photo as well.
- Naming from the advisor is the same request as on the meal page, so it feeds personal memory in the same way.

## v0.13.6 — Readable marking hint

- The marking hint uses theme tokens (`slate-100` / `slate-800`, brand outline), so it is readable in light and dark
  mode; it sits above the photo so it never covers a found region's **+ Add**

## v0.13.5 — Pick or remember missed foods

- In **Mark it on the photo**, regions the detector found but did not list (the "Possible additional items") are shown
  as dotted outlines; **+ Add** adds one. Only the tag takes taps, so a box can still be dragged anywhere.
- A drawn box is checked against the user's personal memory when the model is unsure (same threshold and margin as
  analysis); a match is shown as "Known from your earlier label", with the model's own guess kept for reference.

## v0.13.4 — A calmer meal page

- Key takeaways and Ask the Meal Advisor are collapsible like the other insights; all are grouped under **Insights**
  and closed in Simple view, each showing its key point on one line (glucose impact and first tip; kcal and carbs; advisory status)
- Allergy warnings are never collapsed; Detailed view opens every section as before

## v0.13.3 — Safer side-by-side installs

- Docker images are named after the Compose project (`${COMPOSE_PROJECT_NAME:-mealsenseai}/backend:local`), so a
  second copy on the same server, such as an acceptance run, builds its own images instead of replacing the live ones.
  The live stack's names are unchanged. The test stack (`scripts/test.sh`) uses `mealsenseai-test/…`.

## v0.13.2 — Mark a food on the photo

- Add missing food → **Mark it on the photo**: drag a box around the food (mouse, finger or pen). The model classifies
  only that box and estimates the portion from its size; a weak guess becomes an unidentified item with its top three
- Items added by name or description can be given a box (**Show where it is on the photo**); the name is kept
- Drawn items survive re-analysis; new endpoints `POST /meals/{id}/regions` and `PUT /meals/{id}/foods/{fid}/region`

## v0.13.1 — Clearer meal composition

- Meal composition redesigned in one teal palette: the meal at a glance, where its energy comes from, and each
  nutrient against your day (your goals, the WHO sodium limit, a fibre guideline, saturated fat under 10% of energy)
- Amber only when one meal alone goes past its share of a limit; missing nutrient values are shown as missing
- Inside the carbohydrate (sugar, starch, fibre) with glycaemic load; food-by-food comparison by carbs, kcal or sodium
- Documentation and database schema brought up to date for the submission

## v0.13.0 — Safer learning from your photos

- Sharing corrected photos for training is now tracked per photo; switching it off withdraws everything shared from future training
- Settings shows what you shared, what was accepted and what is in review; confirm your email to let shared photos be used
- Every shared photo is screened automatically (duplicates, implausible or carbohydrate-lowering relabels, repeated patterns,
  contributor caps, outliers); flagged ones and a random audit sample are reviewed by a person
- Admin area: review queue, contributors, frozen dataset versions, a model gate with shadow mode, model package uploads,
  model settings and versioned prompts, and an audit log (see docs/ADMIN.md)

## v0.12.0 — Watch the demo

- A four-minute narrated tour, from the landing page (beside Get Started and in the top bar) and from About MealSenseAI
- Plays in a window over the page, with subtitles; Escape or a click outside closes it

## v0.11.0 — Contact form and creator links

- Contact page now has a form; messages are saved and emailed to the creator
- Removed the draft notices from the Privacy, Terms and Contact pages
- Creator profile links to LinkedIn

## v0.10.0 — Glucose estimates in mmol/L

- Forecast and portion simulator charts now show glucose in mmol/L (or mg/dL from your profile) instead of a relative index
- Starts from your logged pre-meal reading; without one, the chart shows the estimated rise above your pre-meal level
- Population estimate with a wide range; after 3 meals with before and after readings it calibrates to your own response
- Always labelled an estimate, even with a known baseline; your measured readings are shown as dots for comparison

## v0.9.0 — A friendlier Meal Advisor

- Warm, witty personality that adapts its tone: playful for food chat, careful for diabetes topics, serious for urgent ones
- “You missed my sausage!” offers a one-tap Add button; the meal updates when you tap it
- Handles “is this too much rice?”, “can I eat pizza?”, mystery dishes and questions it cannot answer, honestly
- Remembers the food you are talking about: “Is nasi lemak healthy?” → “What if I skip the rice?” → “What about adding an egg?”

## v0.8.0 — Minimal design, grounded conversations

- New minimalist landing, sign-in and register pages; Privacy, Terms and Contact pages (drafts)
- Onboarding is now enforced by the server; age range, other goals and a “why we ask” note added
- Meal Advisor rebuilt: every fact is traced to you, the photo model, the food table or approved guidance
- Follow-up questions, “what if I remove the rice?” (never saved), how a food was identified, low-confidence checks
- Replies from the local language model are checked against your data; urgent and medication questions handled safely
- Conversations are kept on the server for 30 days and can be cleared

## v0.7.0 — Meal Advisor, About page, easier saving

- Meal Advisor chat grounded in your meals, profile and the food table; medication questions declined
- Meal type and Save pinned at the top of the meal review
- “Can’t find it?” pinned at the top of the food picker; short help tips on key controls
- Appearance setting (system / light / dark); version shown next to the logo; About page with datasets, model and evaluation

## v0.6.0 — Your own foods and food memory

- Create foods that are not in the list, with portion and nutrients (unknowns stay blank)
- Foods you name are recognised again from your earlier labels
- Opt-in export of corrected photo regions for the next training cycle

## v0.5.0 — Clearer, calmer interface

- Landing page before login and a getting-started checklist for new accounts
- Simple / Detailed meal review with “Why?” explanations on every card
- Pipeline progress bar with a telemetry drawer; dark and light mode
- AI explanation no longer delays results

## v0.4.0 — Multi-food recognition and health intelligence

- Every food on the plate detected, numbered and editable (rename, merge, remove, add)
- Meal composition dashboard, portion simulator and glycaemic-load breakdown
- Measured glucose readings (mmol/L) and personalised insights by goal

## v0.3.0 — EXP-002 model and portable deployment

- EXP-002 EfficientNet-B0 (320 Food-101 + FoodSG classes) served on CPU via ONNX Runtime, top-3 suggestions
- One-command Docker deployment, offline mode and the NUS submission package

## v0.2.0 — Forecasts and infrastructure

- Educational energy and glucose forecast with activity what-ifs, citations and cautions
- Docker Compose stack, test environment and home-server hardening guide

## v0.1.0 — First MVP

- Sign-up, health onboarding, meal capture, food recognition, nutrition estimates, insights and history
