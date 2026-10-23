"""Inference pipeline orchestrator, aligned with the solution-architecture diagram:

 1 Meal capture            (capture endpoint)
 2 Image pre-processing    (capture endpoint)
 3 Food instance detection (YOLO11n-seg masks / EfficientDet boxes)
 4 Food classification     (per-instance crops: fine-tuned classifier or ImageNet fallback)
 5 Portion estimation
 6 Nutrition mapping
 7 Meal aggregation
 8 AI contextualisation    (local SLM, grounded in computed numbers + user goals)
 9 Recommendations
10 Application output      (persisted meal returned to the UI for review/correction)
"""
import re
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import InferenceLog, Meal, MealFood
from app.services import insights, nutrition, portion, slm, vision

UNKNOWN_PORTION = {"method": "unknown", "uncertainty": "unknown", "range_g": None,
                   "notes": ["No nutrition match; choose a food from the table and enter the portion."]}


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


class _Stages:
    def __init__(self, existing: list[dict]):
        self.items = [s for s in existing if s["key"] in ("capture", "preprocess")]
        self.t = time.perf_counter()

    def add(self, key, name, status, detail, **extra):
        now = time.perf_counter()
        self.items.append({"key": key, "name": name, "status": status, "detail": detail,
                           "latency_ms": round((now - self.t) * 1000, 1), **extra})
        self.t = now


def run(db: Session, meal: Meal, profile) -> list[dict]:
    st = _Stages(meal.stages)
    vstat = vision.status()
    mods = vstat["models"]

    # 3 + 4: detection and classification (run together per image; latencies reported separately)
    results = [vision.analyze(im["path"], im["view"]) for im in meal.images]
    meal.images = [{**im, "overlay_path": r.get("overlay_path")} for im, r in zip(meal.images, results)]
    for im, r in zip(meal.images, results):
        if not r["ok"]:
            continue
        for role, task in (("detector", "detector"), ("classifier", "classifier")):
            m = mods.get(role) or mods.get("classifier_imagenet")
            db.add(InferenceLog(meal_id=meal.id, model_name=m["name"], model_version=m["version"], task=m["task"],
                                latency_ms=r["latency_ms"][task], extra={"view": im["view"]}))
    preds = vision.merge(results)
    det_ms = sum(r.get("latency_ms", {}).get("detector", 0) for r in results)
    cls_ms = sum(r.get("latency_ms", {}).get("classifier", 0) for r in results)
    n_inst = sum(1 for r in results for i in r.get("instances", []) if i["kind"] in ("food", "container"))
    det_name = mods.get("detector", {}).get("name", "unavailable")
    cls_name = (mods.get("classifier") or mods.get("classifier_imagenet") or {}).get("name", "unavailable")
    if not meal.images:
        st.add("detect", "Food instance detection", "skipped", "No photo provided.")
        st.add("classify", "Food classification", "skipped", "No photo provided.")
    elif not vstat["available"]:
        st.add("detect", "Food instance detection", "unsupported", f"Vision models unavailable ({vstat['error']}).")
        st.add("classify", "Food classification", "unsupported", "Manual entry enabled.")
    else:
        st.items.append({"key": "detect", "name": "Food instance detection", "status": "done",
                         "detail": f"{det_name}: {n_inst} food/dish instance(s) segmented"
                                   + ("" if n_inst else " — whole image used as one region"),
                         "latency_ms": det_ms,
                         "per_view": [{"view": r["view"], "instances": r.get("instances", [])} for r in results]})
        st.items.append({"key": "classify", "name": "Food classification",
                         "status": "done" if preds else "unsupported",
                         "detail": (f"{cls_name}: {len(preds)} food(s) identified" if preds else
                                    f"{cls_name}: no food in the model vocabulary recognised. Add foods manually "
                                    "or via the description."),
                         "latency_ms": cls_ms,
                         "per_view": [{"view": r["view"], "top_labels": r.get("top_labels", [])} for r in results]})
        st.t = time.perf_counter()

    # 5: portion estimation (+ create items)
    for f in list(meal.foods):  # re-analysis replaces previous automatic items
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
            grams, pinfo = portion.estimate(ref, bbox=p["bbox"], area_frac=p.get("area_frac"),
                                            containers=containers.get(p["view"]), reference_object=meal.reference_object,
                                            n_views=n_views, note=meal.serving_note, instances=p["instances"],
                                            has_mask=p.get("has_mask", False))
        else:
            grams, pinfo = 0, dict(UNKNOWN_PORTION)
        pred = {k: p.get(k) for k in ("model_label", "nutrition_key", "score", "bbox", "model", "model_name", "view",
                                       "views", "instance", "detector_label", "detector_score", "classifier_top",
                                       "area_frac", "has_mask", "instances", "deferred_from")}
        pred.update(score_band=vision.score_band(p["score"]), score_type="raw model score (uncalibrated)")
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
            if key and key in seen:
                continue
            ref = nutrition.get(key)
            if ref:
                grams, pinfo = portion.estimate(ref, n_views=n_views, servings=servings, note=meal.serving_note)
            else:
                grams, pinfo = 0, dict(UNKNOWN_PORTION)
            f = MealFood(origin="description", label=ref["name"] if ref else name, grams=grams, portion=pinfo,
                         original_prediction={"description_text": name, "parser": desc_source, "servings": servings})
            apply_mapping(f, key, quality)
            meal.foods.append(f)
            seen.add(key)
    active = [f for f in meal.foods if not f.removed]
    methods = sorted({f.portion.get("method") for f in active})
    st.add("portion", "Portion estimation", "done" if active else "skipped",
           f"Methods: {', '.join(methods) or '—'}. Typical-serving priors with uncertainty bands; mask/box area scaling "
           "only when a reference container is detected. Volume is not measured.")

    # 6: nutrition mapping (performed per item above, reported here)
    mapped = sum(1 for f in active if f.nutrition_key)
    st.add("nutrition", "Nutrition mapping", "done" if active else "skipped",
           f"{mapped}/{len(active)} item(s) matched to reference table {nutrition.version()}"
           + (f"; description parsed by {desc_source}" if desc_source else ""))

    # 7 + 9: aggregation, assessments, recommendations (deterministic)
    foods = [food_dict(f) for f in active]
    meal.totals, ins = insights.core(foods, profile)
    st.add("aggregate", "Meal aggregation", "done",
           f"{meal.totals['calories_kcal'] or 0} kcal · {meal.totals['carbs_g'] or 0} g carbs across "
           f"{meal.totals['item_count']} item(s)")
    # 8: AI contextualisation
    ins["explanation"] = insights.contextualise(foods, meal.totals, ins, profile)
    st.add("contextualise", "AI contextualisation", "done" if ins["explanation"]["text"] else "fallback",
           f"Explanation by {ins['explanation']['source'].replace('slm:', 'local SLM ')}" if ins["explanation"]["text"]
           else "Local SLM offline — composition-grounded rule engine used.")
    st.items.append({"key": "recommend", "name": "Recommendations", "status": "done",
                     "detail": f"{len(ins['recommendations'])} recommendation(s), glucose impact {ins['glucose']['level']}",
                     "latency_ms": 0.0})
    ins["generated_at"] = datetime.now(timezone.utc).isoformat()
    meal.insights = ins

    # 10: application output
    meal.model_info = {"vision": {k: {kk: v[kk] for kk in ("name", "version", "trained_on", "task")}
                                  for k, v in mods.items()} if vstat["available"] else None,
                       "slm": slm.status()["selected"], "nutrition_table": nutrition.version()}
    st.add("output", "Application output", "done", "Results ready for your review and correction.")
    meal.stages = st.items
    meal.status = "analyzed"
    return st.items
