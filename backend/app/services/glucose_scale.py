"""Turn the relative meal-glucose curve into an estimated glucose value: baseline (your pre-meal reading, or unknown)
+ the rise from this meal.

The meal model (services/forecast.py) tracks meal glucose in arbitrary units, so its curve is converted with an
explicit calibration anchor:
  population  scaled so a 75 g glucose drink gives a peak rise of about +3 mmol/L with normal glucose tolerance,
              +5 with prediabetes and +8 with diabetes (approximate oral-glucose-tolerance-test ranges), band ±50%
  personal    once >= 3 meals have a pre-meal reading and a reading 20–180 min after eating, the median ratio of your
              measured rise to the model's predicted rise replaces the population anchor; the band is the spread of
              those ratios (at least ±25%)
Readings are never generated; they only calibrate and anchor the estimate. Not for insulin or medication decisions.
"""
from datetime import timedelta
from functools import lru_cache
from statistics import median, quantiles

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GlucoseReading, Meal, User
from app.services import forecast

MGDL_PER_MMOL = 18.016
OGTT_PEAK_RISE = {"normal": 3.0, "prediabetes": 5.0, "diabetes": 8.0}
POP_BAND = (0.5, 1.5)
MIN_MEALS = 3


def group(status: str | None) -> str:
    return "prediabetes" if status == "prediabetes" else "diabetes" if status in ("type1", "type2", "gestational") else "normal"


@lru_cache
def _ogtt_model_peak(grp: str) -> float:
    status = {"normal": None, "prediabetes": "prediabetes", "diabetes": "type2"}[grp]
    k, _ = forecast._clearance_k(status)
    meal = {"glycemic_carbs_g": 75.0, "absorption_peak_min": 30, "available_carbs_g": 75.0, "gi_assumed_for": [], "kcal": 0}
    return max(forecast._simulate(meal, k, forecast.DEFAULT_WEIGHT_KG, None, 300)["series"])


def mmol_per_unit(status: str | None) -> float:
    g = group(status)
    return OGTT_PEAK_RISE[g] / _ogtt_model_peak(g)


def _profile_status(user: User):
    p = user.profile
    return p.diabetes_status if p and p.health_consent else None


def _predicted_rise(meal: Meal, user: User, minutes: list[int]) -> float | None:
    from app.services import analysis
    foods = [analysis.food_dict(f) for f in meal.foods if not f.removed and f.nutrition_key]
    if not foods:
        return None
    status = _profile_status(user)
    k, _ = forecast._clearance_k(status)
    weight = (user.profile.weight_kg if user.profile and user.profile.weight_kg else None) or forecast.DEFAULT_WEIGHT_KG
    series = forecast._simulate(forecast._meal_inputs(foods, meal.totals or {}), k, weight, None, 300)["series"]   # every 5 min
    vals = [series[min(len(series) - 1, max(0, round(m / 5)))] for m in minutes]
    return max(vals) * mmol_per_unit(status) if vals else None


def baseline(db: Session, user_id: int, meal: Meal) -> tuple[float | None, str | None]:
    """Your measured pre-meal level: a reading linked to this meal or taken up to 90 min before it."""
    rows = db.scalars(select(GlucoseReading).where(
        GlucoseReading.user_id == user_id,
        GlucoseReading.measured_at >= meal.eaten_at - timedelta(minutes=90),
        GlucoseReading.measured_at <= meal.eaten_at + timedelta(minutes=5)).order_by(GlucoseReading.measured_at.desc())).all()
    rows = [r for r in rows if r.context != "after_meal"]
    if not rows:
        return None, None
    r = rows[0]
    return r.value_mmol, f"your {r.context.replace('_', ' ')} reading at {r.measured_at.strftime('%H:%M')}"


def personal_ratios(db: Session, user: User, limit: int = 30) -> list[float]:
    meal_ids = db.scalars(select(GlucoseReading.meal_id).where(GlucoseReading.user_id == user.id, GlucoseReading.meal_id.is_not(None))
                          .distinct().limit(limit)).all()
    ratios = []
    for mid in meal_ids:
        meal = db.get(Meal, mid)
        if not meal:
            continue
        pre, _ = baseline(db, user.id, meal)
        posts = [(round((r.measured_at - meal.eaten_at).total_seconds() / 60), r.value_mmol) for r in
                 db.scalars(select(GlucoseReading).where(GlucoseReading.meal_id == mid)).all()]
        posts = [(m, v) for m, v in posts if 20 <= m <= 180]
        if pre is None or not posts:
            continue
        pred = _predicted_rise(meal, user, [m for m, _ in posts])
        if pred and pred > 0.3:
            ratios.append(min(5.0, max(0.1, (max(v for _, v in posts) - pre) / pred)))
    return ratios


def scale(db: Session, user: User, meal: Meal, meal_peak_units: float) -> dict:
    """How to draw the curve in mmol/L: value = baseline (if known) + index/100 × peak_rise."""
    status = _profile_status(user)
    pop_peak = meal_peak_units * mmol_per_unit(status)
    ratios = personal_ratios(db, user)
    if len(ratios) >= MIN_MEALS:
        f = median(ratios)
        q = quantiles(ratios, n=4) if len(ratios) >= 4 else [min(ratios), f, max(ratios)]
        lo, hi = min(q[0], f * 0.75), max(q[-1], f * 1.25)
        cal = {"kind": "personal", "n_meals": len(ratios), "factor_vs_population": round(f, 2),
               "label": f"Calibrated from {len(ratios)} of your meals with readings"}
    else:
        f, (lo, hi) = 1.0, POP_BAND
        cal = {"kind": "population", "n_meals": len(ratios), "factor_vs_population": 1.0,
               "label": "Population estimate" + (f" ({len(ratios)}/{MIN_MEALS} meals with readings for personal calibration)" if ratios else "")}
    base, src = baseline(db, user.id, meal)
    unit = (user.profile.glucose_unit if user.profile else None) or "mmol/L"
    return {"unit": unit, "mgdl_per_mmol": MGDL_PER_MMOL, "baseline_mmol": base, "baseline_source": src,
            "peak_rise_mmol": round(pop_peak * f, 2), "band_mmol": [round(pop_peak * lo, 2), round(pop_peak * hi, 2)],
            "calibration": cal, "glucose_group": group(status),
            "anchor": "75 g glucose drink ≈ +3 / +5 / +8 mmol/L peak rise (normal / prediabetes / diabetes), approximate OGTT ranges",
            "note": ("Estimate only, even when it starts from your measured pre-meal reading: the curve after that point is "
                     "modelled, not measured, and your real response can differ. Do not use it to adjust insulin or medication.")}
