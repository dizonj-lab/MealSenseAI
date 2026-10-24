from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import active_user
from app.models import ChatMessage, ChatThread, Meal, User
from app.services import advisor

router = APIRouter(prefix="/advisor", tags=["advisor"])


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    meal_id: int | None = None
    thread_id: int | None = None
    tz_offset_min: int = 0
    history: list[Turn] = Field(default_factory=list, max_length=12, description="ignored: history is kept server-side")


def _owned_meal(db: Session, user: User, meal_id: int | None) -> Meal | None:
    if meal_id is None:
        return None
    meal = db.get(Meal, meal_id)
    if not meal or meal.user_id != user.id:
        raise HTTPException(404, "Meal not found")
    return meal


@router.post("/chat", summary="Meal Advisor reply grounded in the user's meals, model outputs and the food table")
def chat(body: ChatIn, user: User = Depends(active_user), db: Session = Depends(get_db)):
    meal = _owned_meal(db, user, body.meal_id)
    if meal is None and advisor.MEALREF.search(body.message):   # "my meal" without an open meal -> the latest one
        meal = db.scalar(select(Meal).where(Meal.user_id == user.id, Meal.status.in_(("analyzed", "confirmed")))
                         .order_by(Meal.eaten_at.desc()))
    return advisor.answer(db, user, body.message.strip(), meal, body.tz_offset_min, body.thread_id)


@router.get("/threads", summary="The latest conversation (per meal, or general) with its messages")
def thread(meal_id: int | None = None, user: User = Depends(active_user), db: Session = Depends(get_db)):
    _owned_meal(db, user, meal_id)
    th = db.scalar(select(ChatThread).where(ChatThread.user_id == user.id, ChatThread.meal_id.is_(None) if meal_id is None
                                            else ChatThread.meal_id == meal_id).order_by(ChatThread.updated_at.desc()))
    if not th:
        return {"thread_id": None, "meal_id": meal_id, "messages": []}
    msgs = db.scalars(select(ChatMessage).where(ChatMessage.thread_id == th.id).order_by(ChatMessage.id)).all()
    return {"thread_id": th.id, "meal_id": th.meal_id, "messages": [
        {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat(), "source": (m.meta or {}).get("source"),
         "evidence": (m.meta or {}).get("evidence", []), "followups": (m.meta or {}).get("followups", []),
         "hypothetical": (m.meta or {}).get("hypothetical", False), "actions": (m.meta or {}).get("actions", [])} for m in msgs]}


@router.delete("/threads/{thread_id}", status_code=204, summary="Clear a conversation")
def clear(thread_id: int, user: User = Depends(active_user), db: Session = Depends(get_db)):
    th = db.get(ChatThread, thread_id)
    if not th or th.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    db.execute(delete(ChatMessage).where(ChatMessage.thread_id == th.id))
    db.delete(th)
    db.commit()
