from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import active_user
from app.models import Meal, User


def owned_meal(meal_id: int, user: User = Depends(active_user), db: Session = Depends(get_db)) -> Meal:
    meal = db.get(Meal, meal_id)
    if not meal or meal.user_id != user.id:
        raise HTTPException(404, "Meal not found")
    return meal
