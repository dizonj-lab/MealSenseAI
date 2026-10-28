"""Audit log: who did what to which record. Written in the same transaction as the change it records."""
from sqlalchemy.orm import Session

from app.models import AuditLog


def log(db: Session, actor_id: int | None, action: str, target_type: str | None = None, target_id=None, **detail) -> None:
    db.add(AuditLog(actor_id=actor_id, action=action, target_type=target_type,
                    target_id=None if target_id is None else str(target_id), detail=detail))
