from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import current_user
from app.models import Meal, User
from app.services import advisor

router = APIRouter(prefix="/advisor", tags=["advisor"])


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[Turn] = Field(default_factory=list, max_length=12)
    meal_id: int | None = None
    tz_offset_min: int = 0


@router.post("/chat", summary="Meal Advisor reply grounded in the user's meals, profile and the food table")
def chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meal = None
    if body.meal_id is not None:
        meal = db.get(Meal, body.meal_id)
        if not meal or meal.user_id != user.id:
            raise HTTPException(404, "Meal not found")
    return advisor.answer(db, user, body.message.strip(), [t.model_dump() for t in body.history], meal, body.tz_offset_min)
