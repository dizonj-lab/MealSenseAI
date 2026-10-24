from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import active_user, current_user
from app.models import HealthProfile, User
from app.schemas import ProfileIn, UserOut

router = APIRouter(prefix="/users", tags=["users"])
HEALTH_FIELDS = ("diabetes_status", "known_readings", "hba1c", "has_cgm", "clinician_targets")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


class TrainingConsentIn(BaseModel):
    consent: bool


@router.put("/me/training-consent", response_model=UserOut)
def training_consent(body: TrainingConsentIn, user: User = Depends(active_user), db: Session = Depends(get_db)):
    """Opt in/out of exporting your corrected photo regions as training data (memory works either way)."""
    user.training_consent = body.consent
    db.commit()
    db.refresh(user)
    return user


@router.put("/health-profile", response_model=UserOut)
def update_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = body.model_dump()
    if not body.health_consent:  # data minimisation: health details are only stored with consent
        for k in HEALTH_FIELDS:
            data[k] = None
    if user.profile is None:
        user.profile = HealthProfile()
    for k, v in data.items():
        setattr(user.profile, k, v)
    user.onboarded = True
    db.commit()
    db.refresh(user)
    return user


@router.delete("/me", status_code=204)
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
