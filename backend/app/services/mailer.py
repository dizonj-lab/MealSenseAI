"""Send contact-form messages by SMTP (STARTTLS) using the owner's own mail account. Optional: without SMTP settings
the message is only stored in the database (python -m app.services.mailer lists recent ones)."""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger(__name__)


def configured() -> bool:
    return bool(settings.smtp_host and settings.contact_to)


def send_contact(name: str, email: str, topic: str, message: str) -> str:
    if not configured():
        return "not_configured"
    m = EmailMessage()
    m["Subject"] = f"[MealSenseAI contact] {topic}: {name}"
    m["From"] = settings.smtp_from or settings.smtp_user
    m["To"] = settings.contact_to
    m["Reply-To"] = email
    m.set_content(f"From: {name} <{email}>\nTopic: {topic}\n\n{message}\n")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(m)
        return "sent"
    except Exception as e:   # the message is already stored, so a mail failure never loses it
        log.warning("contact email failed: %s", e)
        return "failed"


if __name__ == "__main__":
    from sqlalchemy import select

    from app.core.db import SessionLocal
    from app.models import ContactMessage
    with SessionLocal() as db:
        for c in db.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(50)):
            print(f"#{c.id} {c.created_at:%Y-%m-%d %H:%M} [{c.email_status}] {c.topic} · {c.name} <{c.email}>\n  {c.message}\n")
