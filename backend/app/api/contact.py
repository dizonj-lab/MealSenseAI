"""Public contact form. Stored first, then emailed to the site owner in the background (if SMTP is configured)."""
import time
from collections import defaultdict, deque
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.models import ContactMessage
from app.services import mailer

router = APIRouter(prefix="/contact", tags=["contact"])
LIMIT, WINDOW_S = 5, 3600
_recent: dict[str, deque] = defaultdict(deque)


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    topic: Literal["Feedback", "Question", "Data request", "Bug report", "Other"] = "Question"
    message: str = Field(min_length=10, max_length=5000)
    website: str = ""   # honeypot: hidden from people, filled in by bots


def _deliver(msg_id: int):
    with SessionLocal() as db:
        c = db.get(ContactMessage, msg_id)
        c.email_status = mailer.send_contact(c.name, c.email, c.topic, c.message)
        db.commit()


@router.post("", status_code=201)
def send(body: ContactIn, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if body.website:
        return {"ok": True}   # silently drop bot submissions
    ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")
    q, now = _recent[ip], time.monotonic()
    while q and now - q[0] > WINDOW_S:
        q.popleft()
    if len(q) >= LIMIT:
        raise HTTPException(429, "Too many messages from this connection. Please try again later.")
    q.append(now)
    c = ContactMessage(name=body.name.strip(), email=str(body.email), topic=body.topic, message=body.message.strip(),
                       email_status="queued" if mailer.configured() else "not_configured")
    db.add(c)
    db.commit()
    if mailer.configured():
        tasks.add_task(_deliver, c.id)
    return {"ok": True}
