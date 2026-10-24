# Changelog

High-level changes per release. The running version is shown next to the logo and on the About page.

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
