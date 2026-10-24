"""Public contact form: stored, emailed only when SMTP is configured, validated, bot- and rate-limited."""
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import ContactMessage
from app.services import mailer

API = "/api/v1"
MSG = {"name": "Ana", "email": "ana@example.com", "topic": "Feedback", "message": "Love the chicken rice estimates!"}


def stored(email):
    with SessionLocal() as db:
        return db.scalars(select(ContactMessage).where(ContactMessage.email == email)).all()


def test_contact_stored_without_smtp(client, monkeypatch):
    monkeypatch.setattr(mailer.settings, "smtp_host", "")
    r = client.post(f"{API}/contact", json={**MSG, "email": "nosmtp@example.com"})
    assert r.status_code == 201 and r.json() == {"ok": True}
    [c] = stored("nosmtp@example.com")
    assert c.email_status == "not_configured" and c.topic == "Feedback"


def test_contact_emailed_to_owner(client, monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout): sent.append(("host", host, port))
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self): pass
        def login(self, u, p): sent.append(("login", u))
        def send_message(self, m): sent.append(("msg", m["To"], m["Reply-To"], m["Subject"]))
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mailer.settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(mailer.settings, "smtp_user", "bot@example.com")
    assert client.post(f"{API}/contact", json={**MSG, "email": "smtp@example.com"}).status_code == 201
    assert ("msg", "joel.dizon@live.com", "smtp@example.com", "[MealSenseAI contact] Feedback: Ana") in sent
    assert stored("smtp@example.com")[0].email_status == "sent"


def test_contact_validation_honeypot_and_rate_limit(client, monkeypatch):
    monkeypatch.setattr(mailer.settings, "smtp_host", "")
    assert client.post(f"{API}/contact", json={**MSG, "email": "not-an-email"}).status_code == 422
    assert client.post(f"{API}/contact", json={**MSG, "message": "hi"}).status_code == 422
    assert client.post(f"{API}/contact", json={**MSG, "email": "bot@example.com", "website": "spam.biz"}).status_code == 201
    assert stored("bot@example.com") == []
    from app.api import contact
    contact._recent.clear()
    codes = [client.post(f"{API}/contact", json={**MSG, "email": "flood@example.com"}).status_code for _ in range(7)]
    assert codes[:5] == [201] * 5 and codes[5:] == [429, 429]
    contact._recent.clear()
