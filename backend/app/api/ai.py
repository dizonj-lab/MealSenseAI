from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import cache
from app.core.db import get_db
from app.core.security import current_user
from app.models import Correction, Experiment, InferenceLog, User
from app.services import nutrition, portion, slm, vision

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
                   "models": [{**m, "latency": _latency(db, m["name"]), "score_calibrated": False,
                               "accuracy": (f"test accuracy {m['test_metrics']['accuracy']:.3f}, macro-F1 "
                                            f"{m['test_metrics']['macro_f1']:.3f} (held-out split)")
                               if m.get("test_metrics") else "not measured on food data"}
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


@router.get("/foods/search", tags=["foods"])
def search_foods(q: str = Query("", max_length=100), user: User = Depends(current_user)):
    return nutrition.search(q) if q.strip() else [nutrition.summary(f) for f in nutrition.all_foods()]


@router.get("/foods/{key}", tags=["foods"])
def food_detail(key: str, user: User = Depends(current_user)):
    f = nutrition.get(key)
    return f or {}


@router.get("/reference-objects", tags=["foods"])
def reference_objects():
    return portion.REFERENCE_OBJECTS
