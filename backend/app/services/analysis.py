"""Orchestrates stages 2–6 and recomputation after user corrections."""
import re
import time

from sqlalchemy.orm import Session

from app.models import InferenceLog, Meal, MealFood
from app.services import insights, nutrition, portion, slm, vision


def food_dict(f: MealFood) -> dict:
    return {"label": f.label, "grams": f.grams, "nutrients": f.nutrients or {}, "nutrition_key": f.nutrition_key}


def apply_mapping(f: MealFood, key: str | None, quality: str):
    f.nutrition_key, f.mapping_quality = key, quality if key else "none"
    if key:
        f.nutrients = nutrition.compute(key, f.grams)
        f.nutrition_source = nutrition.source_info(key)
    else:
        f.nutrients, f.nutrition_source = nutrition.empty_nutrients(), None


def recompute(meal: Meal, profile, use_slm: bool = True):
    active = [food_dict(f) for f in meal.foods if not f.removed]
    meal.totals, meal.insights = insights.build(active, profile, use_slm=use_slm)


def _parse_description(text: str) -> tuple[list[tuple[str, float]], str]:
    res = slm.parse_description(text)
    if res and res.foods:
        return [(m.name, m.servings) for m in res.foods], f"slm:{slm.status()['selected']}"
    out = []
    for chunk in re.split(r",|;|\+|&|\band\b|\bwith\b|\bplus\b", text.lower()):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:x\s*)?(.*)$", chunk)
        servings, name = (float(m.group(1)), m.group(2)) if m else (1.0, chunk)
        out.append((name.strip(), servings))
    return out, "rule_based_parser"


def _provisional(label: str) -> str | None:
    res = slm.suggest_match(label, [nutrition.summary(f) for f in nutrition.all_foods()])
    return res.key if res and nutrition.get(res.key) else None


def run(db: Session, meal: Meal, profile) -> list[dict]:
    stages = [s for s in meal.stages if s["key"] == "preprocess"]
    t0 = time.perf_counter()
    results = []
    for im in meal.images:
        r = vision.analyze(im["path"], im["view"])
        results.append(r)
        if r["ok"]:
            for task, model in (("classifier", vision.MODELS["classifier"]), ("detector", vision.MODELS["detector"])):
                db.add(InferenceLog(meal_id=meal.id, model_name=model["name"], model_version=model["version"],
                                    task=model["task"], latency_ms=r["latency_ms"][task],
                                    extra={"view": im["view"], "food_hits": sum(1 for i in r["items"] if i["model"] == task)}))
    preds = vision.merge(results)
    vstat = vision.status()
    detail = (f"{len(preds)} food item(s) recognised" if preds else
              "No food from the models' vocabulary was recognised. Add foods manually or via description.")
    if not vstat["available"]:
        detail = f"Vision models unavailable ({vstat['error']}). Manual entry enabled."
    stages.append({"key": "recognize", "name": "Food detection & classification",
                   "status": "done" if preds else "unsupported", "detail": detail,
                   "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                   "per_view": [{"view": r["view"], "top_labels": r.get("top_labels", []),
                                 "latency_ms": r.get("latency_ms"), "containers": r.get("containers", [])}
                                for r in results]})

    # Stage 3 + 4: create food items, estimate portions, map nutrition
    t1 = time.perf_counter()
    for f in list(meal.foods):  # re-analysis replaces prior auto items
        if f.origin in ("model", "description") and not f.user_corrected:
            meal.foods.remove(f)
    containers = {r["view"]: r.get("containers", []) for r in results}
    seen = {f.nutrition_key for f in meal.foods if not f.removed}
    n_views = len(meal.images)
    for p in preds:
        key = p["nutrition_key"]
        if key and key in seen:
            continue
        label = (nutrition.get(key) or {}).get("name") or p["model_label"]
        quality = "exact" if key else "none"
        if not key and (pk := _provisional(p["model_label"])):
            key, quality = pk, "provisional"
        ref = nutrition.get(key)
        if ref:
            grams, pinfo = portion.estimate(ref, bbox=p["bbox"], containers=containers.get(p["view"]),
                                            reference_object=meal.reference_object, n_views=n_views,
                                            note=meal.serving_note)
        else:
            grams, pinfo = 0, {"method": "unknown", "uncertainty": "unknown", "range_g": None,
                               "notes": ["No nutrition match; enter food and portion manually."]}
        pred = {k: p[k] for k in ("model_label", "nutrition_key", "score", "bbox", "model", "view", "views")}
        pred.update(model_name=vision.MODELS[p["model"]]["name"], score_band=vision.score_band(p["score"]),
                    score_type="raw model score (uncalibrated)", evidence=p["evidence"])
        f = MealFood(origin="model", label=label, grams=grams, portion=pinfo, original_prediction=pred)
        apply_mapping(f, key, quality)
        meal.foods.append(f)
        seen.add(key)

    desc_source = None
    if meal.description:
        mentions, desc_source = _parse_description(meal.description)
        for name, servings in mentions:
            key, quality = nutrition.lookup(name)
            if not key and (pk := _provisional(name)):
                key, quality = pk, "provisional"
            if key in seen and key:
                continue
            ref = nutrition.get(key)
            if ref:
                grams, pinfo = portion.estimate(ref, n_views=n_views, servings=servings, note=meal.serving_note)
            else:
                grams, pinfo = 0, {"method": "unknown", "uncertainty": "unknown", "range_g": None,
                                   "notes": ["No nutrition match; choose a food from the table."]}
            f = MealFood(origin="description", label=ref["name"] if ref else name, grams=grams, portion=pinfo,
                         original_prediction={"description_text": name, "parser": desc_source, "servings": servings})
            apply_mapping(f, key, quality)
            meal.foods.append(f)
            seen.add(key)
    active = [f for f in meal.foods if not f.removed]
    stages.append({"key": "portion", "name": "Portion estimation", "status": "done" if active else "skipped",
                   "detail": "Typical-serving priors with uncertainty bands; area scaling only when a reference "
                             "container is detected. Volume is not measured.",
                   "latency_ms": round((time.perf_counter() - t1) * 1000, 1)})
    mapped = sum(1 for f in active if f.nutrition_key)
    stages.append({"key": "nutrition", "name": "Nutrition mapping",
                   "status": "done" if active else "skipped",
                   "detail": f"{mapped}/{len(active)} item(s) matched to reference table {nutrition.version()}"
                             + (f"; description parsed by {desc_source}" if desc_source else ""),
                   "latency_ms": 0.0})
    t2 = time.perf_counter()
    recompute(meal, profile)
    stages.append({"key": "aggregate", "name": "Meal aggregation", "status": "done",
                   "detail": f"{meal.totals['calories_kcal'] or 0} kcal across {meal.totals['item_count']} item(s)",
                   "latency_ms": 0.0})
    stages.append({"key": "insights", "name": "Review & insights", "status": "done",
                   "detail": "Explanation by " + (meal.insights["explanation"]["source"]
                                                  if meal.insights["explanation"]["text"] else
                                                  "rule-based engine (SLM offline)"),
                   "latency_ms": round((time.perf_counter() - t2) * 1000, 1)})
    meal.model_info = {"vision": {k: {kk: v[kk] for kk in ("name", "version", "trained_on")}
                                  for k, v in vision.MODELS.items()} if vstat["available"] else None,
                       "slm": slm.status()["selected"], "nutrition_table": nutrition.version()}
    meal.stages = stages
    meal.status = "analyzed"
    return stages
