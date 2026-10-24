"""User-defined foods: registered into the nutrition lookup as "custom_<id>" records (owner-only)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CustomFood
from app.services import nutrition


def key(cf_id: int) -> str:
    return f"custom_{cf_id}"


def record(cf: CustomFood) -> dict:
    return {"key": key(cf.id), "name": cf.name, "category": "custom", "region": "custom", "user_id": cf.user_id,
            "custom_food_id": cf.id, "per_100g": {n: cf.per_100g.get(n) for n in nutrition.NUTRIENTS},
            "default_serving_g": cf.serving_g, "serving_desc": cf.serving_desc,
            "glycemic_index": cf.glycemic_index, "gi_source": "entered by you" if cf.glycemic_index is not None else None,
            "refined_carb": False, "allergens": [], "aliases": [a.lower() for a in (cf.aliases or [])],
            "source": "Entered by you", "verification": "user_entered"}


def register(cf: CustomFood) -> dict:
    nutrition.CUSTOM[key(cf.id)] = rec = record(cf)
    return rec


def load_all(db: Session) -> int:
    rows = db.scalars(select(CustomFood)).all()
    for cf in rows:
        register(cf)
    return len(rows)


def owned(k: str | None, user_id: int) -> bool:
    """False only for another user's custom food (reference-table keys are shared)."""
    rec = nutrition.CUSTOM.get(k or "")
    return rec is None or rec["user_id"] == user_id


def search(user_id: int, q: str) -> list[dict]:
    qn = q.lower().strip()
    return [nutrition.summary(r) | {"custom": True} for r in nutrition.CUSTOM.values()
            if r["user_id"] == user_id and (not qn or qn in r["name"].lower() or any(qn in a for a in r["aliases"]))]
