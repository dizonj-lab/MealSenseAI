"""Screening of labelled photo samples before they can reach a training set (protection against dataset poisoning).

Every sample is checked when it is recorded, and again in a batch (admin "Run checks", and before a dataset version
is frozen), because some checks need the whole pool. Each check adds a reason:

  reject  removes it automatically (an exact or near copy of the same person's own sample, a missing photo)
  flag    sends it to a person for review (implausible label, carbohydrate safety, near-identical photos from
          other accounts, a repeated pattern, no food seen, a new account, a contributor over the cap or the
          weekly limit, an outlier within its food)
  info    noted, not acted on (a "confirmation" that only accepted the model's own guess)

A sample that passed every check may still be picked for the random audit. An admin's decision (approve / reject)
is final until the label changes. Thresholds are admin settings (services/tuning.py, "Training data checks").

Eligible for a dataset version: shared with consent and not withdrawn, from a verified, active contributor, and
approved, or passed and not awaiting audit.
"""
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import TrainingSample, User
from app.services import nutrition, tuning

PAD = 0.12          # the same padding the app classifies crops with
BUCKETS = {"approved": "accepted", "passed": "accepted", "flagged": "in_review", "pending": "in_review", "rejected": "rejected"}
LABELS = {
    "missing_image": "Photo missing",
    "duplicate": "Duplicate of own sample",
    "near_duplicate": "Same photo as another account",
    "repeated_pattern": "Repeated pattern",
    "no_food_seen": "No food seen",
    "implausible_label": "Implausible label",
    "lowers_carbs": "Carbohydrate safety",
    "new_account": "New account",
    "contributor_cap": "Contributor cap",
    "high_volume": "Weekly limit",
    "outlier": "Outlier in its food",
    "self_confirmation": "Confirmed the model's own guess",
    "random_audit": "Random audit",
}


def bucket(status: str, audit: bool) -> str:
    """How a sample's state reads to its contributor: accepted, in review or rejected."""
    if status == "passed" and audit:
        return "in_review"
    return BUCKETS.get(status, "in_review")


def crop(path: str, bbox: dict | None) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if not bbox:
        return img
    W, H = img.size
    x1, y1 = max(0.0, bbox["x"] - PAD * bbox["w"]), max(0.0, bbox["y"] - PAD * bbox["h"])
    x2, y2 = min(1.0, bbox["x"] + bbox["w"] * (1 + PAD)), min(1.0, bbox["y"] + bbox["h"] * (1 + PAD))
    return img.crop((round(x1 * W), round(y1 * H), round(x2 * W), round(y2 * H)))


def dhash(img: Image.Image) -> str:
    """64-bit difference hash: survives resizing, recompression and small edits, so re-uploads still match."""
    g = np.asarray(img.convert("L").resize((9, 8), Image.Resampling.LANCZOS), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return f"{int(''.join('1' if b else '0' for b in bits), 2):016x}"


def distance(a: str | None, b: str | None) -> int:
    return 64 if not a or not b else (int(a, 16) ^ int(b, 16)).bit_count()


def _reason(code: str, severity: str, detail: str) -> dict:
    return {"code": code, "label": LABELS[code], "severity": severity, "detail": detail}


def fingerprint_hashes(s: TrainingSample) -> bool:
    """Compute the crop's hashes once. False when the photo is gone."""
    if s.image_sha256 and s.phash:
        return True
    p = Path(s.image_path)
    if not p.exists():
        return False
    try:
        c = crop(str(p), s.bbox)
    except Exception:   # noqa: BLE001 - an unreadable file is the same as a missing one here
        return False
    s.image_sha256 = hashlib.sha256(c.tobytes() + repr(c.size).encode()).hexdigest()
    s.phash = dhash(c)
    return True


def _carbs(key: str | None) -> float | None:
    ref = nutrition.get(key) if key else None
    return (ref or {}).get("per_100g", {}).get("carbs_g")


def sample_reasons(db: Session, s: TrainingSample, user: User, pool: list[TrainingSample] | None = None) -> list[dict]:
    """The checks that look at one sample (with the other samples for duplicates)."""
    if not fingerprint_hashes(s):
        return [_reason("missing_image", "reject", "The photo for this sample is no longer stored.")]
    out = []
    bits = tuning.get("screen.near_duplicate_bits")
    others = pool if pool is not None else list(db.scalars(select(TrainingSample).where(
        TrainingSample.id != s.id, TrainingSample.status != "rejected", TrainingSample.phash.is_not(None))))
    same_photo = [o for o in others if o.id != s.id and o.status != "rejected"
                  and (o.image_sha256 == s.image_sha256 or distance(o.phash, s.phash) <= bits)]
    own_earlier = [o for o in same_photo if o.user_id == s.user_id and o.label == s.label and (o.id or 0) < (s.id or 0)]
    if own_earlier:
        out.append(_reason("duplicate", "reject", f"Same photo and label as sample #{own_earlier[0].id}."))
    foreign = [o for o in same_photo if o.user_id != s.user_id]
    if foreign:
        same_label_accounts = {o.user_id for o in foreign if o.label == s.label} | {s.user_id}
        if len(same_label_accounts) >= tuning.get("screen.repeat_accounts"):
            out.append(_reason("repeated_pattern", "flag", f"Near-identical crops labelled \"{s.label}\" from "
                               f"{len(same_label_accounts)} accounts: possibly a planted pattern."))
        else:
            out.append(_reason("near_duplicate", "flag", f"Matches a photo from {len({o.user_id for o in foreign})} other account(s)."))
    if s.bbox is None and s.model_score is not None and s.model_score < 0.15:
        out.append(_reason("no_food_seen", "flag", f"The model saw no food it knows in this photo ({s.model_score:.0%})."))
    cands = s.model_candidates or []
    top = [(c.get("label") or "").lower() for c in cands]
    corrected = s.source in ("corrected", "named") and s.model_label and s.label.lower() != (s.model_label or "").lower()
    if corrected and (s.model_score or 0) >= tuning.get("screen.implausible_min_score") and s.label.lower() not in top:
        out.append(_reason("implausible_label", "flag", f"The model said {s.model_label} at {s.model_score:.0%}; "
                           f"\"{s.label}\" is not among its top {len(top) or 3}."))
    if corrected:
        model_key = next((c.get("nutrition_key") for c in cands if (c.get("label") or "").lower() == s.model_label.lower()), None)
        before = _carbs(model_key or nutrition.lookup(s.model_label)[0])
        after = _carbs(s.nutrition_key)
        if before is not None and after is not None and before >= 15 and after < tuning.get("screen.lowers_carbs_ratio") * before:
            out.append(_reason("lowers_carbs", "flag", f"Relabels {before:g} g carbohydrate per 100 g as {after:g} g: "
                               "if wrong, the model would under-report carbohydrate."))
    created = user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=timezone.utc)
    hours = tuning.get("screen.new_account_hours")
    if hours and datetime.now(timezone.utc) - created < timedelta(hours=hours):
        out.append(_reason("new_account", "flag", f"Account is less than {hours} hours old."))
    if s.source == "confirmed" and (s.model_label or "").lower() == s.label.lower():
        out.append(_reason("self_confirmation", "info", "The person accepted the model's own guess; it teaches the model little."))
    return out


def _decide(s: TrainingSample, reasons: list[dict]) -> None:
    s.reasons = reasons
    s.screened_at = datetime.now(timezone.utc)
    rate = tuning.get("screen.audit_rate_pct")
    s.audit = int(hashlib.sha256(f"audit:{s.id}".encode()).hexdigest(), 16) % 10000 < rate * 100
    if s.reviewed_at:   # a person's decision stands
        return
    sev = {r["severity"] for r in reasons}
    s.status = "rejected" if "reject" in sev else "flagged" if "flag" in sev else "passed"


def screen_one(db: Session, s: TrainingSample, user: User) -> None:
    """Checks at the moment a sample is recorded (the batch checks run with rescreen_all)."""
    db.flush()   # the sample needs its id for the audit pick and the duplicate order
    _decide(s, sample_reasons(db, s, user))


def rescreen_all(db: Session) -> dict:
    """Every check, including those that need the whole pool. Returns counts by status."""
    samples = list(db.scalars(select(TrainingSample).order_by(TrainingSample.id)))
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_({s.user_id for s in samples})))} if samples else {}
    for s in samples:
        fingerprint_hashes(s)
    shared = [s for s in samples if s.consent_at and not s.withdrawn_at]
    reasons = {s.id: sample_reasons(db, s, users[s.user_id], pool=[o for o in samples if o.phash]) for s in samples}
    # contributor cap: one person's share of a food's shared samples
    cap = tuning.get("screen.contributor_cap_pct")
    by_label = defaultdict(list)
    for s in shared:
        if not any(r["severity"] == "reject" for r in reasons[s.id]):
            by_label[s.label].append(s)
    for label, group in by_label.items():
        if len(group) < 20:
            continue
        counts = defaultdict(int)
        for s in group:
            counts[s.user_id] += 1
        for s in group:
            share = 100 * counts[s.user_id] / len(group)
            if share > cap:
                reasons[s.id].append(_reason("contributor_cap", "flag", f"This contributor supplied {share:.0f}% of "
                                             f"\"{label}\" (cap {cap:g}%)."))
    # weekly volume per contributor
    limit = tuning.get("screen.weekly_limit")
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent = defaultdict(int)
    for s in samples:
        if s.created_at and (s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=timezone.utc)) >= week_ago:
            recent[s.user_id] += 1
    for s in samples:
        if recent[s.user_id] > limit:
            reasons[s.id].append(_reason("high_volume", "flag", f"{recent[s.user_id]} samples in 7 days (limit {limit})."))
    # outliers: far from the average fingerprint of their food
    threshold = tuning.get("screen.outlier_cosine")
    for label, group in by_label.items():
        fps = [g for g in group if g.fingerprint]
        if len(fps) < 8 or len({len(g.fingerprint) for g in fps}) != 1:
            continue
        M = np.array([g.fingerprint for g in fps], dtype=np.float32)
        M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
        centre = M.mean(axis=0)
        centre /= np.linalg.norm(centre) + 1e-9
        for g, sim in zip(fps, M @ centre):
            if sim < threshold:
                reasons[g.id].append(_reason("outlier", "flag", f"Similarity {sim:.2f} to the average \"{label}\" "
                                             f"(threshold {threshold:g})."))
    for s in samples:
        _decide(s, reasons[s.id])
    out = defaultdict(int)
    for s in samples:
        out[s.status] += 1
    return dict(out) | {"audit": sum(1 for s in samples if s.audit and s.status == "passed" and not s.reviewed_at)}


def eligible_filter():
    """SQL conditions for samples that may enter a dataset version (join TrainingSample with User)."""
    return and_(TrainingSample.consent_at.is_not(None), TrainingSample.withdrawn_at.is_(None),
                User.email_verified_at.is_not(None), User.contributor_status == "active",
                or_(TrainingSample.status == "approved",
                    and_(TrainingSample.status == "passed", TrainingSample.audit.is_(False))))
