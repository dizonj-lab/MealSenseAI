from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import active_user, current_user
from app.models import DatasetVersion, HealthProfile, TrainingSample, User
from app.schemas import ProfileIn, UserOut
from app.services import audit, mailer

router = APIRouter(prefix="/users", tags=["users"])
HEALTH_FIELDS = ("diabetes_status", "known_readings", "hba1c", "has_cgm", "clinician_targets")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


class TrainingConsentIn(BaseModel):
    consent: bool


@router.put("/me/training-consent", response_model=UserOut)
def training_consent(body: TrainingConsentIn, user: User = Depends(active_user), db: Session = Depends(get_db)):
    """Opt in/out of sharing your corrected photo regions as training data (memory works either way).

    Opting in shares the corrections you have made so far and those you make from now on. Opting out withdraws all
    of them: they are left out of every dataset version exported from then on."""
    now = datetime.now(timezone.utc)
    mine = TrainingSample.user_id == user.id
    if body.consent and not user.training_consent:
        db.execute(update(TrainingSample).where(mine).values(consent_at=now, withdrawn_at=None))
    elif not body.consent and user.training_consent:
        db.execute(update(TrainingSample).where(mine, TrainingSample.consent_at.is_not(None),
                                                 TrainingSample.withdrawn_at.is_(None)).values(withdrawn_at=now))
    if body.consent != user.training_consent:
        audit.log(db, user.id, "consent.training_on" if body.consent else "consent.training_off", "user", user.id)
    user.training_consent = body.consent
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/training-summary", summary="What you have shared for training, and where it stands")
def training_summary(user: User = Depends(active_user), db: Session = Depends(get_db)):
    from app.services import screening
    rows = db.execute(select(TrainingSample.status, TrainingSample.audit, TrainingSample.withdrawn_at.is_(None), func.count())
                      .where(TrainingSample.user_id == user.id, TrainingSample.consent_at.is_not(None))
                      .group_by(TrainingSample.status, TrainingSample.audit, TrainingSample.withdrawn_at.is_(None))).all()
    shared = accepted = in_review = rejected = withdrawn = 0
    for status, audited, active, n in rows:
        if not active:
            withdrawn += n
            continue
        shared += n
        bucket = screening.bucket(status, audited)
        accepted += n if bucket == "accepted" else 0
        in_review += n if bucket == "in_review" else 0
        rejected += n if bucket == "rejected" else 0
    latest = db.scalar(select(DatasetVersion).where(DatasetVersion.status == "frozen").order_by(DatasetVersion.id.desc()))
    used = 0
    if latest:
        ids = set(latest.manifest.get("sample_ids", []))
        used = sum(1 for (i,) in db.execute(select(TrainingSample.id).where(TrainingSample.user_id == user.id,
                                                                             TrainingSample.withdrawn_at.is_(None))) if i in ids)
    return {"consent": user.training_consent, "email_verified": user.email_verified_at is not None,
            "contributor_status": user.contributor_status, "shared": shared, "accepted": accepted,
            "in_review": in_review, "rejected": rejected, "withdrawn": withdrawn,
            "dataset": {"name": latest.name, "your_samples": used} if latest else None,
            "verification_email": "available" if mailer.configured_smtp() else "not_configured"}


@router.post("/me/verify-email", summary="Send a new email-verification link")
def resend_verification(request: Request, user: User = Depends(current_user)):
    from app.api.auth import base_url, send_verification
    if user.email_verified_at:
        return {"status": "already_verified"}
    status = send_verification(user, base_url(request))
    if status == "failed":
        raise HTTPException(502, "The email could not be sent. Please try again later.")
    return {"status": status}


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
