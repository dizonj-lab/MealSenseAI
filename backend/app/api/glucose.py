"""Measured glucose readings entered by the user (meter / CGM). Values are stored in mmol/L
(mg/dL ÷ 18.016). The app never generates or estimates these values."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import current_user
from app.models import GlucoseReading, Meal, User

router = APIRouter(prefix="/glucose", tags=["glucose"])
MGDL_PER_MMOL = 18.016


class ReadingIn(BaseModel):
    value: float = Field(gt=0)
    unit: Literal["mmol/L", "mg/dL"] = "mmol/L"
    measured_at: datetime
    context: Literal["fasting", "before_meal", "after_meal", "other"] = "other"
    source: Literal["meter", "cgm"] = "meter"
    meal_id: int | None = None
    note: str | None = Field(default=None, max_length=200)


def out(r: GlucoseReading) -> dict:
    return {"id": r.id, "meal_id": r.meal_id, "measured_at": r.measured_at.isoformat(), "value_mmol": r.value_mmol,
            "entered_unit": r.entered_unit, "context": r.context, "source": r.source, "note": r.note,
            "kind": "measured"}


@router.get("")
def list_readings(meal_id: int | None = None, days: int = Query(30, ge=1, le=365),
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(GlucoseReading).where(GlucoseReading.user_id == user.id)
    if meal_id is not None:
        q = q.where(GlucoseReading.meal_id == meal_id)
    else:
        q = q.where(GlucoseReading.measured_at >= datetime.now(timezone.utc) - timedelta(days=days))
    return [out(r) for r in db.scalars(q.order_by(GlucoseReading.measured_at)).all()]


@router.post("", status_code=201)
def add_reading(body: ReadingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mmol = body.value / MGDL_PER_MMOL if body.unit == "mg/dL" else body.value
    if not 1.0 <= mmol <= 35.0:
        raise HTTPException(422, "Value outside the range a glucose meter reports (1–35 mmol/L / 18–630 mg/dL)")
    if body.meal_id is not None and not db.scalar(select(Meal.id).where(Meal.id == body.meal_id, Meal.user_id == user.id)):
        raise HTTPException(404, "Meal not found")
    at = body.measured_at if body.measured_at.tzinfo else body.measured_at.replace(tzinfo=timezone.utc)
    r = GlucoseReading(user_id=user.id, meal_id=body.meal_id, measured_at=at, value_mmol=round(mmol, 2),
                       entered_unit=body.unit, context=body.context, source=body.source, note=body.note)
    db.add(r)
    db.commit()
    return out(r)


@router.delete("/{reading_id}", status_code=204)
def delete_reading(reading_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(GlucoseReading, reading_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "Reading not found")
    db.delete(r)
    db.commit()
