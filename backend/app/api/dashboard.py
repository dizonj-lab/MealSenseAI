from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import current_user
from app.models import Meal, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
KEYS = ("calories_kcal", "carbs_g", "protein_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")


@router.get("/summary")
def summary(tz_offset_min: int = Query(0), days: int = Query(7, ge=1, le=90),
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    tz = timezone(timedelta(minutes=tz_offset_min))
    today = datetime.now(tz).date()
    start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), tz)
    meals = db.scalars(select(Meal).where(Meal.user_id == user.id, Meal.status != "captured",
                                          Meal.eaten_at >= start).order_by(Meal.eaten_at.desc())).all()
    trend = {(today - timedelta(days=i)).isoformat(): {k: 0.0 for k in KEYS} | {"meals": 0}
             for i in range(days - 1, -1, -1)}
    for m in meals:
        d = trend.get(m.eaten_at.astimezone(tz).date().isoformat())
        if d is None:
            continue
        for k in KEYS:
            d[k] = round(d[k] + (m.totals.get(k) or 0), 1)
        d["meals"] += 1
    t = trend[today.isoformat()]
    kcal = t["calories_kcal"]
    macro = {n: round(t[f"{n}_g"] * w / kcal * 100) for n, w in (("carbs", 4), ("protein", 4), ("fat", 9))} if kcal else {}
    p = user.profile
    goals = {"calorie_goal": p.calorie_goal, "carb_goal_g": p.carb_goal_g, "protein_goal_g": p.protein_goal_g,
             "goals": p.goals} if p else {}
    recent = db.scalars(select(Meal).where(Meal.user_id == user.id, Meal.status != "captured")
                        .order_by(Meal.eaten_at.desc()).limit(5)).all()
    total_meals = db.query(Meal).filter(Meal.user_id == user.id, Meal.status != "captured").count()
    return {
        "date": today.isoformat(), "today": t, "macro_energy_pct": macro, "goals": goals,
        "trend": [{"date": k, **v} for k, v in trend.items()],
        "recent_meals": [{"id": m.id, "eaten_at": m.eaten_at, "meal_type": m.meal_type, "status": m.status,
                          "calories_kcal": m.totals.get("calories_kcal"), "carbs_g": m.totals.get("carbs_g"),
                          "labels": [f.label for f in m.foods if not f.removed],
                          "glucose_level": (m.insights.get("glucose") or {}).get("level"),
                          "has_image": bool(m.images)} for m in recent],
        "total_meals": total_meals, "is_demo": False,
    }
