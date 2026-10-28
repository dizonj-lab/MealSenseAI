"""Personal food memory and labelled training samples.

Whenever the user names, corrects or confirms a food that came from a photo region, the region's fingerprint
(sqrt of EXP-002 class probabilities) is stored with the label as a TrainingSample. On later meals, an
unidentified or low-confidence region whose fingerprint is close to one of the user's samples is labelled
from memory (shown as "known from your earlier label", still editable).

Threshold: on held-out Food-101 photos (3 classes, 3 remembered photos per class, 120 queries) cosine >= 0.70
gave 94/120 matches, all correct; 0.60 gave 101/120, all correct. 0.70 plus a 0.05 margin over the best
sample with a different label is used to stay conservative with more foods.
"""
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Meal, MealFood, TrainingSample, User
from app.services import nutrition, screening, tuning

MATCH_MIN = 0.70   # default; the live value is the admin setting memory.match_min
MARGIN = 0.05
MAX_SAMPLES = 2000


def record(db: Session, user: User, meal: Meal, f: MealFood, source: str) -> TrainingSample | None:
    """Create or update the labelled sample for a photo-derived food (no-op for manual/description items)."""
    pred = f.original_prediction or {}
    fp = pred.get("fingerprint")
    if not fp or not f.nutrition_key or f.removed:
        return None
    image = next((im for im in meal.images if im["view"] == pred.get("view")), None)
    if not image:
        return None
    ref = nutrition.get(f.nutrition_key) or {}
    s = db.scalar(select(TrainingSample).where(TrainingSample.food_id == f.id)) or TrainingSample(food_id=f.id, user_id=user.id)
    if s.id is not None and s.label != f.label:   # a new label is a new claim: an earlier review no longer applies
        s.reviewed_at = s.reviewed_by = s.review_note = None
    if s.id is None and user.training_consent:    # shared from the moment it is made, while consent is on
        s.consent_at = datetime.now(timezone.utc)
    s.meal_id, s.view = meal.id, image["view"]
    s.image_path = image.get("original_path") or image["path"]
    s.bbox, s.fingerprint = pred.get("bbox"), fp
    s.label, s.nutrition_key = f.label, f.nutrition_key
    s.taxonomy_class = f.taxonomy_class if f.taxonomy_class == f.label else None
    s.custom_food_id = ref.get("custom_food_id")
    said = pred.get("memory") or pred   # for memory-labelled items keep what the model itself said
    s.model_label, s.model_score = said.get("model_label"), said.get("model_score", pred.get("score"))
    s.model_version = pred.get("model_version")
    s.model_candidates = [{"label": c.get("label"), "nutrition_key": c.get("nutrition_key"), "score": c.get("score")}
                          for c in (pred.get("candidates") or [])[:3]]
    if s.id is None or source != "confirmed":   # confirming later does not downgrade a "named"/"corrected" sample
        s.source = source
    db.add(s)
    screening.screen_one(db, s, user)
    return s


def matcher(db: Session, user_id: int):
    """Return a function fp -> best memory match (or None) over the user's samples."""
    rows = db.execute(select(TrainingSample.id, TrainingSample.label, TrainingSample.nutrition_key, TrainingSample.fingerprint)
                      .where(TrainingSample.user_id == user_id).order_by(TrainingSample.id.desc()).limit(MAX_SAMPLES)).all()
    rows = [r for r in rows if r.nutrition_key and nutrition.get(r.nutrition_key)]
    if not rows:
        return lambda fp: None
    by_size: dict[int, tuple[list, np.ndarray]] = {}   # a new model has a different number of classes

    def matrix(n: int):
        if n not in by_size:
            rs = [r for r in rows if len(r.fingerprint or []) == n]
            M = np.array([r.fingerprint for r in rs], dtype=np.float32).reshape(len(rs), n)
            by_size[n] = (rs, M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9))
        return by_size[n]

    def match(fp):
        if not fp:
            return None
        rows_n, M = matrix(len(fp))
        if not rows_n:
            return None
        v = np.asarray(fp, dtype=np.float32)
        sims = M @ (v / (np.linalg.norm(v) + 1e-9))
        i = int(sims.argmax())
        best = rows_n[i]
        other = max((float(s) for s, r in zip(sims, rows_n) if r.nutrition_key != best.nutrition_key), default=0.0)
        if sims[i] < tuning.get("memory.match_min") or sims[i] - other < MARGIN:
            return None
        return {"sample_id": best.id, "label": best.label, "nutrition_key": best.nutrition_key,
                "similarity": round(float(sims[i]), 3), "next_best_other": round(other, 3)}
    return match
