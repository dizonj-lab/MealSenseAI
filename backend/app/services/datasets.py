"""Dataset versions (Block 4): freeze the eligible user samples for one training cycle.

Freezing first re-runs every screening check, then takes the eligible samples (screening.eligible_filter) and writes
a manifest: sample ids, counts per food, contributors as pseudonyms, the largest share any one contributor has of any
food, and the screening settings in force. The base datasets (Food-101, FoodSG-233) are fixed and never mixed with
user data. A version never changes; removing a contributor's samples creates a new version that supersedes it.
Withdrawals after freezing are honoured at export time (python -m app.tools.export_dataset <version>).
"""
import hashlib
import re
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DatasetVersion, TrainingSample, User
from app.services import screening, tuning

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,59}$")
BASE = ["Food-101 (ETH Zürich)", "FoodSG-233 (NUS)"]


def pseudonym(user_id: int) -> str:
    """Stable, not reversible without the server's secret; the same in manifests, exports and the admin pages."""
    return "u·" + hashlib.sha256(f"{settings.jwt_secret}:contributor:{user_id}".encode()).hexdigest()[:6]


def _manifest(samples: list[TrainingSample]) -> dict:
    per_label = Counter(s.label for s in samples)
    per_user_label = defaultdict(Counter)
    for s in samples:
        per_user_label[s.label][s.user_id] += 1
    largest = max(((100 * n / per_label[label], label) for label, users in per_user_label.items()
                   for n in users.values() if per_label[label] >= 20), default=(0.0, None))   # as the contributor cap
    contributors = Counter(s.user_id for s in samples)
    return {
        "sample_ids": sorted(s.id for s in samples),
        "samples": len(samples),
        "per_label": dict(per_label.most_common()),
        "contributors": {pseudonym(u): n for u, n in contributors.most_common()},
        "largest_share": {"pct": round(largest[0], 1), "label": largest[1]},
        "weights": {str(s.id): 0.5 for s in samples if any(r["code"] == "self_confirmation" for r in s.reasons or [])},
        "by_source": dict(Counter(s.source for s in samples)),
        "base_datasets": BASE,
        "screening_settings": {k: tuning.get(k) for k in tuning.BY_KEY if k.startswith("screen.")},
    }


def freeze(db: Session, name: str, notes: str | None, actor_id: int) -> DatasetVersion:
    if not NAME.match(name or ""):
        raise ValueError("A name is 2-60 letters, digits, dots, dashes or underscores, e.g. EXP-003")
    if db.scalar(select(DatasetVersion).where(DatasetVersion.name == name)):
        raise ValueError(f"A version called {name} already exists")
    screening.rescreen_all(db)
    db.flush()
    samples = list(db.scalars(select(TrainingSample).join(User, User.id == TrainingSample.user_id)
                              .where(screening.eligible_filter()).order_by(TrainingSample.id)))
    if not samples:
        raise ValueError("No samples are eligible yet: they need consent, a verified email, and approval or a clean pass")
    v = DatasetVersion(name=name, status="frozen", created_by=actor_id, notes=(notes or "").strip()[:500] or None,
                       manifest=_manifest(samples))
    db.add(v)
    return v


def exclude_contributor(db: Session, v: DatasetVersion, user_id: int, note: str | None, actor_id: int) -> DatasetVersion:
    """Roll back one contributor: a new version without their samples supersedes this one."""
    ids = set(v.manifest.get("sample_ids", []))
    rows = list(db.scalars(select(TrainingSample).where(TrainingSample.id.in_(ids)).order_by(TrainingSample.id)))
    if not any(s.user_id == user_id for s in rows):
        raise ValueError("That contributor has no samples in this version")
    keep = [s for s in rows if s.user_id != user_id]
    n = 1
    while db.scalar(select(DatasetVersion).where(DatasetVersion.name == f"{v.name}-r{n}")):
        n += 1
    new = DatasetVersion(name=f"{v.name}-r{n}", status="frozen", parent_id=v.id, created_by=actor_id,
                         notes=f"{v.name} without {pseudonym(user_id)}" + (f": {note.strip()[:300]}" if note and note.strip() else ""),
                         manifest=_manifest(keep) | {"excluded_contributors": v.manifest.get("excluded_contributors", []) + [pseudonym(user_id)]})
    v.status = "superseded"
    db.add(new)
    return new


def live_state(db: Session, v: DatasetVersion) -> dict:
    """What an export of this version would contain today: samples withdrawn or deleted since freezing drop out."""
    ids = v.manifest.get("sample_ids", [])
    rows = {s.id: s for s in db.scalars(select(TrainingSample).where(TrainingSample.id.in_(ids)))} if ids else {}
    gone = [i for i in ids if i not in rows]
    withdrawn = [i for i, s in rows.items() if s.withdrawn_at]
    return {"exportable": len(ids) - len(gone) - len(withdrawn), "withdrawn_since": len(withdrawn), "deleted_since": len(gone)}
