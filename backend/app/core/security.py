from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret, algorithm="HS256")


VERIFY_HOURS = 48


def create_verify_token(user_id: int, email: str) -> str:
    """A link token that proves the person can read this inbox. Bound to the address, so changing it voids the link."""
    exp = datetime.now(timezone.utc) + timedelta(hours=VERIFY_HOURS)
    return jwt.encode({"sub": str(user_id), "email": email, "purpose": "verify_email", "exp": exp},
                      settings.jwt_secret, algorithm="HS256")


def read_verify_token(token: str) -> tuple[int, str] | None:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if claims.get("purpose") != "verify_email":
            return None
        return int(claims["sub"]), claims["email"]
    except (JWTError, KeyError, ValueError):
        return None


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    from app.models import User

    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if claims.get("purpose"):   # a verification link is not a session
            raise err
        uid = int(claims["sub"])
    except (JWTError, KeyError, ValueError):
        raise err
    user = db.get(User, uid)
    if not user:
        raise err
    return user


def active_user(user=Depends(current_user)):
    """Signed in AND onboarding finished. Every feature endpoint uses this; only account/profile/onboarding
    endpoints accept an account that has not finished onboarding (enforced server-side, not just in the UI)."""
    if not user.onboarded:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "onboarding_required")
    return user


def admin_user(user=Depends(current_user)):
    """Admins only. The role is read from the database on every request, so revoking it takes effect at once.
    Granted on the server with `python -m app.tools.admin grant <email>`, never through the API."""
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_only")
    return user
