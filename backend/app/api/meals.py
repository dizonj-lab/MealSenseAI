import shutil
import time
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import owned_meal
from app.core.config import settings
from app.core.db import get_db
from app.core.security import active_user
from app.models import Correction, Meal, MealFood, User
from app.schemas import AnalyzeIn, ConfirmIn, FoodAddIn, FoodUpdateIn, ForecastIn, HistoryOut, MealOut, MergeIn, RegionIn, SimulateIn
from app.services import analysis, custom_foods, forecast, glucose_scale, imaging, insights, memory, nutrition, portion, tuning, vision

router = APIRouter(prefix="/meals", tags=["meals"])


def _snapshot(f: MealFood) -> dict:
    return {"label": f.label, "taxonomy_class": f.taxonomy_class, "nutrition_key": f.nutrition_key, "grams": f.grams,
            "mapping_quality": f.mapping_quality, "nutrients": f.nutrients}


def _model_name(f: MealFood) -> str | None:
    return (f.original_prediction or {}).get("model_name")


@router.post("/capture", response_model=MealOut, status_code=201,
             summary="Upload top and/or side view photos (stage 1: validation & preprocessing)")
async def capture(top: UploadFile | None = File(None), side: UploadFile | None = File(None),
                  description: str | None = Form(None), reference_object: str | None = Form(None),
                  serving_note: str | None = Form(None), meal_type: str | None = Form(None),
                  user: User = Depends(active_user), db: Session = Depends(get_db)):
    uploads = [(v, u) for v, u in (("top", top), ("side", side)) if u is not None and u.filename]
    if not uploads and not (description or "").strip():
        raise HTTPException(422, "Provide at least one photo or a food description")
    if reference_object and reference_object not in portion.REFERENCE_OBJECTS:
        raise HTTPException(422, "Unknown reference object")
    meal = Meal(user_id=user.id, description=(description or "").strip() or None,
                reference_object=reference_object, serving_note=serving_note, meal_type=meal_type)
    db.add(meal)
    db.flush()
    images, read_s, proc_s = [], 0.0, 0.0     # timed separately: upload receipt (capture) vs image processing
    try:
        for view, up in uploads:
            t0 = time.perf_counter()
            raw = await up.read()
            t1 = time.perf_counter()
            read_s += t1 - t0
            if len(raw) > settings.max_upload_mb * 1024 * 1024:
                raise imaging.ImageError(f"{view}: file exceeds {settings.max_upload_mb} MB")
            images.append(imaging.process(raw, settings.data_dir / "uploads" / str(user.id) / str(meal.id), view))
            proc_s += time.perf_counter() - t1
    except imaging.ImageError as e:
        db.rollback()
        raise HTTPException(422, str(e))
    meal.images = images
    warn = [w for im in images for w in im["warnings"]]
    views = ", ".join(im["view"] for im in images) or "none"
    meal.stages = [
        {"key": "capture", "name": "Meal capture", "status": "done", "latency_ms": round(read_s * 1000, 1),
         "detail": f"Photos: {views}" + ("; description provided" if meal.description else "")
                   + (f"; reference: {portion.REFERENCE_OBJECTS[reference_object]}" if reference_object else "")},
        {"key": "preprocess", "name": "Image pre-processing", "status": "done" if images else "skipped",
         "latency_ms": round(proc_s * 1000, 1),
         "detail": (f"{len(images)} image(s) validated and orientation-corrected; originals retained. The classifier "
                    "uses the original with the EXP-002 evaluation preprocessing (resize 256, centre-crop 224, "
                    "ImageNet normalisation); a ≤1024 px copy is kept for display." if images else "No photo provided.")
                   + (" Warnings: " + "; ".join(warn) if warn else "")}]
    db.commit()
    db.refresh(meal)
    return meal


@router.post("/analyze", response_model=MealOut, summary="Run recognition, portion, nutrition and insights")
def analyze(body: AnalyzeIn, user: User = Depends(active_user), db: Session = Depends(get_db)):
    meal = owned_meal(body.meal_id, user, db)
    analysis.run(db, meal, user.profile)
    db.commit()
    db.refresh(meal)
    return meal


@router.get("/history", response_model=HistoryOut)
def history(start: date | None = Query(None), end: date | None = Query(None),
            tz_offset_min: int = Query(0, description="Client UTC offset in minutes (e.g. 480 for SGT)"),
            user: User = Depends(active_user), db: Session = Depends(get_db)):
    tz = timezone(timedelta(minutes=tz_offset_min))
    q = select(Meal).where(Meal.user_id == user.id, Meal.status != "captured").order_by(Meal.eaten_at.desc())
    if start:
        q = q.where(Meal.eaten_at >= datetime.combine(start, datetime.min.time(), tz))
    if end:
        q = q.where(Meal.eaten_at < datetime.combine(end + timedelta(days=1), datetime.min.time(), tz))
    meals = db.scalars(q.limit(500)).all()
    days: dict[str, dict] = {}
    out = []
    for m in meals:
        d = m.eaten_at.astimezone(tz).date().isoformat()
        day = days.setdefault(d, {"date": d, "calories_kcal": 0, "carbs_g": 0, "protein_g": 0, "fat_g": 0, "meals": 0})
        for k in ("calories_kcal", "carbs_g", "protein_g", "fat_g"):
            day[k] = round(day[k] + (m.totals.get(k) or 0), 1)
        day["meals"] += 1
        out.append({"id": m.id, "status": m.status, "meal_type": m.meal_type, "eaten_at": m.eaten_at,
                    "totals": m.totals, "labels": [f.label for f in m.foods if not f.removed],
                    "glucose_level": (m.insights.get("glucose") or {}).get("level"), "has_image": bool(m.images)})
    return {"meals": out, "days": list(days.values())}


@router.get("/{meal_id}", response_model=MealOut)
def get_meal(meal: Meal = Depends(owned_meal)):
    return meal


@router.get("/{meal_id}/images/{view}", response_class=FileResponse)
def get_image(view: str, original: bool = False, meal: Meal = Depends(owned_meal)):
    overlay = view.endswith("_overlay")
    im = next((i for i in meal.images if i["view"] == view.removesuffix("_overlay")), None)
    path = im and (im.get("overlay_path") if overlay else im["original_path"] if original else im["path"])
    if not path or not Path(path).is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(path)


@router.post("/{meal_id}/forecast", summary="Educational post-meal forecast and what-if activity scenarios")
def meal_forecast(body: ForecastIn, meal: Meal = Depends(owned_meal), user: User = Depends(active_user),
                  db: Session = Depends(get_db)):
    foods = [analysis.food_dict(f) for f in meal.foods if not f.removed and f.nutrition_key]
    if not foods:
        raise HTTPException(422, "Add at least one food with a nutrition match first")
    out = forecast.forecast(foods, meal.totals, meal.insights, user.profile,
                            [s.model_dump() for s in body.scenarios], body.horizon_min)
    out["glucose_scale"] = glucose_scale.scale(db, user, meal, out["meal_peak_units"])
    return out


@router.get("/{meal_id}/progress", summary="Live analysis stages while /meals/analyze runs")
def analysis_progress(meal: Meal = Depends(owned_meal)):
    return analysis.progress(meal.id) or {"stages": meal.stages, "done": len(meal.stages), "total": len(analysis.STAGE_ORDER),
                                          "current": None, "elapsed_ms": None}


@router.post("/{meal_id}/explain", response_model=MealOut, summary="Write the local-SLM explanation (after results are shown)")
def explain(meal: Meal = Depends(owned_meal), user: User = Depends(active_user), db: Session = Depends(get_db)):
    if (meal.insights or {}).get("explanation", {}).get("source") != "pending":
        return meal
    foods = [analysis.food_dict(f) for f in meal.foods if not f.removed]
    t0 = time.perf_counter()
    exp = insights.contextualise(foods, meal.totals, meal.insights, user.profile, timeout=90)
    exp["latency_ms"] = round((time.perf_counter() - t0) * 1000)
    meal.insights = {**meal.insights, "explanation": exp}
    db.commit()
    db.refresh(meal)
    return meal


@router.post("/{meal_id}/simulate", summary="Portion what-if: original vs modified portions (nothing is saved)")
def simulate(body: SimulateIn, meal: Meal = Depends(owned_meal), user: User = Depends(active_user), db: Session = Depends(get_db)):
    foods = [f for f in meal.foods if not f.removed and f.nutrition_key]
    if not foods:
        raise HTTPException(422, "Add at least one food with a nutrition match first")
    ids = {f.id for f in foods}
    if bad := [i for i in body.portions if i not in ids]:
        raise HTTPException(422, f"Unknown or unmapped food id(s): {bad}")
    if any(not 0 <= g <= 3000 for g in body.portions.values()):
        raise HTTPException(422, "Portions must be between 0 and 3000 g")
    items = [{"id": f.id, "label": f.label, "nutrition_key": f.nutrition_key, "grams": f.grams,
              "new_grams": body.portions.get(f.id, f.grams), "range_g": (f.portion or {}).get("range_g")} for f in foods]
    out = forecast.portion_whatif(items, user.profile, body.horizon_min)
    out["glucose_scale"] = glucose_scale.scale(db, user, meal, out["meal_peak_units"])
    return out


@router.put("/{meal_id}/confirm", response_model=MealOut)
def confirm(body: ConfirmIn, meal: Meal = Depends(owned_meal), user: User = Depends(active_user),
            db: Session = Depends(get_db)):
    active = [f for f in meal.foods if not f.removed]
    if not active:
        raise HTTPException(422, "Add at least one food before saving")
    if any(not f.nutrition_key for f in active):
        raise HTTPException(422, "Every food needs a nutrition match (edit or remove unmatched items)")
    for f in active:
        if not f.confirmed:
            f.confirmed = True
            if f.mapping_quality in ("fuzzy", "provisional"):
                f.mapping_quality = "exact"  # user verified the suggested match
            db.add(Correction(user_id=user.id, meal_id=meal.id, food_id=f.id, kind="confirm",
                              after=_snapshot(f), model_name=_model_name(f),
                              before={"user_corrected": f.user_corrected, "origin": f.origin}))
    for f in active:   # saved meal = labels accepted: remember photo regions (memory + training data)
        memory.record(db, user, meal, f, "confirmed")
    if body.meal_type:
        meal.meal_type = body.meal_type
    if body.eaten_at:
        meal.eaten_at = body.eaten_at
    meal.status = "confirmed"
    db.commit()
    db.refresh(meal)
    return meal


@router.put("/{meal_id}/foods/{food_id}", response_model=MealOut, summary="Edit food label and/or portion")
def update_food(food_id: int, body: FoodUpdateIn, meal: Meal = Depends(owned_meal),
                user: User = Depends(active_user), db: Session = Depends(get_db)):
    f = next((x for x in meal.foods if x.id == food_id and (not x.removed or body.restore)), None)
    if not f:
        raise HTTPException(404, "Food not found")
    before = _snapshot(f)
    if not custom_foods.owned(body.nutrition_key, user.id):
        raise HTTPException(422, "Unknown nutrition_key")
    was_unidentified = not f.nutrition_key
    kinds = []
    if body.restore and f.removed:
        f.removed = False
        kinds.append("add")
    if body.candidate_class_id is not None:
        cls = vision.taxonomy_class(body.candidate_class_id)
        if not cls:
            raise HTTPException(422, "Unknown taxonomy class id")
        if cls["name"] != f.taxonomy_class:
            f.label, f.taxonomy_class = cls["name"], cls["name"]
            ref = nutrition.get(cls["nutrition_key"])
            if ref and (not f.grams or f.nutrition_key != ref["key"]):
                f.grams, f.portion = portion.estimate(ref)
            analysis.apply_mapping(f, cls["nutrition_key"], cls["match"])
            if not ref:
                f.grams, f.portion = 0, dict(analysis.UNKNOWN_PORTION)
            kinds.append("edit_food")
    elif body.nutrition_key is not None and body.nutrition_key != f.nutrition_key:
        ref = nutrition.get(body.nutrition_key)
        if not ref:
            raise HTTPException(422, "Unknown nutrition_key")
        f.label = body.label or ref["name"]
        if body.grams is None and not f.grams:
            f.grams, f.portion = portion.estimate(ref)
        analysis.apply_mapping(f, ref["key"], "exact")
        kinds.append("edit_food")
    elif body.label and body.label != f.label:
        f.label = body.label
        kinds.append("edit_food")
    if body.grams is not None and body.grams != f.grams:
        f.grams = body.grams
        f.portion = portion.user_entered(body.grams)
        analysis.apply_mapping(f, f.nutrition_key, f.mapping_quality)
        kinds.append("edit_portion")
    if f.mapping_quality in ("fuzzy", "provisional") and body.confirmed:
        f.mapping_quality = "exact"  # user verified the suggested match
    if body.confirmed is not None:
        f.confirmed = body.confirmed
    if kinds:
        f.user_corrected = True
        for k in kinds:
            db.add(Correction(user_id=user.id, meal_id=meal.id, food_id=f.id, kind=k, before=before,
                              after=_snapshot(f), model_name=_model_name(f)))
    if "edit_food" in kinds or body.confirmed:   # remember the label for this photo region (memory + training data)
        memory.record(db, user, meal, f, "named" if was_unidentified else "corrected" if "edit_food" in kinds else "confirmed")
    analysis.recompute(meal, user.profile)
    db.commit()
    db.refresh(meal)
    return meal


@router.post("/{meal_id}/foods/merge", response_model=MealOut, summary="Merge several detections into one food")
def merge_foods(body: MergeIn, meal: Meal = Depends(owned_meal), user: User = Depends(active_user),
                db: Session = Depends(get_db)):
    foods = [next((f for f in meal.foods if f.id == i and not f.removed), None) for i in body.food_ids]
    if any(f is None for f in foods):
        raise HTTPException(404, "Food not found")
    keep = next((f for f in foods if f.nutrition_key), foods[0])
    before = [_snapshot(f) for f in foods]
    grams = sum(f.grams for f in foods if f.nutrition_key == keep.nutrition_key or not f.nutrition_key) or keep.grams
    pred = dict(keep.original_prediction or {})
    boxes = [b for b in ((f.original_prediction or {}).get("bbox") for f in foods) if b]
    if boxes:
        x1, y1 = min(b["x"] for b in boxes), min(b["y"] for b in boxes)
        pred["bbox"] = {"x": x1, "y": y1, "w": max(b["x"] + b["w"] for b in boxes) - x1,
                        "h": max(b["y"] + b["h"] for b in boxes) - y1}
    pred["merged_from"] = [f.id for f in foods if f is not keep]
    keep.original_prediction = pred
    if keep.nutrition_key and grams != keep.grams:
        keep.grams, keep.portion = grams, {**keep.portion, "notes": (keep.portion.get("notes") or [])
                                           + [f"Merged {len(foods)} detections; portions added."]}
        analysis.apply_mapping(keep, keep.nutrition_key, keep.mapping_quality)
    keep.user_corrected = True
    for f in foods:
        if f is not keep:
            f.removed = True
    db.add(Correction(user_id=user.id, meal_id=meal.id, food_id=keep.id, kind="merge",
                      before={"foods": before}, after=_snapshot(keep), model_name=_model_name(keep)))
    analysis.recompute(meal, user.profile)
    db.commit()
    db.refresh(meal)
    return meal


@router.post("/{meal_id}/foods", response_model=MealOut, status_code=201, summary="Add a missing food")
def add_food(body: FoodAddIn, meal: Meal = Depends(owned_meal), user: User = Depends(active_user),
             db: Session = Depends(get_db)):
    tax = None
    if not custom_foods.owned(body.nutrition_key, user.id):
        raise HTTPException(422, "Unknown nutrition_key")
    if body.candidate_class_id is not None:
        tax = vision.taxonomy_class(body.candidate_class_id)
        if not tax:
            raise HTTPException(422, "Unknown taxonomy class id")
        key, quality = tax["nutrition_key"], tax["match"]
    else:
        key, quality = (body.nutrition_key, "exact") if body.nutrition_key else nutrition.lookup(body.label or "")
    ref = nutrition.get(key)
    if body.nutrition_key and not ref:
        raise HTTPException(422, "Unknown nutrition_key")
    if not ref and not body.label and not tax:
        raise HTTPException(422, "Provide candidate_class_id, nutrition_key or label")
    if body.grams:
        grams, pinfo = body.grams, portion.user_entered(body.grams)
    elif ref:
        grams, pinfo = portion.estimate(ref, servings=body.servings)
        pinfo["method"] = "typical_serving_manual"
    else:
        grams, pinfo = 0, {"method": "unknown", "uncertainty": "unknown", "range_g": None, "notes": []}
    f = MealFood(origin="manual", label=(tax and tax["name"]) or body.label or ref["name"], grams=grams, portion=pinfo,
                 taxonomy_class=tax["name"] if tax else None, user_corrected=True, original_prediction=None)
    analysis.apply_mapping(f, key, quality)
    meal.foods.append(f)
    db.flush()
    db.add(Correction(user_id=user.id, meal_id=meal.id, food_id=f.id, kind="add", after=_snapshot(f)))
    analysis.recompute(meal, user.profile)
    if meal.status == "captured":
        meal.status = "analyzed"
    db.commit()
    db.refresh(meal)
    return meal


def _region(meal: Meal, body: RegionIn) -> tuple[dict, dict, list[dict], list[float], str | None]:
    """The photo, the clipped box, and the classifier's view of the region the user drew."""
    im = next((i for i in meal.images if i["view"] == body.view), None)
    if not im:
        raise HTTPException(422, f"This meal has no {body.view} photo")
    b = body.bbox
    box = {"x": round(b.x, 4), "y": round(b.y, 4), "w": round(min(b.w, 1 - b.x), 4), "h": round(min(b.h, 1 - b.y), 4)}
    if box["w"] < 0.02 or box["h"] < 0.02:
        raise HTTPException(422, "The box is too small: drag over the whole food")
    try:
        top, fp, shadow = vision.classify_region(im["path"], im.get("original_path"), box)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return im, box, top, fp, shadow


def _drawn_prediction(meal: Meal, view: str, box: dict, top: list[dict], fp: list[float], shadow: str | None, kind: str) -> dict:
    n = 1 + sum(1 for f in meal.foods if (f.original_prediction or {}).get("drawn"))
    cls = vision.models().get("classifier") or {}
    t1 = top[0]
    return {"region_id": f"{view}-d{n}", "kind": kind, "model_label": t1["label"] if kind == "food" else None,
            "class_id": t1["class_id"] if kind == "food" else None, "nutrition_key": t1["nutrition_key"] if kind == "food" else None,
            "match": t1["match"] if kind == "food" else "none", "score": t1["score"], "candidates": top, "bbox": box,
            "view": view, "views": [view], "instance": "marked by you", "area_frac": round(box["w"] * box["h"], 4),
            "has_mask": False, "instances": 1, "fingerprint": fp, "shadow_label": shadow, "drawn": True,
            "model_name": cls.get("name"), "model_version": cls.get("version"), "score_band": vision.score_band(t1["score"]),
            "score_type": "raw softmax score (uncalibrated)", "needs_review": True}


def _portion_for(meal: Meal, ref: dict, box: dict) -> tuple[float, dict]:
    return portion.estimate(ref, bbox=box, area_frac=box["w"] * box["h"], reference_object=meal.reference_object,
                            n_views=len(meal.images), note=meal.serving_note)


@router.post("/{meal_id}/regions", response_model=MealOut, status_code=201,
             summary="Add a food the detector missed, from a box the user drew on the photo")
def add_region(body: RegionIn, meal: Meal = Depends(owned_meal), user: User = Depends(active_user), db: Session = Depends(get_db)):
    im, box, top, fp, shadow = _region(meal, body)
    t1 = top[0]
    ref = nutrition.get(t1["nutrition_key"]) if t1["score"] >= tuning.get("vision.unknown_min") else None
    # the user's own earlier label for a region like this, under the same rule as analysis: only when the model is unsure
    mem = memory.matcher(db, user.id)(fp) if not ref or t1["score"] < analysis.vision_auto_accept() else None
    mref = nutrition.get(mem["nutrition_key"]) if mem else None
    if mref:
        grams, pinfo = _portion_for(meal, mref, box)
        pred = _drawn_prediction(meal, body.view, box, top, fp, shadow, "food")
        pred.update(model_label=mem["label"], nutrition_key=mref["key"], match="exact", needs_review=False,
                    memory={**mem, "model_label": t1["label"], "model_score": t1["score"]})
        f = MealFood(origin="memory", label=mem["label"], taxonomy_class=None, grams=grams, portion=pinfo, original_prediction=pred)
        analysis.apply_mapping(f, mref["key"], "exact")
    elif ref:
        grams, pinfo = _portion_for(meal, ref, box)
        f = MealFood(origin="drawn", label=t1["label"], taxonomy_class=t1["label"], grams=grams, portion=pinfo,
                     original_prediction=_drawn_prediction(meal, body.view, box, top, fp, shadow, "food"))
        analysis.apply_mapping(f, ref["key"], t1["match"])
    else:   # not sure: the user names it from the region's own top-3 or the food list
        n = 1 + sum(1 for x in meal.foods if not x.removed and x.label.startswith("Unidentified food"))
        f = MealFood(origin="drawn", label=f"Unidentified food {n}", taxonomy_class=None, grams=0,
                     portion=dict(analysis.UNKNOWN_PORTION), original_prediction=_drawn_prediction(meal, body.view, box, top, fp, shadow, "unknown"))
        analysis.apply_mapping(f, None, "none")
    meal.foods.append(f)
    db.flush()
    db.add(Correction(user_id=user.id, meal_id=meal.id, food_id=f.id, kind="add_region", after=_snapshot(f),
                      model_name=_model_name(f)))
    analysis.recompute(meal, user.profile)
    if meal.status == "captured":
        meal.status = "analyzed"
    db.commit()
    db.refresh(meal)
    return meal


@router.put("/{meal_id}/foods/{food_id}/region", response_model=MealOut,
            summary="Mark or move where a food is on the photo (its name stays; the portion follows the box)")
def set_region(food_id: int, body: RegionIn, meal: Meal = Depends(owned_meal), user: User = Depends(active_user),
               db: Session = Depends(get_db)):
    f = next((x for x in meal.foods if x.id == food_id and not x.removed), None)
    if not f:
        raise HTTPException(404, "Food not found")
    before = _snapshot(f)
    im, box, top, fp, shadow = _region(meal, body)
    pred = dict(f.original_prediction or {})
    pred.update(bbox=box, view=body.view, views=[body.view], area_frac=round(box["w"] * box["h"], 4), fingerprint=fp,
                candidates=top, instance="marked by you", drawn=True, has_mask=False, shadow_label=shadow)
    pred.setdefault("kind", "food" if f.nutrition_key else "unknown")
    pred.setdefault("region_id", f"{body.view}-d{1 + sum(1 for x in meal.foods if (x.original_prediction or {}).get('drawn'))}")
    pred.setdefault("score", top[0]["score"])
    f.original_prediction = pred
    ref = nutrition.get(f.nutrition_key)
    if ref and (f.portion or {}).get("method") != "user_entered":   # the user's own grams always stand
        f.grams, f.portion = _portion_for(meal, ref, box)
        analysis.apply_mapping(f, f.nutrition_key, f.mapping_quality)
    db.add(Correction(user_id=user.id, meal_id=meal.id, food_id=f.id, kind="edit_region", before=before, after=_snapshot(f),
                      model_name=_model_name(f)))
    if f.confirmed or f.user_corrected:   # the remembered example now uses the marked region
        memory.record(db, user, meal, f, "corrected" if f.user_corrected else "confirmed")
    analysis.recompute(meal, user.profile)
    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/{meal_id}/foods/{food_id}", response_model=MealOut, summary="Remove a food (kept for evaluation)")
def remove_food(food_id: int, meal: Meal = Depends(owned_meal), user: User = Depends(active_user),
                db: Session = Depends(get_db)):
    f = next((x for x in meal.foods if x.id == food_id and not x.removed), None)
    if not f:
        raise HTTPException(404, "Food not found")
    f.removed = True
    db.add(Correction(user_id=user.id, meal_id=meal.id, food_id=f.id, kind="remove", before=_snapshot(f),
                      model_name=_model_name(f)))
    analysis.recompute(meal, user.profile)
    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/{meal_id}", status_code=204)
def delete_meal(meal: Meal = Depends(owned_meal), db: Session = Depends(get_db)):
    shutil.rmtree(settings.data_dir / "uploads" / str(meal.user_id) / str(meal.id), ignore_errors=True)
    db.delete(meal)
    db.commit()
