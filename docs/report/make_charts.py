"""Charts for the MealSenseAI final report and slides. Every number comes from the repository's evidence files
(paths in each docstring) or from the app's own models (model_data.json, made by the extraction step)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).parent
OUT = HERE / "charts"
OUT.mkdir(exist_ok=True)
REPO = Path("/home/user/MealSenseAI-repo")
DATA = json.loads((HERE / "model_data.json").read_text())

TEAL = "#147D73"           # brand; single-series charts
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"   # validated categorical slots 1-3 (light)
GREY = "#b4b2ab"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlelocation": "left", "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "figure.dpi": 100, "savefig.dpi": 220, "savefig.bbox": "tight", "axes.grid": False,
})


def save(fig, name, source):
    below = 0.12 + (0.32 if fig.axes[0].get_xlabel() else 0) + (0.62 if name.startswith("07") else 0)   # inches under the axes
    fig.text(0.01, -below / fig.get_size_inches()[1], f"Source: {source}", fontsize=7.5, color=INK2, ha="left", va="top", transform=fig.transFigure)
    fig.savefig(OUT / name)
    plt.close(fig)
    print("wrote", name)


def hbar(ax, labels, values, color=TEAL, fmt="{:.1f}%", xmax=100):
    y = range(len(labels))[::-1]
    ax.barh(list(y), values, height=0.5, color=color)
    for yy, v in zip(y, values):
        ax.text(v + xmax * 0.01, yy, fmt.format(v), va="center", fontsize=9.5, color=INK)
    ax.set_yticks(list(y), labels)
    ax.set_xlim(0, xmax * 1.12)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(left=False)


# 1. Classifier quality ------------------------------------------------------------------------------------------
card = json.loads((REPO / "ml/models/exp002/model_card.json").read_text())["metrics"]
fig, ax = plt.subplots(figsize=(6.4, 2.4))
hbar(ax, ["Top-1 accuracy", "Top-3 accuracy", "Macro-F1", "Validation macro-F1 (epoch 5)"],
     [card["reported_by_developer"]["top1_accuracy"] * 100, card["reported_by_developer"]["top3_accuracy"] * 100,
      card["reported_by_developer"]["macro_f1"] * 100, card["checkpoint_metadata"]["validation_macro_f1"] * 100])
ax.set_title("EXP-002 EfficientNet-B0, 320 classes")
save(fig, "01_model_metrics.png", "ml/models/exp002/model_card.json (developer evaluation; checkpoint metadata)")

# 2. Multi-food plates: what happened to each true item ------------------------------------------------------------
mf = json.loads((REPO / "test-results/multifood_metrics.json").read_text())
conf = mf["classification_on_matched"]["confusion"]
near = {"steak": {"sirloin steak", "filet mignon"}, "sushi": {"sashimi"}, "pizza": set()}
rows = {}
for k, n in conf.items():
    gt, pred = [s.strip() for s in k.split("->")]
    r = rows.setdefault(gt, {"Correct": 0, "Close variant": 0, "Left unidentified": 0, "Other class": 0})
    r["Correct" if pred == gt else "Close variant" if pred in near[gt] else "Left unidentified" if pred == "(unidentified)" else "Other class"] += n
order = ["pizza", "sushi", "steak"]
fig, ax = plt.subplots(figsize=(6.4, 2.3))
left = [0] * 3
for name, col in [("Correct", BLUE), ("Close variant", AQUA), ("Left unidentified", ORANGE), ("Other class", GREY)]:
    vals = [rows[g][name] / sum(rows[g].values()) * 100 for g in order]
    bars = ax.barh(range(3)[::-1], vals, left=left, height=0.5, color=col, label=name, edgecolor="white", linewidth=2)
    for b, v, l0 in zip(bars, vals, left):
        if v >= 8:
            ax.text(l0 + v / 2, b.get_y() + b.get_height() / 2, f"{v:.0f}%", ha="center", va="center", fontsize=8.5, color="white")
    left = [a + b for a, b in zip(left, vals)]
ax.set_yticks(range(3)[::-1], [f"{g} (n={sum(rows[g].values())})" for g in order])
ax.set_xlim(0, 100); ax.set_xlabel("share of matched items (%)"); ax.tick_params(left=False)
ax.legend(ncol=4, frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, 1.0))
ax.set_title(f"Multi-food plates: detection P {mf['detection']['precision']:.0%} · R {mf['detection']['recall']:.0%}; "
             f"classification of matched items", pad=22)
save(fig, "02_multifood_outcomes.png", "test-results/multifood_metrics.json (100 synthetic plates, 263 items, IoU ≥ 0.5)")

# 3. Latency ------------------------------------------------------------------------------------------------------
parity = json.loads((REPO / "ml/models/exp002/evidence/onnx_parity.json").read_text())
adv = json.loads((REPO / "test-results/advisor_eval.json").read_text())["summary"]["latency_ms"]
items = [("Classifier only (ONNX, CPU)", parity["onnxruntime_cpu_latency_ms_avg"]),
         ("Meal Advisor reply, rules (p50)", adv["p50"]), ("Meal Advisor reply, rules (p95)", adv["p95"]),
         ("Full multi-food analysis (p50)", mf["latency_ms"]["p50"]), ("Full multi-food analysis (p95)", mf["latency_ms"]["p95"])]
slm = HERE / "slm_eval.json"
if slm.exists():
    s = json.loads(slm.read_text())
    items += [("SLM explanation (p50)", s["explain"]["latency_ms"]["p50"]), ("SLM advisor rewording (p50)", s["rewrite"]["latency_ms"]["p50"])]
fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(items) + 0.8))
y = list(range(len(items)))[::-1]
ax.barh(y, [v for _, v in items], height=0.5, color=TEAL)
ax.set_xscale("log")
for yy, (_, v) in zip(y, items):
    ax.text(v * 1.08, yy, f"{v:,.0f} ms" if v >= 20 else f"{v:.1f} ms", va="center", fontsize=9.5, color=INK)
ax.set_yticks(y, [n for n, _ in items]); ax.tick_params(left=False)
ax.set_xlim(5, max(v for _, v in items) * 4)
ax.xaxis.grid(True, color=GRID, lw=0.8, which="major"); ax.set_axisbelow(True); ax.set_xlabel("milliseconds (log scale)")
ax.set_title("Response time on a 4-vCPU CPU server")
save(fig, "03_latency.png", "onnx_parity.json, advisor_eval.json, multifood_metrics.json" + (", slm_eval.json (Buddy)" if slm.exists() else ""))

# 4. Coverage: classes → nutrition records, foods → GI -------------------------------------------------------------
cov = json.loads((REPO / "ml/models/exp002/evidence/nutrition_coverage.json").read_text())
gi = DATA["gi"]
fig, axes = plt.subplots(2, 1, figsize=(6.4, 2.6), gridspec_kw={"hspace": 1.1})
for ax, title, parts, total in [
    (axes[0], f"320 model classes → nutrition records", [("exact", cov["by_match"]["exact"], BLUE), ("nearest food (proxy)", cov["by_match"]["proxy"], AQUA), ("none: user chooses", cov["by_match"]["none"], GREY)], 320),
    (axes[1], f"{gi['published'] + gi['borrowed'] + gi['none']} foods → glycaemic index", [("published GI", gi["published"], BLUE), ("borrowed from staple (rules)", gi["borrowed"], AQUA), ("no GI: not estimated", gi["none"], GREY)], gi["published"] + gi["borrowed"] + gi["none"])]:
    left = 0
    for name, n, col in parts:
        ax.barh(0, n, left=left, height=0.55, color=col, edgecolor="white", linewidth=2)
        ax.text(left + n / 2, 0, f"{n}", ha="center", va="center", color="white" if col != GREY else INK, fontsize=9.5, fontweight="bold")
        left += n
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=f"{nm} ({n})") for nm, n, c in parts], ncol=3, frameon=False, fontsize=8,
              loc="upper left", bbox_to_anchor=(0, 0.05))
    ax.set_xlim(0, total); ax.set_ylim(-1.2, 0.5); ax.axis("off"); ax.set_title(title, fontsize=10.5)
save(fig, "04_coverage.png", "nutrition_coverage.json; foods.json with services/nutrition.gi_info (v0.13.8)")

# 5. Which staple a borrowed GI comes from ---------------------------------------------------------------------------
by = DATA["gi"]["by_staple"]
fig, ax = plt.subplots(figsize=(6.4, 2.6))
hbar(ax, [f"{n.split(',')[0].split(' (')[0]} (GI {g})" for n, g in
          [(n, {"Udon": 55, "White rice": 73, "White bread": 75, "Soft drink": 63, "Pasta / spaghetti": 49, "French fries": 63,
                "Muesli": 57, "Steamed bun": 88, "Doughnut": 76, "Pancakes": 66}.get(n.split(',')[0].split(' (')[0], "")) for n, _ in by]],
     [c for _, c in by], fmt="{:.0f}", xmax=max(c for _, c in by))
ax.set_title(f"{DATA['gi']['borrowed']} foods borrow the GI of their main carbohydrate")
save(fig, "05_gi_borrowing.png", "services/nutrition.py GI_RULES applied to datasets/nutrition/foods.json")

# 6. Text matching: what the rules get right before the language model is asked -------------------------------------
st = HERE / "baselines.json"
rowsm = json.loads(st.read_text())["match"]["rows"] if st.exists() else []
lk = {"Correct": sum(r["lookup"] == r["want"] for r in rowsm), "Wrong food": sum(r["lookup"] is not None and r["lookup"] != r["want"] for r in rowsm),
      "No match": sum(r["lookup"] is None and r["want"] is not None for r in rowsm)}
groups = [("Fuzzy lookup (rules)", lk)]
if slm.exists():
    sr = s["match"]["rows"]
    groups.append(("Language model", {"Correct": sum(r["correct"] for r in sr), "Wrong food": sum(r["slm"] is not None and r["slm"] != r["want"] for r in sr),
                                      "No match": sum(r["slm"] is None and r["want"] is not None for r in sr)}))
fig, ax = plt.subplots(figsize=(6.4, 0.6 * len(groups) + 1.2))
left = [0] * len(groups)
for name, col in [("Correct", BLUE), ("Wrong food", ORANGE), ("No match", GREY)]:
    vals = [g[1][name] for g in groups]
    bars = ax.barh(range(len(groups))[::-1], vals, left=left, height=0.5, color=col, label=name, edgecolor="white", linewidth=2)
    for b, v, l0 in zip(bars, vals, left):
        if v:
            ax.text(l0 + v / 2, b.get_y() + b.get_height() / 2, str(v), ha="center", va="center", fontsize=9, color="white" if col != GREY else INK)
    left = [a + b for a, b in zip(left, vals)]
ax.set_yticks(range(len(groups))[::-1], [g[0] for g in groups]); ax.tick_params(left=False)
ax.set_xlim(0, len(rowsm)); ax.set_xlabel(f"{len(rowsm)} food names the table does not list verbatim (10 in the table, 5 absent)")
ax.legend(ncol=3, frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, 1.0))
ax.set_title("Matching unknown food names to the nutrition table", pad=22)
save(fig, "06_text_matching.png", "app/tools/slm_eval.py fixed set" + (" (run on Buddy)" if slm.exists() else "; rules baseline measured here"))

# 7. The glucose model on a real meal --------------------------------------------------------------------------------
t = DATA["time"]
fig, ax = plt.subplots(figsize=(6.4, 3.0))
ax.plot(t, DATA["desk"], color=BLUE, lw=2, label=f"Chicken rice + teh tarik, desk afternoon (GL {DATA['gl_full']})")
ax.plot(t, DATA["walk"], color=AQUA, lw=2, label=f"Same meal, 15-min brisk walk at +15 min (peak {DATA['walk_stats']['peak_change_pct']}%)")
ax.plot(t, DATA["smaller"], color=ORANGE, lw=2, label=f"Two-thirds of the rice, desk afternoon (GL {DATA['gl_small']})")
ax.set_xlabel("minutes after the meal"); ax.set_ylabel("relative meal glucose (full meal peak = 100)")
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); ax.set_xlim(0, 300); ax.set_ylim(0, 110)
ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.2))
ax.set_title("Mass-balance glucose estimate, type 2 profile, 78 kg")
save(fig, "07_glucose_curves.png", "services/forecast.py (dG/dt = Ra − k·G − U_ex) run on foods.json records; an estimate, not a measurement")

# 8. Automated tests over the project ----------------------------------------------------------------------------------
hist = [("0.3", 15), ("0.4", 18), ("0.6", 20), ("0.8", 31), ("0.9", 41), ("0.13.0", 56), ("0.13.2", 59), ("0.13.5", 60), ("0.13.7", 62), ("0.13.8", 64)]
fig, ax = plt.subplots(figsize=(6.4, 2.4))
ax.step(range(len(hist)), [n for _, n in hist], where="post", color=TEAL, lw=2)
ax.plot(range(len(hist)), [n for _, n in hist], "o", color=TEAL, ms=5, mec="white", mew=1.5)
for i, (_, n) in enumerate(hist):
    if i in (0, 3, 5, len(hist) - 1):
        ax.text(i, n + 3, str(n), ha="center", fontsize=9, color=INK)
ax.set_xticks(range(len(hist)), ["v" + v for v, _ in hist], fontsize=8)
ax.set_ylim(0, 75); ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); ax.set_ylabel("pytest cases, all passing")
ax.set_title("Automated tests against a real PostgreSQL database")
save(fig, "08_tests_growth.png", "docs/TEST_REPORT.md")


# 9-10. Diagrams ---------------------------------------------------------------------------------------------------------
def box(ax, x, y, w, h, title, body, edge=TEAL, fill="#f1f7f5", dashed=False, tsize=9.5, bsize=7.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06", fc=fill, ec=edge, lw=1.4,
                                ls="--" if dashed else "-"))
    ax.text(x + w / 2, y + h - 0.14, title, ha="center", va="top", fontsize=tsize, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.42, body, ha="center", va="top", fontsize=bsize, color=INK2, linespacing=1.4)


def arrow(ax, x1, y1, x2, y2, label=""):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.2))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.08, label, ha="center", va="bottom", fontsize=7.5, color=INK2)


fig, ax = plt.subplots(figsize=(8.4, 3.8))
ax.set_xlim(0, 12); ax.set_ylim(0, 5); ax.axis("off")
box(ax, 0.1, 2.9, 2.0, 1.6, "Browser", "phone or desktop\nReact + TypeScript")
box(ax, 2.8, 2.9, 2.2, 1.6, "frontend", "nginx 1.27\nstatic app, /api proxy\nrate limits, headers")
box(ax, 5.7, 2.5, 3.2, 2.3, "backend", "FastAPI · Python 3.12\nONNX Runtime (CPU)\nEfficientNet-B0 · YOLO11n-seg\nportion · nutrition · insights\nforecast · advisor · governance")
box(ax, 9.6, 2.9, 2.3, 1.6, "db", "PostgreSQL 16\nAlembic migrations\nvolume: pgdata")
box(ax, 5.7, 0.2, 3.2, 1.5, "ollama (optional)", "Qwen 2.5 1.5B, local\nwording only; validated\nbefore it is shown", dashed=True)
box(ax, 9.6, 0.2, 2.3, 1.5, "volume: uploads", "meal photos\nmodel packages", dashed=True)
arrow(ax, 2.1, 3.7, 2.8, 3.7, "HTTPS")
arrow(ax, 5.0, 3.7, 5.7, 3.7, "/api/v1")
arrow(ax, 8.9, 3.7, 9.6, 3.7, "SQL")
arrow(ax, 7.3, 2.5, 7.3, 1.7, "HTTP")
arrow(ax, 8.9, 2.7, 9.6, 1.5, "")
ax.text(0.1, 0.4, "Docker Compose, one CPU server\nno paid cloud AI service", fontsize=8.5, color=INK2, va="bottom")
ax.set_title("Deployment architecture")
save(fig, "09_architecture.png", "docker-compose.yml, docs/ARCHITECTURE.md")

stages = [("1 Meal capture", "camera or upload"), ("2 Pre-processing", "EXIF, ≤1024 px"), ("3 Detection", "YOLO11n-seg"), ("4 Classification", "EfficientNet-B0\ntop-3"),
          ("5 Portion", "prior or area\n± band"), ("6 Nutrition map", "exact · proxy\n· none"), ("7 Aggregation", "meal totals, GL\n(GI ≥70% carbs)"),
          ("8 Context (AI)", "user context +\nlocal SLM or rules"), ("9 Recommend", "rules, cited\nguidance"), ("10 Output", "user confirms\n& corrects")]
fig, ax = plt.subplots(figsize=(7.2, 2.6))
ax.set_xlim(0, 10); ax.set_ylim(0, 3); ax.axis("off")
for i, (t1, t2) in enumerate(stages):
    row, col = divmod(i, 5)
    x, y = 0.1 + col * 2.0, 1.65 - row * 1.5
    tag = AQUA if i in (2, 3) else ORANGE if i in (4, 5, 6) else BLUE if i in (7, 8) else TEAL
    box(ax, x, y, 1.7, 1.15, t1, t2, edge=tag, tsize=7.6, bsize=7.5)
    if col < 4:
        arrow(ax, x + 1.7, y + 0.57, x + 2.0, y + 0.57)
ax.annotate("", (0.95, 1.3), (9.05, 1.65), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0, connectionstyle="arc3,rad=0.0", ls=":"))
for i, (lab, col) in enumerate([("model prediction", AQUA), ("estimate", ORANGE), ("guidance", BLUE), ("user / system", TEAL)]):
    ax.add_patch(FancyBboxPatch((0.1 + i * 2.2, -0.2), 0.25, 0.18, boxstyle="round,pad=0.01", fc="white", ec=col, lw=1.6))
    ax.text(0.45 + i * 2.2, -0.11, lab, va="center", fontsize=8, color=INK2)
ax.set_ylim(-0.3, 3)
ax.set_title("The ten-stage pipeline from the proposal (each stage shown to the user)")
save(fig, "10_pipeline.png", "backend/app/services/analysis.py, docs/ARCHITECTURE.md")
