"""Inference pipeline orchestrator, aligned with the solution-architecture diagram:

 1 Meal capture            (capture endpoint)
 2 Image pre-processing    (capture endpoint)
 3 Food instance detection (YOLO11n-seg masks; supporting)
 4 Food classification     (EXP-002 EfficientNet-B0, 320 classes, top-3 candidates)
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
from app.services import gate, insights, memory, nutrition, portion, slm, tuning, vision

UNKNOWN_PORTION = {"method": "unknown", "uncertainty": "unknown", "range_g": None,
                   "notes": ["No nutrition match; choose a food from the table and enter the portion."]}


def vision_auto_accept() -> float:
    if (v := tuning.get("vision.auto_accept")) is not None:   # an admin's override
        return float(v)
    card = (vision.models().get("classifier") or {})
    return 0.5 if not card else float(vision._state["cls"]["card"].get("auto_accept_min_score", 0.5))


def food_dict(f: MealFood) -> dict:
    return {"label": f.label, "grams": f.grams, "nutrients": f.nutrients or {}, "nutrition_key": f.nutrition_key}


def apply_mapping(f: MealFood, key: str | None, quality: str):
    f.nutrition_key, f.mapping_quality = key, quality if key else "none"
    if key:
        f.nutrients = nutrition.compute(key, f.grams)
        f.nutrition_source = {**nutrition.source_info(key), "match": quality}
    else:
        f.nutrients, f.nutrition_source = nutrition.empty_nutrients(), None


def recompute(meal: Meal, profile, use_slm: bool = True):
    for f in meal.foods:   # keep the GI shown with each food in step with the table and its borrowing rules
        if f.nutrition_source and f.nutrition_key and nutrition.get(f.nutrition_key):
            gi = nutrition.gi_info(f.nutrition_key) or {}
            f.nutrition_source = {**f.nutrition_source, "glycemic_index": gi.get("value"), "gi_source": gi.get("source"),
                                  "gi_borrowed_from": gi.get("borrowed_from")}
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


STAGE_ORDER = ["capture", "preprocess", "detect", "classify", "portion", "nutrition", "aggregate", "contextualise",
               "recommend", "output"]
PROGRESS: dict[int, dict] = {}   # meal_id -> live stage list while an analysis runs (single-process backend)


def progress(meal_id: int) -> dict | None:
    p = PROGRESS.get(meal_id)
    if not p:
        return None
    done = len(p["stages"])
    return {"stages": p["stages"], "done": done, "total": len(STAGE_ORDER),
            "current": STAGE_ORDER[done] if done < len(STAGE_ORDER) else None,
            "elapsed_ms": round((time.perf_counter() - p["t0"]) * 1000)}


class _Stages:
    def __init__(self, existing: list[dict], meal_id: int | None = None):
        self.items = [s for s in existing if s["key"] in ("capture", "preprocess")]
        self.t = time.perf_counter()
        if meal_id is not None:
            PROGRESS[meal_id] = {"stages": self.items, "t0": self.t}   # same list object: appends are visible live

    def add(self, key, name, status, detail, **extra):
        now = time.perf_counter()
        self.items.append({"key": key, "name": name, "status": status, "detail": detail,
                           "latency_ms": round((now - self.t) * 1000, 1), **extra})
        self.t = now


def run(db: Session, meal: Meal, profile) -> list[dict]:
    try:
        return _run(db, meal, profile)
    finally:
        PROGRESS.pop(meal.id, None)


def _run(db: Session, meal: Meal, profile) -> list[dict]:
    st = _Stages(meal.stages, meal.id)
    vstat = vision.status()
    mods = vstat["models"]

    # 3 + 4: detection and classification (run together per image; latencies reported separately)
    results = [vision.analyze(im["path"], im["view"], im.get("original_path")) for im in meal.images]
    meal.images = [{**im, "overlay_path": r.get("overlay_path")} for im, r in zip(meal.images, results)]
    for im, r in zip(meal.images, results):
        if not r["ok"]:
            continue
        for role in ("detector", "classifier"):
            m = mods.get(role)
            if m:
                db.add(InferenceLog(meal_id=meal.id, model_name=m["name"], model_version=m["version"], task=m["task"],
                                    latency_ms=r["latency_ms"][role], extra={"view": im["view"], "device": r.get("device")}))
    preds = vision.merge(results)
    det_ms = sum(r.get("latency_ms", {}).get("detector", 0) for r in results)
    cls_ms = sum(r.get("latency_ms", {}).get("classifier", 0) for r in results)
    n_inst = sum(1 for r in results for i in r.get("instances", []) if i["kind"] in ("food", "container"))
    det_name = mods.get("detector", {}).get("name", "detector unavailable")
    cls_name = mods.get("classifier", {}).get("name", "unavailable")
    device = next((r.get("device") for r in results if r.get("device")), None)
    if not meal.images:
        st.add("detect", "Food instance detection", "skipped", "No photo provided.")
        st.add("classify", "Food classification", "skipped", "No photo provided.")
    elif not vstat["available"]:
        st.add("detect", "Food instance detection", "unsupported", f"Vision models unavailable ({vstat['error']}).")
        st.add("classify", "Food classification", "unsupported", "Manual entry enabled.")
    else:
        st.items.append({"key": "detect", "name": "Food instance detection", "status": "done",
                         "detail": f"colour/texture segmentation + {det_name}: "
                                   f"{sum(r.get('regions', 0) for r in results)} candidate food region(s)", "latency_ms": det_ms,
                         "per_view": [{"view": r["view"], "instances": r.get("instances", [])} for r in results]})
        n_food = sum(1 for p in preds if p["kind"] == "food")
        n_unknown = sum(1 for p in preds if p["kind"] == "unknown")
        n_sugg = sum(1 for p in preds if p["kind"] == "suggestion")
        weak = n_food == 0
        st.items.append({"key": "classify", "name": "Food classification", "status": "uncertain" if weak else "done",
                         "detail": f"{cls_name} on {device or 'cpu'}: {sum(r.get('regions', 0) for r in results)} region(s) "
                                   f"classified → {n_food} food(s), {n_unknown} unidentified, {n_sugg} possible extra item(s); "
                                   "top-3 per item" + ("; low confidence — choose a candidate or add the food manually" if weak else ""),
                         "latency_ms": cls_ms,
                         "per_view": [{"view": r["view"], "top_labels": r.get("top_labels", [])} for r in results]})
        st.t = time.perf_counter()

    # 5: portion estimation (+ create items)
    for f in list(meal.foods):  # re-analysis replaces previous automatic items
        if f.origin in ("model", "description") and not f.user_corrected:
            meal.foods.remove(f)
    containers = {r["view"]: r.get("containers", []) for r in results}
    seen = {f.nutrition_key for f in meal.foods if not f.removed and f.nutrition_key}
    n_views = len(meal.images)
    n_unknown = 0
    recall = memory.matcher(db, meal.user_id)
    auto_accept = vision_auto_accept()
    n_memory = 0
    for p in preds:
        mem = recall(p.get("fingerprint")) if p["kind"] == "unknown" or (p["kind"] == "food" and p["score"] < auto_accept) else None
        if mem:   # the user named a region like this before: use their label (still editable)
            p = {**p, "kind": "food", "model_label": mem["label"], "nutrition_key": mem["nutrition_key"], "match": "exact",
                 "memory": {**mem, "model_label": p["model_label"], "model_score": p["score"]}}
            n_memory += 1
        key, quality = p["nutrition_key"], p["match"]
        ref = nutrition.get(key)
        if ref:
            grams, pinfo = portion.estimate(ref, bbox=p["bbox"], area_frac=p.get("area_frac"),
                                            containers=containers.get(p["view"]), reference_object=meal.reference_object,
                                            n_views=n_views, note=meal.serving_note, instances=p["instances"],
                                            has_mask=p.get("has_mask", False))
        else:
            grams, pinfo = 0, dict(UNKNOWN_PORTION)
        pred = {k: p.get(k) for k in ("region_id", "kind", "model_label", "class_id", "nutrition_key", "match", "score",
                                       "candidates", "bbox", "view", "views", "instance", "area_frac", "has_mask",
                                       "instances", "detector_label", "detector_score", "fingerprint", "memory")}
        pred.update(model_name=cls_name, model_version=mods.get("classifier", {}).get("version"), device=device,
                    score_band=vision.score_band(p["score"]), score_type="raw softmax score (uncalibrated)",
                    needs_review=p["score"] < auto_accept and not mem)
        if p["kind"] == "food":
            f = MealFood(origin="memory" if mem else "model", label=p["model_label"], taxonomy_class=None if mem else p["model_label"],
                         grams=grams, portion=pinfo, original_prediction=pred)
        else:  # unidentified region: shown for the user to name (suggestions start hidden, not counted)
            n_unknown += 1
            f = MealFood(origin="model", label=f"Unidentified food {n_unknown}", taxonomy_class=None, grams=0,
                         portion=dict(UNKNOWN_PORTION), original_prediction=pred, removed=p["kind"] == "suggestion")
        apply_mapping(f, key, quality)
        meal.foods.append(f)
        if key:
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
    if n_memory:
        st.items[-1]["detail"] += f"; {n_memory} item(s) recognised from your earlier labels"
    gate.record_shadow(db, preds)   # a candidate in shadow mode: count agreement, never shown to the user
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
    # 8: AI contextualisation (deferred: the local SLM writes it after results are shown, so it never delays analysis)
    ins["explanation"] = insights.pending_explanation(foods)
    st.add("contextualise", "AI contextualisation", "deferred" if ins["explanation"]["source"] == "pending" else "fallback",
           f"Local SLM {ins['explanation'].get('model')} writes the explanation after results are shown (does not delay analysis)"
           if ins["explanation"]["source"] == "pending" else "Local SLM offline — composition-grounded rule engine used.")
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
