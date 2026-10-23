import shutil
import time
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import owned_meal
from app.core.config import settings
from app.core.db import get_db
from app.core.security import current_user
from app.models import Correction, Meal, MealFood, User
from app.schemas import AnalyzeIn, ConfirmIn, FoodAddIn, FoodUpdateIn, HistoryOut, MealOut
from app.services import analysis, imaging, nutrition, portion

router = APIRouter(prefix="/meals", tags=["meals"])


def _snapshot(f: MealFood) -> dict:
    return {"label": f.label, "nutrition_key": f.nutrition_key, "grams": f.grams,
            "mapping_quality": f.mapping_quality, "nutrients": f.nutrients}


def _model_name(f: MealFood) -> str | None:
    return (f.original_prediction or {}).get("model_name")


@router.post("/capture", response_model=MealOut, status_code=201,
             summary="Upload top and/or side view photos (stage 1: validation & preprocessing)")
async def capture(top: UploadFile | None = File(None), side: UploadFile | None = File(None),
                  description: str | None = Form(None), reference_object: str | None = Form(None),
                  serving_note: str | None = Form(None), meal_type: str | None = Form(None),
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    uploads = [(v, u) for v, u in (("top", top), ("side", side)) if u is not None and u.filename]
    if not uploads and not (description or "").strip():
        raise HTTPException(422, "Provide at least one photo or a food description")
    if reference_object and reference_object not in portion.REFERENCE_OBJECTS:
        raise HTTPException(422, "Unknown reference object")
    meal = Meal(user_id=user.id, description=(description or "").strip() or None,
                reference_object=reference_object, serving_note=serving_note, meal_type=meal_type)
    db.add(meal)
    db.flush()
    t0 = time.perf_counter()
    images = []
    try:
        for view, up in uploads:
            raw = await up.read()
            if len(raw) > settings.max_upload_mb * 1024 * 1024:
                raise imaging.ImageError(f"{view}: file exceeds {settings.max_upload_mb} MB")
            images.append(imaging.process(raw, settings.data_dir / "uploads" / str(user.id) / str(meal.id), view))
    except imaging.ImageError as e:
        db.rollback()
        raise HTTPException(422, str(e))
    meal.images = images
    warn = [w for im in images for w in im["warnings"]]
    meal.stages = [{"key": "preprocess", "name": "Image validation & preprocessing", "status": "done",
                    "detail": (f"{len(images)} image(s) validated, orientation corrected, resized ≤1024 px; "
                               "originals retained." if images else "No photo provided; description only.")
                              + (" Warnings: " + "; ".join(warn) if warn else ""),
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}]
    db.commit()
    db.refresh(meal)
    return meal


@router.post("/analyze", response_model=MealOut, summary="Run recognition, portion, nutrition and insights")
def analyze(body: AnalyzeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meal = owned_meal(body.meal_id, user, db)
    analysis.run(db, meal, user.profile)
    db.commit()
    db.refresh(meal)
    return meal


@router.get("/history", response_model=HistoryOut)
def history(start: date | None = Query(None), end: date | None = Query(None),
            tz_offset_min: int = Query(0, description="Client UTC offset in minutes (e.g. 480 for SGT)"),
            user: User = Depends(current_user), db: Session = Depends(get_db)):
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
    im = next((i for i in meal.images if i["view"] == view), None)
    if not im:
        raise HTTPException(404, "Image not found")
    return FileResponse(im["original_path"] if original else im["path"])


@router.put("/{meal_id}/confirm", response_model=MealOut)
def confirm(body: ConfirmIn, meal: Meal = Depends(owned_meal), user: User = Depends(current_user),
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
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    f = next((x for x in meal.foods if x.id == food_id and not x.removed), None)
    if not f:
        raise HTTPException(404, "Food not found")
    before = _snapshot(f)
    kinds = []
    if body.nutrition_key is not None and body.nutrition_key != f.nutrition_key:
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
    analysis.recompute(meal, user.profile)
    db.commit()
    db.refresh(meal)
    return meal


@router.post("/{meal_id}/foods", response_model=MealOut, status_code=201, summary="Add a missing food")
def add_food(body: FoodAddIn, meal: Meal = Depends(owned_meal), user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    key, quality = (body.nutrition_key, "exact") if body.nutrition_key else nutrition.lookup(body.label or "")
    ref = nutrition.get(key)
    if body.nutrition_key and not ref:
        raise HTTPException(422, "Unknown nutrition_key")
    if not ref and not body.label:
        raise HTTPException(422, "Provide nutrition_key or label")
    if body.grams:
        grams, pinfo = body.grams, portion.user_entered(body.grams)
    elif ref:
        grams, pinfo = portion.estimate(ref, servings=body.servings)
        pinfo["method"] = "typical_serving_manual"
    else:
        grams, pinfo = 0, {"method": "unknown", "uncertainty": "unknown", "range_g": None, "notes": []}
    f = MealFood(origin="manual", label=body.label or ref["name"], grams=grams, portion=pinfo,
                 user_corrected=True, original_prediction=None)
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


@router.delete("/{meal_id}/foods/{food_id}", response_model=MealOut, summary="Remove a food (kept for evaluation)")
def remove_food(food_id: int, meal: Meal = Depends(owned_meal), user: User = Depends(current_user),
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
