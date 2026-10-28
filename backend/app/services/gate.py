"""Model gate (Block 5) and model packages (the "model updates location").

A candidate arrives as a package uploaded by an admin: model.onnx, class_mapping.json, model_card.json and the
gate report made offline by ml/evaluation/gate_report.py on the fixed test set. The package is checked (it must
load and be self-consistent) and stored under <model updates dir>/<name>/.

The gate compares candidate and live model in the report: overall top-1 accuracy, and each safety group (rice,
noodles, sweet drinks) where a regression would make users under-count carbohydrate. Every candidate must be
evaluated on the same test set (same SHA-256 as the first report ever registered). A candidate that passes can run
in shadow mode: it classifies every crop beside the live model, unseen by users, and agreement is counted.
Promotion needs a passed gate and enough shadow agreement; it switches the live model at once, without a rebuild.
"Use the built-in model" rolls back. Training never runs from the web.
"""
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ModelCandidate
from app.services import tuning, vision

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,59}$")
PACKAGE_FILES = ("model.onnx", "class_mapping.json", "model_card.json", "report.json")
SAFETY_GROUPS = ("rice", "noodles", "sweet_drinks")
GROUP_LABELS = {"rice": "Rice dishes", "noodles": "Noodle dishes", "sweet_drinks": "Sweet drinks"}


def package_dir(name: str) -> Path:
    return settings.updates_dir / name


def _num(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) else None


def validate_report(report: dict) -> list[str]:
    problems = []
    for side in ("live", "candidate"):
        part = report.get(side)
        if not isinstance(part, dict) or _num(part.get("overall_top1")) is None:
            problems.append(f"report.{side}.overall_top1 is missing")
        elif not isinstance(part.get("groups", {}), dict):
            problems.append(f"report.{side}.groups must be an object")
    ts = report.get("test_set")
    if not isinstance(ts, dict) or not isinstance(ts.get("sha256"), str):
        problems.append("report.test_set.sha256 is missing")
    if not NAME.match(str(report.get("name", ""))):
        problems.append("report.name must be 2-60 letters, digits, dots, dashes or underscores")
    return problems


def evaluate(db: Session, report: dict, exclude_id: int | None = None) -> dict:
    """The gate's checks for one report, with today's tolerances."""
    overall_tol = tuning.get("gate.overall_tolerance_pts")
    safety_tol = tuning.get("gate.safety_tolerance_pts")
    live, cand = report["live"], report["candidate"]
    checks = []

    def check(name, a, b, tol, safety=False):
        if a is None or b is None:
            checks.append({"name": name, "live": a, "candidate": b, "delta_pts": None, "tolerance_pts": tol,
                           "ok": False, "safety": safety, "why": "not measured in the report"})
            return
        delta = round((b - a) * 100, 2)
        checks.append({"name": name, "live": a, "candidate": b, "delta_pts": delta, "tolerance_pts": tol,
                       "ok": delta >= -tol, "safety": safety})

    check("Overall accuracy", _num(live["overall_top1"]), _num(cand["overall_top1"]), overall_tol)
    for g in SAFETY_GROUPS:
        check(f"{GROUP_LABELS[g]} (safety)", _num((live.get("groups") or {}).get(g)),
              _num((cand.get("groups") or {}).get(g)), safety_tol, safety=True)
    first = db.scalar(select(ModelCandidate).where(ModelCandidate.id != (exclude_id or 0)).order_by(ModelCandidate.id))
    ref = (first.report.get("test_set") or {}).get("sha256") if first else report["test_set"]["sha256"]
    same_set = ref == report["test_set"]["sha256"]
    checks.append({"name": "Fixed test set", "live": ref[:12], "candidate": report["test_set"]["sha256"][:12],
                   "delta_pts": None, "tolerance_pts": None, "ok": same_set, "safety": False,
                   "why": None if same_set else "evaluated on a different test set than the first candidate"})
    return {"ok": all(c["ok"] for c in checks), "checks": checks, "evaluated_at": datetime.now(timezone.utc).isoformat()}


def install_package(db: Session, files: dict[str, bytes], actor_id: int, dataset_version_id: int | None) -> ModelCandidate:
    """Store an uploaded package, check it loads, and register it at the gate."""
    missing = [f for f in PACKAGE_FILES if f not in files]
    if missing:
        raise ValueError(f"The package needs {', '.join(missing)}")
    try:
        report = json.loads(files["report.json"])
    except json.JSONDecodeError:
        raise ValueError("report.json is not valid JSON")
    problems = validate_report(report)
    if problems:
        raise ValueError("; ".join(problems))
    name = report["name"]
    if db.scalar(select(ModelCandidate).where(ModelCandidate.name == name)):
        raise ValueError(f"A candidate called {name} already exists")
    dest = package_dir(name)
    tmp = dest.with_name(dest.name + ".uploading")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for f in PACKAGE_FILES:
        (tmp / f).write_bytes(files[f])
    try:
        cls = vision.load_classifier(tmp)
    except Exception as e:   # noqa: BLE001 - the admin sees why
        shutil.rmtree(tmp, ignore_errors=True)
        raise ValueError(f"The model does not load: {e}")
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    report.setdefault("package", {}).update(classes=len(cls["names"]), card_version=cls["card"]["version"])
    c = ModelCandidate(name=name, dataset_version_id=dataset_version_id, report=report, gate=evaluate(db, report),
                       status="candidate", shadow={"total": 0, "agree": 0, "disagreements": {}}, created_by=actor_id)
    db.add(c)
    return c


def promotion_blockers(c: ModelCandidate) -> list[str]:
    out = []
    if not c.gate.get("ok"):
        out.append("the gate's checks did not all pass")
    need, total = tuning.get("gate.shadow_min_items"), c.shadow.get("total", 0)
    if total < need:
        out.append(f"shadow mode has compared {total} of the {need} foods required")
    elif total:
        pct = 100 * c.shadow.get("agree", 0) / total
        if pct < tuning.get("gate.shadow_min_agreement_pct"):
            out.append(f"shadow agreement is {pct:.1f}%, below {tuning.get('gate.shadow_min_agreement_pct'):g}%")
    if not package_dir(c.name).is_dir():
        out.append("its package is missing from the model updates location")
    return out


def record_shadow(db: Session, preds: list[dict]) -> None:
    """Count agreement between the live model and the shadow candidate on this meal's foods."""
    name = vision.shadow_name()
    pairs = [(p.get("model_label"), p.get("shadow_label")) for p in preds if p.get("kind") == "food" and p.get("shadow_label")]
    if not name or not pairs:
        return
    c = db.scalar(select(ModelCandidate).where(ModelCandidate.name == name).with_for_update())
    if not c or c.status != "shadow":
        return
    sh = dict(c.shadow or {})
    dis = dict(sh.get("disagreements") or {})
    for live, cand in pairs:
        sh["total"] = sh.get("total", 0) + 1
        if (live or "").lower() == (cand or "").lower():
            sh["agree"] = sh.get("agree", 0) + 1
        else:
            k = f"{live} → {cand}"
            dis[k] = dis.get(k, 0) + 1
    sh["disagreements"] = dict(sorted(dis.items(), key=lambda kv: -kv[1])[:50])
    c.shadow = sh


def apply_from_db(db: Session) -> None:
    """At startup: load the promoted model (if any) as the live one, and the shadow candidate (if any)."""
    promoted = db.scalar(select(ModelCandidate).where(ModelCandidate.status == "promoted").order_by(ModelCandidate.decided_at.desc()))
    vision.use_model(package_dir(promoted.name) if promoted else None, promoted.name if promoted else None)
    shadow = db.scalar(select(ModelCandidate).where(ModelCandidate.status == "shadow"))
    vision.set_shadow(package_dir(shadow.name) if shadow else None, shadow.name if shadow else None)
