from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import cache
from app.core.db import get_db
from app.core.security import current_user
from app.models import Correction, CustomFood, Experiment, InferenceLog, User
from app.services import custom_foods, nutrition, portion, slm, vision

router = APIRouter(tags=["ai"])


def _latency(db: Session, name: str) -> dict:
    rows = db.scalars(select(InferenceLog.latency_ms).where(InferenceLog.model_name == name, InferenceLog.ok)
                      .order_by(InferenceLog.id.desc()).limit(500)).all()
    if not rows:
        return {"count": 0}
    s = sorted(rows)
    return {"count": len(s), "avg_ms": round(sum(s) / len(s), 1), "p95_ms": round(s[int(0.95 * (len(s) - 1))], 1)}


@router.get("/ai/models")
def models(user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = vision.status()
    s = slm.status(force=True)
    corr = dict(db.execute(select(Correction.kind, func.count()).where(Correction.user_id == user.id)
                           .group_by(Correction.kind)).all())
    # agreement between model predictions and the user's final decision (not a benchmark)
    model_conf = db.execute(select(Correction.before).where(
        Correction.user_id == user.id, Correction.kind == "confirm", Correction.model_name.is_not(None))).scalars().all()
    accepted = sum(1 for b in model_conf if not (b or {}).get("user_corrected"))
    rejected = db.query(Correction).filter(Correction.user_id == user.id, Correction.model_name.is_not(None),
                                           Correction.kind.in_(["edit_food", "remove"])).count()
    slm_rows = db.execute(select(func.count(), func.avg(InferenceLog.latency_ms), func.sum(InferenceLog.tokens))
                          .where(InferenceLog.model_version == "ollama")).one()
    return {
        "vision": {"available": v["available"], "error": v["error"],
                   "device": v.get("device"),
                   "models": [{**m, "latency": _latency(db, m["name"]), "score_calibrated": False,
                               "accuracy": (f"top-1 {m['reported_metrics']['top1_accuracy']:.2%}, top-3 "
                                            f"{m['reported_metrics']['top3_accuracy']:.2%}, macro-F1 "
                                            f"{m['reported_metrics']['macro_f1']:.2%} (reported by developer)")
                               if m.get("reported_metrics") else "not evaluated on food classes (supporting detector)"}
                              for m in v["models"].values()]},
        "slm": {**s, "role": "text-only: label normalisation, provisional matches, explanations",
                "calls": slm_rows[0], "avg_latency_ms": round(slm_rows[1] or 0, 1), "tokens": int(slm_rows[2] or 0),
                "cost": "0 (local)"},
        "nutrition": {"table": nutrition.version(), "records": len(nutrition.all_foods()),
                      "verification": "transcribed_unverified",
                      "sources": sorted({f["source"] for f in nutrition.all_foods()})},
        "portion": {"method": "typical-serving priors + optional reference-container area ratio",
                    "volume_measured": False, "reference_objects": portion.REFERENCE_OBJECTS},
        "cache": {**cache.stats, "redis_connected": cache.ping()},
        "corrections": corr,
        "user_agreement": {"accepted_unchanged": accepted, "corrected_or_removed": rejected,
                           "rate": round(accepted / (accepted + rejected), 3) if accepted + rejected else None,
                           "note": "Share of model-recognised foods kept unchanged by you. Not an accuracy benchmark."},
        "experiments": [{"id": e.id, "name": e.name, "model": e.model_name, "dataset": e.dataset,
                         "n_samples": e.n_samples, "has_ground_truth": e.has_ground_truth, "metrics": e.metrics,
                         "notes": e.notes, "created_at": e.created_at}
                        for e in db.scalars(select(Experiment).order_by(Experiment.id.desc()).limit(20))],
    }


@router.get("/taxonomy/search", tags=["foods"])
def search_taxonomy(q: str = Query("", max_length=100), user: User = Depends(current_user)):
    return vision.search_taxonomy(q)


@router.get("/foods/search", tags=["foods"])
def search_foods(q: str = Query("", max_length=100), user: User = Depends(current_user)):
    mine = custom_foods.search(user.id, q)
    return mine + (nutrition.search(q) if q.strip() else [nutrition.summary(f) for f in nutrition.all_foods()])


class CustomFoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    serving_g: float = Field(gt=0, le=3000)
    serving_desc: str = Field(default="1 serving", max_length=80)
    per_100g: dict[str, float | None] = Field(description="nutrients per 100 g; null = unknown (never filled in)")
    glycemic_index: float | None = Field(default=None, ge=0, le=110)
    aliases: list[str] = Field(default_factory=list, max_length=10)


def _custom_out(cf: CustomFood) -> dict:
    return custom_foods.record(cf) | {"id": cf.id}


def _validate(body: CustomFoodIn) -> dict:
    bad = [k for k in body.per_100g if k not in nutrition.NUTRIENTS]
    if bad:
        raise HTTPException(422, f"Unknown nutrient(s): {bad}")
    per = {n: body.per_100g.get(n) for n in nutrition.NUTRIENTS}
    if any(v is not None and (v < 0 or v > (900 if n == "calories_kcal" else 40000 if n == "sodium_mg" else 100)) for n, v in per.items()):
        raise HTTPException(422, "A nutrient value is outside the possible range per 100 g")
    return per


@router.get("/foods/custom", tags=["foods"])
def list_custom(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_custom_out(cf) for cf in db.scalars(select(CustomFood).where(CustomFood.user_id == user.id).order_by(CustomFood.name))]


@router.post("/foods/custom", tags=["foods"], status_code=201)
def create_custom(body: CustomFoodIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cf = CustomFood(user_id=user.id, name=body.name.strip(), serving_g=body.serving_g, serving_desc=body.serving_desc,
                    per_100g=_validate(body), glycemic_index=body.glycemic_index, aliases=body.aliases)
    db.add(cf)
    db.commit()
    custom_foods.register(cf)
    return _custom_out(cf)


@router.put("/foods/custom/{cf_id}", tags=["foods"])
def update_custom(cf_id: int, body: CustomFoodIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cf = db.get(CustomFood, cf_id)
    if not cf or cf.user_id != user.id:
        raise HTTPException(404, "Custom food not found")
    cf.name, cf.serving_g, cf.serving_desc = body.name.strip(), body.serving_g, body.serving_desc
    cf.per_100g, cf.glycemic_index, cf.aliases = _validate(body), body.glycemic_index, body.aliases
    db.commit()
    custom_foods.register(cf)   # existing meals keep their stored nutrients until edited
    return _custom_out(cf)


@router.get("/foods/{key}", tags=["foods"])
def food_detail(key: str, user: User = Depends(current_user)):
    f = nutrition.get(key) if custom_foods.owned(key, user.id) else None
    return f or {}


@router.get("/reference-objects", tags=["foods"])
def reference_objects():
    return portion.REFERENCE_OBJECTS
