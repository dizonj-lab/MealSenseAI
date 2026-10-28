"""Training-data governance: admin access, consent, verification, screening, review, dataset versions, the model gate,
admin settings and prompts. Real PostgreSQL, the real EXP-002 model, no mocks."""
import json
import shutil
import uuid
from pathlib import Path

import pytest

from app.core.config import settings
from app.core.security import create_verify_token
from app.services import tuning, vision
from app.tools import admin as admin_tool

API = "/api/v1"
FIX = Path(__file__).parent / "fixtures"
EXP002 = settings.models_dir / "exp002"


def account(client, admin=False):
    email = f"g{uuid.uuid4().hex[:8]}@test.io"
    r = client.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "name": "G"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.put(f"{API}/users/health-profile", json={}, headers=h).status_code == 200
    if admin:
        assert admin_tool.main(["grant", email]) == 0
    return h, email


@pytest.fixture(scope="module")
def admin(client):
    h, _ = account(client, admin=True)
    # every test account is minutes old; the new-account flag is tested on its own below
    assert client.put(f"{API}/admin/settings/screen.new_account_hours", json={"value": 0}, headers=h).status_code == 200
    yield h
    client.delete(f"{API}/admin/settings/screen.new_account_hours", headers=h)


def plate(client, h):
    r = client.post(f"{API}/meals/capture", headers=h,
                    files={"top": ("plate.jpg", (FIX / "multi_food_plate.jpg").read_bytes(), "image/jpeg")})
    return client.post(f"{API}/meals/analyze", json={"meal_id": r.json()["id"]}, headers=h).json()


def sushi(meal):
    return next(f for f in meal["foods"] if f["label"] == "sushi" and not f["removed"])


def verify(client, h, email):
    me = client.get(f"{API}/users/me", headers=h).json()
    return client.post(f"{API}/auth/verify", json={"token": create_verify_token(me["id"], email)})


def test_admin_routes_need_the_admin_role(client, auth, admin):
    assert client.get(f"{API}/admin/overview").status_code == 401
    assert client.get(f"{API}/admin/overview", headers=auth).status_code == 403
    assert client.get(f"{API}/admin/settings", headers=auth).status_code == 403
    assert client.get(f"{API}/admin/overview", headers=admin).status_code == 200
    assert client.get(f"{API}/users/me", headers=admin).json()["is_admin"] is True
    # the role is read on every request: revoking takes effect at once, with the same token
    h, email = account(client, admin=True)
    assert client.get(f"{API}/admin/overview", headers=h).status_code == 200
    assert admin_tool.main(["revoke", email]) == 0
    assert client.get(f"{API}/admin/overview", headers=h).status_code == 403
    assert admin_tool.main(["grant", "nobody@nowhere.io"]) == 1


def test_email_verification_link(client):
    h, email = account(client)
    me = client.get(f"{API}/users/me", headers=h).json()
    assert me["email_verified_at"] is None
    assert client.post(f"{API}/auth/verify", json={"token": "nonsense"}).status_code == 400
    token = create_verify_token(me["id"], email)
    # a verification link is not a session
    assert client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert verify(client, h, email).json()["verified"] is True
    assert client.get(f"{API}/users/me", headers=h).json()["email_verified_at"]
    # bound to the address it was sent to
    assert client.post(f"{API}/auth/verify", json={"token": create_verify_token(me["id"], "other@x.io")}).status_code == 400
    assert client.post(f"{API}/users/me/verify-email", headers=h).json()["status"] == "already_verified"


def test_consent_is_per_sample_and_withdrawable(client, admin):
    h, email = account(client)
    meal = plate(client, h)
    s = sushi(meal)
    client.put(f"{API}/meals/{meal['id']}/foods/{s['id']}", headers=h, json={"confirmed": True})
    summary = client.get(f"{API}/users/me/training-summary", headers=h).json()
    assert summary["shared"] == 0 and not summary["consent"]                     # recorded, but not shared
    client.put(f"{API}/users/me/training-consent", headers=h, json={"consent": True})
    summary = client.get(f"{API}/users/me/training-summary", headers=h).json()
    assert summary["shared"] == 1                                                  # opting in shares what exists
    client.put(f"{API}/users/me/training-consent", headers=h, json={"consent": False})
    summary = client.get(f"{API}/users/me/training-summary", headers=h).json()
    assert summary["shared"] == 0 and summary["withdrawn"] == 1
    log = client.get(f"{API}/admin/audit", headers=admin).json()["items"]
    assert {"consent.training_on", "consent.training_off"} <= {e["action"] for e in log}


def test_screening_flags_an_implausible_low_carb_relabel(client, admin):
    h, email = account(client)
    client.put(f"{API}/users/me/training-consent", headers=h, json={"consent": True})
    meal = plate(client, h)
    s = sushi(meal)
    client.put(f"{API}/meals/{meal['id']}/foods/{s['id']}", headers=h, json={"nutrition_key": "green_salad"})
    me = client.get(f"{API}/users/me", headers=h).json()
    q = client.get(f"{API}/admin/samples", params={"queue": "review", "contributor": me["id"]}, headers=admin).json()
    mine = [i for i in q["items"] if i["model_label"] == "sushi"]
    assert mine, q
    codes = {r["code"] for r in mine[0]["reasons"]}
    assert {"implausible_label", "lowers_carbs"} <= codes and mine[0]["status"] == "flagged"
    assert client.get(mine[0]["crop_url"].replace("/api/v1", API), headers=admin).headers["content-type"] == "image/jpeg"
    # a person decides; the decision is audited
    r = client.post(f"{API}/admin/samples/review", headers=admin, json={"ids": [mine[0]["id"]], "decision": "reject", "note": "not salad"})
    assert r.json()["updated"] == 1
    assert client.get(f"{API}/users/me/training-summary", headers=h).json()["rejected"] == 1
    assert any(e["action"] == "sample.reject" for e in client.get(f"{API}/admin/audit", headers=admin).json()["items"])


def test_duplicates_and_new_accounts(client, admin):
    h, email = account(client)
    client.put(f"{API}/users/me/training-consent", headers=h, json={"consent": True})
    for _ in range(2):   # the same photo and label twice
        meal = plate(client, h)
        client.put(f"{API}/meals/{meal['id']}/foods/{sushi(meal)['id']}", headers=h, json={"confirmed": True})
    me = client.get(f"{API}/users/me", headers=h).json()
    rows = client.get(f"{API}/admin/samples", params={"queue": "all", "contributor": me["id"]}, headers=admin).json()["items"]
    assert sorted(r["status"] for r in rows)[-1] == "rejected"                 # the later copy
    assert any(r["code"] == "duplicate" for x in rows for r in x["reasons"])
    assert any(r["code"] == "self_confirmation" for x in rows for r in x["reasons"])   # noted, not flagged
    client.put(f"{API}/admin/settings/screen.new_account_hours", json={"value": 72}, headers=admin)
    client.post(f"{API}/admin/screen", headers=admin)
    rows = client.get(f"{API}/admin/samples", params={"queue": "all", "contributor": me["id"]}, headers=admin).json()["items"]
    assert any(r["code"] == "new_account" for x in rows for r in x["reasons"])
    client.put(f"{API}/admin/settings/screen.new_account_hours", json={"value": 0}, headers=admin)
    client.post(f"{API}/admin/screen", headers=admin)


def test_dataset_version_freeze_exclude_and_export(client, admin, tmp_path):
    contributors = []
    for _ in range(2):
        h, email = account(client)
        verify(client, h, email)
        client.put(f"{API}/users/me/training-consent", headers=h, json={"consent": True})
        meal = plate(client, h)
        client.put(f"{API}/meals/{meal['id']}/foods/{sushi(meal)['id']}", headers=h, json={"confirmed": True})
        contributors.append((h, client.get(f"{API}/users/me", headers=h).json()["id"]))
    for _, uid in contributors:   # the two crops are the same photo from two accounts: a person approves them
        ids = [i["id"] for i in client.get(f"{API}/admin/samples", params={"queue": "all", "contributor": uid},
                                           headers=admin).json()["items"]]
        client.post(f"{API}/admin/samples/review", headers=admin, json={"ids": ids, "decision": "approve"})
    name = f"T-{uuid.uuid4().hex[:6]}"
    r = client.post(f"{API}/admin/datasets", headers=admin, json={"name": name, "notes": "test"})
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["samples"] >= 2 and v["contributors"] >= 2 and v["base_datasets"]
    assert client.post(f"{API}/admin/datasets", headers=admin, json={"name": name}).status_code == 422   # names are unique
    # roll back one contributor: a new version supersedes this one
    h0, uid0 = contributors[0]
    r = client.post(f"{API}/admin/datasets/{v['id']}/exclude", headers=admin, json={"contributor_id": uid0, "note": "test"})
    new = r.json()
    assert r.status_code == 201 and new["name"] == f"{name}-r1" and new["samples"] == v["samples"] - 1
    assert next(d for d in client.get(f"{API}/admin/datasets", headers=admin).json() if d["id"] == v["id"])["status"] == "superseded"
    # a withdrawal after freezing is honoured by the export
    h1, uid1 = contributors[1]
    client.put(f"{API}/users/me/training-consent", headers=h1, json={"consent": False})
    assert client.get(f"{API}/admin/datasets/{new['id']}", headers=admin).json()["withdrawn_since"] == 1
    from app.tools.export_dataset import export
    summary = export(new["name"], tmp_path)
    assert summary["withdrawn_since_freeze"] == 1 and summary["samples"] == new["samples"] - 1
    assert (tmp_path / "manifest.csv").exists()


def test_settings_validate_and_apply(client, admin):
    r = client.put(f"{API}/admin/settings/vision.unknown_min", json={"value": 3}, headers=admin)
    assert r.status_code == 422 and "between" in r.json()["detail"]
    assert client.put(f"{API}/admin/settings/no.such", json={"value": 1}, headers=admin).status_code == 422
    r = client.put(f"{API}/admin/settings/slm.enabled", json={"value": False}, headers=admin)
    assert r.json()["value"] is False and r.json()["overridden"]
    assert tuning.get("slm.enabled") is False
    r = client.delete(f"{API}/admin/settings/slm.enabled", headers=admin)
    assert r.json()["value"] is True and not r.json()["overridden"]
    assert any(e["action"] == "setting.change" and e["target_id"] == "slm.enabled"
               for e in client.get(f"{API}/admin/audit", headers=admin).json()["items"])


def test_prompts_are_versioned(client, admin):
    key = "meal.explanation"
    default = tuning.PROMPT_BY_KEY[key].default
    r = client.post(f"{API}/admin/prompts/{key}", headers=admin, json={"text": "Explain the meal kindly. Use only the numbers given.", "note": "v1"})
    assert r.status_code == 201 and r.json()["active_version"] == 1
    assert tuning.prompt(key).startswith("Explain the meal kindly")
    client.post(f"{API}/admin/prompts/{key}", headers=admin, json={"text": "Second wording, still only the given numbers."})
    r = client.post(f"{API}/admin/prompts/{key}/activate", headers=admin, json={"version": 1}).json()
    assert r["active_version"] == 1 and len(r["history"]) == 2
    r = client.post(f"{API}/admin/prompts/{key}/activate", headers=admin, json={"version": None}).json()
    assert r["active_version"] is None and tuning.prompt(key) == default
    assert client.post(f"{API}/admin/prompts/{key}", headers=admin, json={"text": "short"}).status_code == 422


def package(tmp: Path, name: str, live: float, cand: float, rice: float, sha="a" * 64) -> dict:
    """A candidate package: the EXP-002 model itself, with a gate report."""
    for f in ("model.onnx", "class_mapping.json", "model_card.json"):
        shutil.copy(EXP002 / f, tmp / f)
    report = {"name": name, "test_set": {"sha256": sha, "images": 100},
              "live": {"overall_top1": live, "groups": {"rice": 0.88, "noodles": 0.83, "sweet_drinks": 0.9}},
              "candidate": {"overall_top1": cand, "groups": {"rice": rice, "noodles": 0.83, "sweet_drinks": 0.9}}}
    (tmp / "report.json").write_text(json.dumps(report))
    return {f: (f, (tmp / f).read_bytes()) for f in ("model.onnx", "class_mapping.json", "model_card.json", "report.json")}


def upload(client, admin, files):
    return client.post(f"{API}/admin/models", headers=admin, files=[("files", v) for v in files.values()])


def test_model_gate_shadow_promote_and_rollback(client, admin, tmp_path):
    settings.model_updates_dir = tmp_path / "models"
    try:
        # a safety regression (rice) fails the gate even with better overall accuracy
        bad = upload(client, admin, package(tmp_path, f"C-{uuid.uuid4().hex[:5]}", 0.84, 0.86, rice=0.80)).json()
        assert bad["gate"]["ok"] is False and any(c["safety"] and not c["ok"] for c in bad["gate"]["checks"])
        assert client.post(f"{API}/admin/models/{bad['id']}/action", headers=admin, json={"action": "shadow"}).status_code == 422
        # a broken package is refused
        files = package(tmp_path, "C-broken", 0.84, 0.85, rice=0.89)
        files["class_mapping.json"] = ("class_mapping.json", b'{"a": 0}')
        assert "does not load" in upload(client, admin, files).json()["detail"]
        # a good one passes, shadows the live model (the same model: full agreement), and is promoted
        good = upload(client, admin, package(tmp_path, f"C-{uuid.uuid4().hex[:5]}", 0.84, 0.85, rice=0.89)).json()
        assert good["gate"]["ok"] is True
        r = client.post(f"{API}/admin/models/{good['id']}/action", headers=admin, json={"action": "promote"})
        assert r.status_code == 422 and "shadow" in r.json()["detail"]
        assert client.post(f"{API}/admin/models/{good['id']}/action", headers=admin, json={"action": "shadow"}).json()["status"] == "shadow"
        h, _ = account(client)
        plate(client, h)
        cand = next(c for c in client.get(f"{API}/admin/models", headers=admin).json()["candidates"] if c["id"] == good["id"])
        assert cand["shadow"]["total"] >= 1 and cand["shadow"]["agreement_pct"] == 100.0
        client.put(f"{API}/admin/settings/gate.shadow_min_items", json={"value": 1}, headers=admin)
        r = client.post(f"{API}/admin/models/{good['id']}/action", headers=admin, json={"action": "promote", "note": "ok"})
        assert r.status_code == 200, r.text
        live = client.get(f"{API}/admin/models", headers=admin).json()["live"]
        assert live["promoted"] == good["name"]
        meal = plate(client, h)   # the promoted package now serves recognition
        assert any(f["label"] == "sushi" for f in meal["foods"])
        live = client.post(f"{API}/admin/models/use-builtin", headers=admin).json()["live"]
        assert live["promoted"] is None
        # a report on a different test set cannot pass
        other = upload(client, admin, package(tmp_path, f"C-{uuid.uuid4().hex[:5]}", 0.84, 0.85, rice=0.89, sha="b" * 64)).json()
        assert next(c for c in other["gate"]["checks"] if c["name"] == "Fixed test set")["ok"] is False
    finally:
        client.delete(f"{API}/admin/settings/gate.shadow_min_items", headers=admin)
        vision.set_shadow(None, None)
        vision.use_model(None, None)
        settings.model_updates_dir = None
