"""Process and system diagrams for the final report (requested in review). Numbers come from the evidence files
named on each figure; the multi-food figure uses a screenshot from test-results/ui-multifood and the live model."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = Path(__file__).parent
OUT = HERE / "charts"
REPO = Path("/home/user/MealSenseAI-repo")
TEAL, BLUE, ORANGE, AQUA, GREY = "#147D73", "#2a78d6", "#eb6834", "#1baf7a", "#b4b2ab"
INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "DejaVu Sans", "savefig.dpi": 220, "savefig.bbox": "tight"})


def box(ax, x, y, w, h, title, body="", edge=TEAL, fill="#F3F8F7", ts=7.6, bs=6.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.06", fc=fill, ec=edge, lw=1.3))
    ax.text(x + w / 2, y + h - 0.07, title, ha="center", va="top", fontsize=ts, weight="bold", color=INK)
    if body:
        ax.text(x + w / 2, y + h - 0.27, body, ha="center", va="top", fontsize=bs, color=INK2, linespacing=1.3)


def arrow(ax, x1, y1, x2, y2, label="", color=INK2, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=8, color=color, lw=1.2, ls=ls))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.04, label, ha="center", va="bottom", fontsize=6.2, color=color)


def canvas(w, h, title):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 0.92)
    ax.set_title(title, loc="left", fontsize=11.5, weight="bold", color=INK)
    return fig, ax


def save(fig, name, source):
    fig.text(0.01, -0.02, f"Source: {source}", fontsize=7.2, color=INK2, ha="left", va="top")
    fig.savefig(OUT / name); plt.close(fig); print("wrote", name)


TR = REPO / "ml/models/exp002/evidence/training"
clean = json.loads((TR / "cleaning_summary.json").read_text())
splits = clean["split_counts"]


def row(ax, steps, x0, y, w, h, gap, edges=None, rev=False):
    for i, (t, b) in enumerate(steps):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, t, b, edge=(edges or {}).get(t, TEAL))
        if i < len(steps) - 1:
            a, b2 = (x + w + gap, x + w) if rev else (x + w, x + w + gap)
            arrow(ax, a, y + h / 2, b2, y + h / 2)


# 14. Data preparation
fig, ax = canvas(6.8, 2.55, "Data preparation (Section 3.3)")
row(ax, [("1 Collect", "Food-101: 101,000\nFoodSG-233: 209,861\ntotal 310,861"),
         ("2 Harmonise", "334 class names\n→ 324 normalised\n→ 320 classes"),
         ("3 Audit", "SHA-256 per file\n2,040 duplicate\ngroups found"),
         ("4 Clean", "4,193 excluded\n(conflicting labels,\nduplicates) → 306,668"),
         ("5 Split", "Food-101: official\ntest + 10% val\nFoodSG: 80/10/10")], 0.05, 1.2, 1.18, 0.95, 0.17)
tr = splits["Food101_train"] + splits["FoodSG233_train"]; va = splits["Food101_val"] + splits["FoodSG233_val"]; te = splits["Food101_test"] + splits["FoodSG233_test"]
for i, (t, n, col) in enumerate([("Training", tr, BLUE), ("Validation", va, AQUA), ("Test (held out)", te, ORANGE)]):
    x = 1.4 + i * 1.75
    box(ax, x, 0.08, 1.55, 0.6, t, f"{n:,} images", edge=col, fill="white")
    arrow(ax, 6.15, 1.2, x + 0.78, 0.68, color=col)
save(fig, "14_data_prep.png", "evidence/training: dataset_inventory.json, cleaning_summary.json, dataset_splits.json, derived_summary.json")

# 15. Training and deploying the classifier
h1 = json.loads((TR / "EXP-001_UnifiedFood/summary.json").read_text()); h2 = json.loads((TR / "EXP-002_FineTuning/summary.json").read_text())
ov = json.loads((TR / "EXP-002_FineTuning/evaluation/overall_metrics.json").read_text())
fig, ax = canvas(6.8, 1.7, "Training and deploying the food classifier (Section 3.4)")
row(ax, [("Start", "EfficientNet-B0\nImageNet\nweights"),
         ("EXP-001", f"new head,\nbackbone frozen\nval F1 {h1['best_validation_macro_f1']*100:.1f}%"),
         ("EXP-002", f"+ last 3 blocks\nlower lr, 5 ep.\nval F1 {h2['best_validation_macro_f1']*100:.1f}%"),
         ("Test", f"{ov['test_images']:,} img\ntop-1 {ov['accuracy']*100:.1f}%\ntop-3 {ov['top3_accuracy']*100:.1f}%"),
         ("Export", "ONNX\nsame top-3\n601 / 601"),
         ("In the app", "ONNX Runtime\nCPU\n~12 ms / photo")], 0.05, 0.1, 0.97, 1.0, 0.15, {"Test": ORANGE})
ax.text(1.65, 1.2, "RTX 5060 Ti on Buddy, ~20 min per stage", ha="center", fontsize=6.4, color=INK2)
save(fig, "15_training_flow.png", "EXP-001/EXP-002 config.json, summary.json, overall_metrics.json; evidence/onnx_parity.json")

# 16. Multi-food evidence
from PIL import Image
img = Image.open(HERE / "mfcrop.png")
fig = plt.figure(figsize=(6.8, 2.9))
ax1 = fig.add_axes([0.0, 0.02, 0.45, 0.86]); ax1.imshow(img); ax1.axis("off")
fig.text(0.0, 0.95, "Regions found on a test plate (app screenshot)", fontsize=8.6, weight="bold")
fig.text(0.48, 0.95, "What the classifier returned for each region", fontsize=8.6, weight="bold")
ax2 = fig.add_axes([0.48, 0.02, 0.52, 0.86]); ax2.axis("off"); ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
hdr = [(0.0, "#"), (0.06, "Actual"), (0.24, "Top score"), (0.43, "Top 3 guesses")]
for x, t in hdr:
    ax2.text(x, 0.95, t, fontsize=7.2, weight="bold", color=INK)
rows = [("1", "sushi", "0.79", "sushi, spring rolls, ceviche", "named as sushi"),
        ("2", "pizza", "0.29", "pizza, sambal, pineapple tarts", "below 0.45: shown as unidentified;\nthe user taps pizza in the top 3"),
        ("3", "steak", "0.43", "lamb chops, sirloin steak,\nfilet mignon", "below 0.45: shown as unidentified;\nthe user picks or searches")]
y = 0.87
for r in rows:
    for (x, _), t in zip(hdr, r[:4]):
        ax2.text(x, y, t, fontsize=7.0, color=INK, va="top")
    ax2.text(0.06, y - 0.1, "→ " + r[4], fontsize=6.6, color=TEAL, va="top")
    y -= 0.24
ax2.text(0.0, 0.0, "All 100 test plates (263 foods): precision 74.7%, recall 68.4%,\nAP50 0.59; 262 ms median on CPU (Figure in Section 6.1).", fontsize=6.6, color=INK)
save(fig, "16_multifood_evidence.png", "test-results/ui-multifood/06_analysis_review.png; vision.analyze on tests/fixtures/multi_food_plate.jpg; multifood_metrics.json")

# 17. Meal Advisor
fig, ax = canvas(6.8, 1.9, "How the Meal Advisor answers (Section 3.8)")
row(ax, [("Question", "from the user,\nmeal or week\nin view"),
         ("Rule engine", "facts from meals,\nprofile, food table,\nsource-tagged"),
         ("Local SLM", "Qwen 2.5 1.5B\nrewords the draft\n(if available)"),
         ("Validator", "numbers ±2%\nno new foods\nno unsafe advice")], 0.05, 0.55, 1.15, 0.95, 0.25,
    {"Rule engine": BLUE, "Local SLM": AQUA, "Validator": ORANGE})
box(ax, 5.65, 1.08, 1.1, 0.5, "Pass", "reworded answer", fill="white")
box(ax, 5.65, 0.42, 1.1, 0.5, "Fail", "rule draft shown", fill="white", edge=ORANGE)
arrow(ax, 5.25, 1.15, 5.65, 1.33); arrow(ax, 5.25, 0.9, 5.65, 0.67)
ax.text(3.4, 0.12, "Medication questions, urgent readings, or the model offline or slow: the rule answer is shown directly.", ha="center", fontsize=6.4, color=INK2)
save(fig, "17_advisor_flow.png", "backend/app/services/advisor.py (answer, phrase, validate)")

# 18. Learning safely
fig, ax = canvas(6.8, 2.55, "Learning from users safely (Section 3.9)")
row(ax, [("User names a food", "on a region\nof the photo"),
         ("Personal memory", "fingerprint kept;\nreused at cosine\n≥ 0.70, no retraining"),
         ("Consent", "training share\nis off by default"),
         ("Screening", "11 automatic\nchecks"),
         ("Human review", "of flagged\nsamples")], 0.05, 1.35, 1.17, 0.85, 0.2, {"Personal memory": AQUA, "Consent": GREY})
row(ax, [("Admin promotes", "or rolls back;\nall audited"),
         ("Shadow mode", "≥ 200 foods,\n≥ 90% agreement"),
         ("Model gate", "top-1 within 0.2 pts;\nsafety foods\nno worse"),
         ("Dataset version", "frozen, consented\nsamples only")], 0.73, 0.1, 1.2, 0.85, 0.3, {"Admin promotes": BLUE, "Shadow mode": ORANGE, "Model gate": ORANGE}, rev=True)
arrow(ax, 6.12, 1.35, 6.12, 0.95)
save(fig, "18_learning_flow.png", "backend/app/services/memory.py, screening.py, datasets.py, gate.py; docs/ADMIN.md")

# 19. Detailed system diagram
fig, ax = canvas(6.8, 3.9, "MealSenseAI system: components and data flow (Section 4.3)")
ax.text(3.4, 3.62, "Docker Compose on one CPU server; no cloud AI service", ha="center", fontsize=6.6, color=INK2)
box(ax, 0.05, 2.8, 1.5, 0.75, "Browser", "React + TypeScript\nphone or desktop")
box(ax, 1.95, 2.8, 1.4, 0.75, "nginx", "app + /api proxy\nrate limits")
arrow(ax, 1.55, 3.17, 1.95, 3.17, "HTTPS")
box(ax, 5.2, 2.8, 1.55, 0.75, "Ollama (optional)", "Qwen 2.5 1.5B\nlocal, CPU", edge=AQUA)
ax.add_patch(FancyBboxPatch((0.05, 0.75), 4.85, 1.85, boxstyle="round,pad=0,rounding_size=0.06", fc="none", ec=TEAL, lw=1.2, ls="--"))
ax.text(0.12, 2.45, "FastAPI backend (one process; models loaded once)", fontsize=7.2, weight="bold", color=TEAL)
arrow(ax, 2.65, 2.8, 2.65, 2.6)
for i, (t, b, e) in enumerate([("API routers", "auth, meals, foods,\nadvisor, admin", TEAL), ("Pipeline", "10 stages\nanalysis.py", TEAL), ("Vision", "YOLO11n-seg +\nEfficientNet-B0", BLUE)]):
    box(ax, 0.15 + i * 1.6, 1.62, 1.45, 0.72, t, b, edge=e)
for i, (t, b) in enumerate([("Portion, nutrition", "priors, plate area,\nfood table, GI rules"), ("Insights, forecast", "GL, glucose model,\nwhat-if, advice"), ("Advisor, memory", "rules, validator,\nfingerprints")]):
    box(ax, 0.15 + i * 1.6, 0.83, 1.45, 0.7, t, b)
arrow(ax, 1.6, 1.98, 1.75, 1.98); arrow(ax, 3.2, 1.98, 3.35, 1.98)
box(ax, 5.2, 1.75, 1.55, 0.8, "PostgreSQL 16", "users, meals, foods,\ncorrections, logs", edge=INK2)
box(ax, 5.2, 0.8, 1.55, 0.7, "Volume", "photos, models", edge=INK2)
arrow(ax, 4.9, 2.1, 5.2, 2.1, "SQL"); arrow(ax, 4.9, 1.15, 5.2, 1.15); arrow(ax, 4.9, 2.5, 5.45, 2.8, "HTTP")
box(ax, 0.6, 0.05, 1.7, 0.55, "Redis (optional)", "cache", edge=GREY, fill="white")
box(ax, 2.7, 0.05, 2.0, 0.55, "Admin settings", "thresholds, model, prompts", edge=GREY, fill="white")
save(fig, "19_system_detail.png", "docker-compose.yml; backend/app/api, backend/app/services; docs/ARCHITECTURE.md")

# 20. Experiments: input → method → output
rows = [("E1", "45,800 test images", "classify; compare with labels", "overall_metrics.json", "top-1 70.6%, top-3 85.7%"),
        ("E2", "601 images", "PyTorch vs ONNX", "onnx_parity.json", "601/601 same top-3"),
        ("E3", "100 plates, 263 foods", "detect + classify", "multifood_metrics.json", "P 74.7%, R 68.4%"),
        ("E4", "38 questions", "ask the advisor", "advisor_eval.json", "38/38, 0 unsupported"),
        ("E5", "20 meals, 15 names", "rule parser, lookup", "baselines.json", "F1 0.987; 7/15 right"),
        ("E6", "E5 sets + 14 texts", "local SLM on Buddy", "slm_eval.json", "F1 0.732; 7/8 pass"),
        ("E7", "fresh deployment", "sign-up to restart", "acceptance_*.json", "9/9 checks pass"),
        ("E8", "chicken rice meal", "glucose model", "forecast run", "walk −2.3%, rice −23%")]
fig, ax = canvas(6.8, 3.6, "Experiments: input → method → output (Section 5)")
cols = [(0.05, 0.38, "", TEAL), (0.55, 1.4, "Input", INK2), (2.1, 1.5, "Method", BLUE), (3.75, 1.45, "Output file", INK2), (5.35, 1.4, "Result", ORANGE)]
for (x, w, h, c) in cols[1:]:
    ax.text(x + w / 2, 3.12, h, ha="center", fontsize=7.4, weight="bold", color=c)
for i, r in enumerate(rows):
    y = 2.7 - i * 0.37
    for j, (x, w, h, c) in enumerate(cols):
        ax.add_patch(FancyBboxPatch((x, y), w, 0.28, boxstyle="round,pad=0,rounding_size=0.05", fc=TEAL if j == 0 else "white", ec=c, lw=1.0))
        ax.text(x + w / 2, y + 0.14, r[j], ha="center", va="center", fontsize=6.4, color="white" if j == 0 else INK, weight="bold" if j in (0, 4) else "normal")
        if 0 < j < 4:
            arrow(ax, x + w, y + 0.14, cols[j + 1][0], y + 0.14)
save(fig, "20_experiments_flow.png", "test-results/, ml/models/exp002/evidence/, docs/report/slm_eval.json, baselines.json")
