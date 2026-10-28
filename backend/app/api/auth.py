from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_token, create_verify_token, hash_password, read_verify_token, verify_password
from app.models import HealthProfile, User
from app.schemas import LoginIn, RegisterIn, TokenOut
from app.services import audit, mailer

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    user.profile = HealthProfile()
    db.add(user)
    db.commit()
    background.add_task(send_verification, user, base_url(request))
    return TokenOut(access_token=create_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return TokenOut(access_token=create_token(user.id))


def base_url(request: Request) -> str:
    return (settings.public_url or str(request.base_url)).rstrip("/")


def send_verification(user: User, base: str) -> str:
    link = f"{base}/verify?token={create_verify_token(user.id, user.email)}"
    return mailer.send_verification(user.email, user.name, link)


class VerifyIn(BaseModel):
    token: str


@router.post("/verify", summary="Confirm an email address from the link in the verification email")
def verify(body: VerifyIn, db: Session = Depends(get_db)):
    claims = read_verify_token(body.token)
    user = db.get(User, claims[0]) if claims else None
    if not user or user.email != claims[1]:
        raise HTTPException(400, "This link is invalid or has expired. Send a new one from Settings.")
    if not user.email_verified_at:
        user.email_verified_at = datetime.now(timezone.utc)
        audit.log(db, user.id, "email.verified", "user", user.id)
        db.commit()
    return {"verified": True, "email": user.email}
