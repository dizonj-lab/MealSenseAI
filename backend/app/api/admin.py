"""Admin API: training-data review, contributors, dataset versions, the model gate, model updates, settings, prompts
and the audit log. Every route requires an admin (core/security.admin_user); every change is written to the audit log
in the same transaction."""
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import admin_user
from app.models import AuditLog, DatasetVersion, ModelCandidate, PromptVersion, TrainingSample, User
from app.services import audit, datasets, gate, screening, slm, tuning, vision

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_user)])
now = lambda: datetime.now(timezone.utc)   # noqa: E731


def _aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


CAP_MIN = 20   # the contributor cap applies to foods with at least this many shared examples (screening.py)


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'•' * max(2, len(name) - 1)}@{domain}"


# ------------------------------------------------------------------ overview
@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    week = now() - timedelta(days=7)
    by_status = dict(db.execute(select(TrainingSample.status, func.count()).group_by(TrainingSample.status)).all())
    audit_open = db.scalar(select(func.count()).select_from(TrainingSample).where(
        TrainingSample.status == "passed", TrainingSample.audit, TrainingSample.reviewed_at.is_(None))) or 0
    eligible = db.scalar(select(func.count()).select_from(TrainingSample).join(User, User.id == TrainingSample.user_id)
                         .where(screening.eligible_filter())) or 0
    latest = db.scalar(select(DatasetVersion).where(DatasetVersion.status == "frozen").order_by(DatasetVersion.id.desc()))
    return {
        "received_week": db.scalar(select(func.count()).select_from(TrainingSample).where(TrainingSample.created_at >= week)) or 0,
        "by_status": by_status, "audit_open": audit_open, "eligible": eligible,
        "shared": db.scalar(select(func.count()).select_from(TrainingSample).where(
            TrainingSample.consent_at.is_not(None), TrainingSample.withdrawn_at.is_(None))) or 0,
        "contributors": db.scalar(select(func.count(func.distinct(TrainingSample.user_id)))) or 0,
        "latest_dataset": latest.name if latest else None,
        "live_model": (vision.models().get("classifier") or {}),
        "shadow": vision.shadow_name(),
    }


@router.post("/screen", summary="Run every screening check again over all samples")
def rescreen(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    counts = screening.rescreen_all(db)
    audit.log(db, admin.id, "screening.run", detail_counts=counts)
    db.commit()
    return counts


# ------------------------------------------------------------------ review queue
def _sample(s: TrainingSample, u: User) -> dict:
    return {"id": s.id, "label": s.label, "nutrition_key": s.nutrition_key, "source": s.source,
            "model_label": s.model_label, "model_score": s.model_score, "model_candidates": s.model_candidates,
            "status": s.status, "audit": s.audit, "reasons": s.reasons or [], "bucket": screening.bucket(s.status, s.audit),
            "shared": bool(s.consent_at and not s.withdrawn_at), "withdrawn": bool(s.withdrawn_at),
            "contributor": {"id": u.id, "pseudonym": datasets.pseudonym(u.id), "verified": u.email_verified_at is not None,
                            "status": u.contributor_status, "account_days": (now() - _aware(u.created_at)).days},
            "created_at": s.created_at, "reviewed_at": s.reviewed_at, "review_note": s.review_note,
            "crop_url": f"/api/v1/admin/samples/{s.id}/crop"}


@router.get("/samples")
def samples(queue: str = Query("review", pattern="^(review|audit|flagged|passed|approved|rejected|withdrawn|all)$"),
            reason: str | None = None, label: str | None = None, contributor: int | None = None,
            limit: int = Query(50, le=200), offset: int = 0, db: Session = Depends(get_db)):
    q = select(TrainingSample, User).join(User, User.id == TrainingSample.user_id)
    if queue == "review":   # what needs a person: flagged, plus the open random audit
        q = q.where(TrainingSample.reviewed_at.is_(None), (TrainingSample.status == "flagged")
                    | ((TrainingSample.status == "passed") & TrainingSample.audit))
    elif queue == "audit":
        q = q.where(TrainingSample.status == "passed", TrainingSample.audit, TrainingSample.reviewed_at.is_(None))
    elif queue == "withdrawn":
        q = q.where(TrainingSample.withdrawn_at.is_not(None))
    elif queue != "all":
        q = q.where(TrainingSample.status == queue)
    if label:
        q = q.where(TrainingSample.label == label)
    if contributor:
        q = q.where(TrainingSample.user_id == contributor)
    rows = db.execute(q.order_by(TrainingSample.created_at.desc())).all()
    if reason:
        rows = [(s, u) for s, u in rows if any(r["code"] == reason for r in s.reasons or [])]
    reasons = Counter(r["code"] for s, _ in rows for r in s.reasons or [] if r["severity"] != "info")
    return {"total": len(rows), "items": [_sample(s, u) for s, u in rows[offset:offset + limit]],
            "reasons": [{"code": c, "label": screening.LABELS.get(c, c), "count": n} for c, n in reasons.most_common()]}


@router.get("/samples/{sample_id}/crop")
def sample_crop(sample_id: int, db: Session = Depends(get_db)):
    s = db.get(TrainingSample, sample_id)
    if not s:
        raise HTTPException(404, "Sample not found")
    try:
        img = screening.crop(s.image_path, s.bbox)
    except Exception:   # noqa: BLE001
        raise HTTPException(404, "Photo no longer stored")
    img.thumbnail((480, 480))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


class ReviewIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)
    decision: str = Field(pattern="^(approve|reject)$")
    note: str | None = Field(default=None, max_length=300)


@router.post("/samples/review")
def review(body: ReviewIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(TrainingSample).where(TrainingSample.id.in_(body.ids))))
    for s in rows:
        before = s.status
        s.status = "approved" if body.decision == "approve" else "rejected"
        s.reviewed_by, s.reviewed_at, s.review_note = admin.id, now(), (body.note or "").strip() or None
        audit.log(db, admin.id, f"sample.{body.decision}", "training_sample", s.id, before=before, label=s.label,
                  reasons=[r["code"] for r in s.reasons or []], note=s.review_note)
    db.commit()
    return {"updated": len(rows)}


# ------------------------------------------------------------------ contributors
@router.get("/contributors")
def contributors(db: Session = Depends(get_db)):
    rows = db.execute(select(TrainingSample.user_id, TrainingSample.label, TrainingSample.status, TrainingSample.created_at,
                             TrainingSample.consent_at.is_not(None) & TrainingSample.withdrawn_at.is_(None))).all()
    label_totals, per = Counter(), defaultdict(lambda: {"samples": 0, "shared": 0, "approved": 0, "passed": 0, "flagged": 0,
                                                         "rejected": 0, "pending": 0, "week": 0, "labels": Counter()})
    week = now() - timedelta(days=7)
    for uid, label, status, created, shared in rows:
        p = per[uid]
        p["samples"] += 1
        p[status] = p.get(status, 0) + 1
        p["shared"] += 1 if shared else 0
        p["week"] += 1 if created and _aware(created) >= week else 0
        if shared:
            p["labels"][label] += 1
            label_totals[label] += 1
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(per)))} if per else {}
    out = []
    for uid, p in per.items():
        u = users[uid]
        share = max(((100 * n / label_totals[l], l) for l, n in p["labels"].items() if label_totals[l] >= CAP_MIN),
                    default=(0, None))   # a share of a food with few examples says nothing
        days = (now() - _aware(u.created_at)).days
        decided = p["approved"] + p["passed"] + p["rejected"]
        reject_rate = p["rejected"] / decided if decided else 0
        trust = ("suspended" if u.contributor_status == "suspended" else "new" if days < 3 else
                 "watch" if reject_rate >= 0.2 else "established" if days >= 30 and p["approved"] + p["passed"] >= 10 else "normal")
        out.append({"id": uid, "pseudonym": datasets.pseudonym(uid), "email": _mask(u.email), "verified": u.email_verified_at is not None,
                    "status": u.contributor_status, "consent": u.training_consent, "account_days": days, "trust": trust,
                    "reject_rate": round(reject_rate, 3), "largest_share": {"pct": round(share[0], 1), "label": share[1]},
                    **{k: p[k] for k in ("samples", "shared", "approved", "passed", "flagged", "rejected", "week")}})
    return sorted(out, key=lambda r: (-r["flagged"], -r["samples"]))


class ContributorIn(BaseModel):
    action: str = Field(pattern="^(suspend|reactivate|verify_email)$")
    note: str | None = Field(default=None, max_length=300)


@router.post("/contributors/{user_id}")
def contributor_action(user_id: int, body: ContributorIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "No such contributor")
    if body.action == "verify_email":
        u.email_verified_at = u.email_verified_at or now()
    else:
        u.contributor_status = "suspended" if body.action == "suspend" else "active"
    audit.log(db, admin.id, f"contributor.{body.action}", "user", u.id, pseudonym=datasets.pseudonym(u.id), note=body.note)
    db.commit()
    return {"ok": True, "status": u.contributor_status, "verified": u.email_verified_at is not None}


# ------------------------------------------------------------------ dataset versions
def _version(db: Session, v: DatasetVersion, full: bool = False) -> dict:
    m = v.manifest
    out = {"id": v.id, "name": v.name, "status": v.status, "parent_id": v.parent_id, "notes": v.notes, "created_at": v.created_at,
           "samples": m.get("samples", 0), "labels": len(m.get("per_label", {})), "contributors": len(m.get("contributors", {})),
           "largest_share": m.get("largest_share"), "excluded_contributors": m.get("excluded_contributors", []),
           **datasets.live_state(db, v)}
    if full:
        out |= {"per_label": m.get("per_label", {}), "contributor_counts": m.get("contributors", {}),
                "by_source": m.get("by_source", {}), "base_datasets": m.get("base_datasets", []),
                "screening_settings": m.get("screening_settings", {}),
                "export_command": f"docker compose exec backend python -m app.tools.export_dataset {v.name}"}
    return out


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    return [_version(db, v) for v in db.scalars(select(DatasetVersion).order_by(DatasetVersion.id.desc()))]


@router.get("/datasets/{version_id}")
def get_dataset(version_id: int, db: Session = Depends(get_db)):
    v = db.get(DatasetVersion, version_id)
    if not v:
        raise HTTPException(404, "No such version")
    return _version(db, v, full=True)


class FreezeIn(BaseModel):
    name: str
    notes: str | None = Field(default=None, max_length=500)


@router.post("/datasets", status_code=201)
def freeze_dataset(body: FreezeIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        v = datasets.freeze(db, body.name.strip(), body.notes, admin.id)
    except ValueError as e:
        db.rollback()
        raise HTTPException(422, str(e))
    db.flush()
    audit.log(db, admin.id, "dataset.freeze", "dataset_version", v.name, samples=v.manifest["samples"])
    db.commit()
    return _version(db, v, full=True)


class ExcludeIn(BaseModel):
    contributor_id: int
    note: str | None = Field(default=None, max_length=300)


@router.post("/datasets/{version_id}/exclude", status_code=201)
def exclude(version_id: int, body: ExcludeIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    v = db.get(DatasetVersion, version_id)
    if not v or v.status != "frozen":
        raise HTTPException(404, "No such current version")
    try:
        new = datasets.exclude_contributor(db, v, body.contributor_id, body.note, admin.id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.flush()
    audit.log(db, admin.id, "dataset.exclude_contributor", "dataset_version", new.name, parent=v.name,
              contributor=datasets.pseudonym(body.contributor_id), note=body.note)
    db.commit()
    return _version(db, new, full=True)


# ------------------------------------------------------------------ model gate and model updates
def _candidate(c: ModelCandidate, db: Session) -> dict:
    sh = c.shadow or {}
    total = sh.get("total", 0)
    ds = db.get(DatasetVersion, c.dataset_version_id) if c.dataset_version_id else None
    return {"id": c.id, "name": c.name, "status": c.status, "dataset": ds.name if ds else c.report.get("dataset_version"),
            "gate": c.gate, "report": {k: c.report.get(k) for k in ("live", "candidate", "test_set", "created_at", "tool", "package")},
            "shadow": {"total": total, "agree": sh.get("agree", 0), "agreement_pct": round(100 * sh.get("agree", 0) / total, 1) if total else None,
                       "disagreements": list((sh.get("disagreements") or {}).items())[:10]},
            "blockers": gate.promotion_blockers(c) if c.status in ("candidate", "shadow") else [],
            "package_dir": str(gate.package_dir(c.name)), "note": c.note, "decided_at": c.decided_at, "created_at": c.created_at}


@router.get("/models")
def models(db: Session = Depends(get_db)):
    return {"live": vision.models().get("classifier"), "errors": vision.status().get("error"),
            "updates_dir": str(settings.updates_dir), "package_files": list(gate.PACKAGE_FILES),
            "shadow_requirements": {"min_items": tuning.get("gate.shadow_min_items"),
                                    "min_agreement_pct": tuning.get("gate.shadow_min_agreement_pct")},
            "candidates": [_candidate(c, db) for c in db.scalars(select(ModelCandidate).order_by(ModelCandidate.id.desc()))]}


@router.post("/models", status_code=201, summary="Upload a model package to the model updates location")
async def upload_model(files: list[UploadFile] = File(...), dataset_version: str | None = Form(None),
                       admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    data = {}
    for f in files:
        name = (f.filename or "").rsplit("/", 1)[-1]
        if name in gate.PACKAGE_FILES:
            data[name] = await f.read()
    ds = db.scalar(select(DatasetVersion).where(DatasetVersion.name == dataset_version)) if dataset_version else None
    if dataset_version and not ds:
        raise HTTPException(422, f"No dataset version called {dataset_version}")
    try:
        c = gate.install_package(db, data, admin.id, ds.id if ds else None)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.flush()
    audit.log(db, admin.id, "model.upload", "model_candidate", c.name, gate_ok=c.gate["ok"], dataset=dataset_version)
    db.commit()
    return _candidate(c, db)


class ModelActionIn(BaseModel):
    action: str = Field(pattern="^(shadow|stop_shadow|promote|reject|reevaluate)$")
    note: str | None = Field(default=None, max_length=500)


@router.post("/models/{candidate_id}/action")
def model_action(candidate_id: int, body: ModelActionIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    c = db.get(ModelCandidate, candidate_id)
    if not c:
        raise HTTPException(404, "No such candidate")
    a = body.action
    if a == "reevaluate":   # today's tolerances
        c.gate = gate.evaluate(db, c.report, exclude_id=c.id)
    elif a == "shadow":
        if c.status not in ("candidate",):
            raise HTTPException(422, "Only a candidate can start shadow mode")
        if not c.gate.get("ok"):
            raise HTTPException(422, "Shadow mode needs a passed gate")
        err = vision.set_shadow(gate.package_dir(c.name), c.name)
        if err:
            raise HTTPException(422, f"The package does not load: {err}")
        for other in db.scalars(select(ModelCandidate).where(ModelCandidate.status == "shadow", ModelCandidate.id != c.id)):
            other.status = "candidate"
        c.status = "shadow"
    elif a == "stop_shadow":
        if c.status == "shadow":
            vision.set_shadow(None, None)
            c.status = "candidate"
    elif a == "promote":
        if c.status not in ("candidate", "shadow"):
            raise HTTPException(422, f"A {c.status} model cannot be promoted")
        blockers = gate.promotion_blockers(c)
        if blockers:
            raise HTTPException(422, "Promotion is blocked: " + "; ".join(blockers))
        for other in db.scalars(select(ModelCandidate).where(ModelCandidate.status == "promoted")):
            other.status = "retired"
        if c.status == "shadow":
            vision.set_shadow(None, None)
        c.status = "promoted"
        vision.use_model(gate.package_dir(c.name), c.name)
    elif a == "reject":
        if c.status == "shadow":
            vision.set_shadow(None, None)
        if c.status == "promoted":
            raise HTTPException(422, "Roll back to the built-in model first")
        c.status = "rejected"
    if a in ("promote", "reject"):
        c.decided_by, c.decided_at, c.note = admin.id, now(), body.note
    audit.log(db, admin.id, f"model.{a}", "model_candidate", c.name, note=body.note, gate_ok=c.gate.get("ok"))
    db.commit()
    return _candidate(c, db)


@router.post("/models/use-builtin", summary="Roll back: the built-in model becomes the live model again")
def use_builtin(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    for c in db.scalars(select(ModelCandidate).where(ModelCandidate.status == "promoted")):
        c.status = "retired"
        audit.log(db, admin.id, "model.rollback", "model_candidate", c.name)
    vision.use_model(None, None)
    db.commit()
    return {"live": vision.models().get("classifier")}


# ------------------------------------------------------------------ settings and prompts
@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return {"settings": tuning.describe(db), "slm_models": slm.status(force=True).get("models", [])}


class SettingIn(BaseModel):
    value: object = None


@router.put("/settings/{key}")
def put_setting(key: str, body: SettingIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        before, after = tuning.set_value(db, key, body.value, admin.id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    audit.log(db, admin.id, "setting.change", "setting", key, before=before, after=after)
    db.commit()
    tuning.invalidate()
    return next(s for s in tuning.describe(db) if s["key"] == key)


@router.delete("/settings/{key}")
def reset_setting(key: str, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if key not in tuning.BY_KEY:
        raise HTTPException(404, "Unknown setting")
    before, after = tuning.set_value(db, key, tuning.BY_KEY[key].default, admin.id)
    audit.log(db, admin.id, "setting.reset", "setting", key, before=before, after=after)
    db.commit()
    tuning.invalidate()
    return next(s for s in tuning.describe(db) if s["key"] == key)


def _prompt(db: Session, p: tuning.Prompt) -> dict:
    hist = tuning.prompt_history(db, p.key)
    active = next((h for h in hist if h.active), None)
    return {"key": p.key, "label": p.label, "help": p.help, "default": p.default, "text": active.text if active else p.default,
            "active_version": active.version if active else None, "versions": len(hist)}


@router.get("/prompts")
def prompts(db: Session = Depends(get_db)):
    return [_prompt(db, p) for p in tuning.PROMPTS]


@router.get("/prompts/{key}")
def prompt_detail(key: str, db: Session = Depends(get_db)):
    p = tuning.PROMPT_BY_KEY.get(key)
    if not p:
        raise HTTPException(404, "Unknown prompt")
    return _prompt(db, p) | {"history": [{"version": h.version, "text": h.text, "note": h.note, "active": h.active,
                                          "created_at": h.created_at} for h in tuning.prompt_history(db, key)]}


class PromptIn(BaseModel):
    text: str
    note: str | None = Field(default=None, max_length=300)


@router.post("/prompts/{key}", status_code=201)
def save_prompt(key: str, body: PromptIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        pv = tuning.save_prompt(db, key, body.text, body.note, admin.id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.flush()
    audit.log(db, admin.id, "prompt.save", "prompt", key, version=pv.version, note=pv.note)
    db.commit()
    tuning.invalidate()
    return prompt_detail(key, db)


class ActivateIn(BaseModel):
    version: int | None = None   # None: the built-in default


@router.post("/prompts/{key}/activate")
def activate_prompt(key: str, body: ActivateIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if key not in tuning.PROMPT_BY_KEY:
        raise HTTPException(404, "Unknown prompt")
    try:
        tuning.activate_prompt(db, key, body.version)
    except ValueError as e:
        raise HTTPException(422, str(e))
    audit.log(db, admin.id, "prompt.activate", "prompt", key, version=body.version or "default")
    db.commit()
    tuning.invalidate()
    return prompt_detail(key, db)


# ------------------------------------------------------------------ audit log
@router.get("/audit")
def audit_log(limit: int = Query(100, le=500), offset: int = 0, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)))
    actors = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.actor_id for r in rows if r.actor_id})))}
    def who(r):
        u = actors.get(r.actor_id)
        if not u:
            return "server" if r.actor_id is None else "deleted account"
        return u.email if u.is_admin else datasets.pseudonym(u.id)
    return {"total": db.scalar(select(func.count()).select_from(AuditLog)) or 0,
            "items": [{"id": r.id, "at": r.created_at, "actor": who(r), "action": r.action, "target_type": r.target_type,
                       "target_id": r.target_id, "detail": r.detail} for r in rows]}
