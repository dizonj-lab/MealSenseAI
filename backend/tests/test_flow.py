import pytest
import io
from pathlib import Path

from PIL import Image

FIX = Path(__file__).parent / "fixtures"
API = "/api/v1"


def jpeg(color=(200, 200, 200), size=(400, 300)):
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "JPEG")
    return b.getvalue()


def test_health(client):
    r = client.get(f"{API}/health").json()
    assert r["database"] and r["vision"]


def test_auth(client):
    r = client.post(f"{API}/auth/register", json={"email": "a@b.io", "password": "secret123"})
    assert r.status_code == 201
    assert client.post(f"{API}/auth/register", json={"email": "A@b.io", "password": "secret123"}).status_code == 409
    assert client.post(f"{API}/auth/login", json={"email": "a@b.io", "password": "wrong"}).status_code == 401
    tok = client.post(f"{API}/auth/login", json={"email": "a@b.io", "password": "secret123"}).json()["access_token"]
    me = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {tok}"}).json()
    assert me["email"] == "a@b.io" and me["onboarded"] is False
    assert client.get(f"{API}/users/me").status_code == 401
    assert client.get(f"{API}/users/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_onboarding_consent_minimises(client, auth):
    body = {"age": 40, "diabetes_status": "type2", "hba1c": 7.1, "goals": ["carb_awareness"], "health_consent": False,
            "allergies": ["peanut"], "calorie_goal": 2000, "carb_goal_g": 200}
    me = client.put(f"{API}/users/health-profile", json=body, headers=auth).json()
    assert me["onboarded"] and me["profile"]["diabetes_status"] is None and me["profile"]["hba1c"] is None
    me = client.put(f"{API}/users/health-profile", json={**body, "health_consent": True}, headers=auth).json()
    assert me["profile"]["diabetes_status"] == "type2" and me["profile"]["allergies"] == ["peanut"]


def test_model_loaded_and_taxonomy_aligned(client, auth):
    import json
    from app.core.config import settings
    from app.services import vision
    st = vision.status()
    assert st["available"] and st["models"]["classifier"]["food_classes"] == 320
    tax = json.loads((settings.models_dir / "exp002/class_mapping.json").read_text())
    for name, idx in tax.items():  # every class id resolves to exactly its canonical name
        assert vision.taxonomy_class(idx)["name"] == name
    assert vision.taxonomy_class(320) is None
    ai = client.get(f"{API}/ai/models", headers=auth).json()
    names = [e["name"] for e in ai["experiments"]]
    assert any("reported" in n for n in names) and any("parity" in n for n in names)


def test_top3_confirm_override_on_photo(client, auth):
    r = client.post(f"{API}/meals/capture", headers=auth,
                    files={"top": ("coffee.png", (FIX / "coffee.png").read_bytes(), "image/png")})
    assert r.status_code == 201, r.text
    meal = client.post(f"{API}/meals/analyze", json={"meal_id": r.json()["id"]}, headers=auth).json()
    keys = [s["key"] for s in meal["stages"]]
    assert keys == ["capture", "preprocess", "detect", "classify", "portion", "nutrition", "aggregate",
                    "contextualise", "recommend", "output"]
    top = next(s for s in meal["stages"] if s["key"] == "classify")["per_view"][0]["top_labels"]
    print("top-3:", top)
    assert len(top) == 3 and all("class_id" in t for t in top)
    food = next(f for f in meal["foods"] if f["origin"] == "model")
    pred = food["original_prediction"]
    assert len(pred["candidates"]) == 3 and pred["score_type"].startswith("raw softmax")
    assert food["taxonomy_class"] == pred["candidates"][0]["label"] == "kopi teh milo"
    assert food["nutrition_source"]["match"] in ("exact", "proxy")
    # override with the 2nd candidate: label, taxonomy class and nutrition follow; original prediction kept
    alt = pred["candidates"][1]
    meal2 = client.put(f"{API}/meals/{meal['id']}/foods/{food['id']}", headers=auth,
                       json={"candidate_class_id": alt["class_id"]}).json()
    f2 = next(f for f in meal2["foods"] if f["id"] == food["id"])
    assert f2["taxonomy_class"] == alt["label"] and f2["user_corrected"]
    assert f2["original_prediction"]["candidates"][0]["label"] == "kopi teh milo"
    # add a taxonomy class directly (e.g. from the candidates of an uncertain photo)
    meal3 = client.post(f"{API}/meals/{meal['id']}/foods", headers=auth, json={"candidate_class_id": 63}).json()
    assert any(f["taxonomy_class"] == "chicken rice" and f["nutrition_key"] == "chicken_rice" for f in meal3["foods"])
    assert client.get(f"{API}/taxonomy/search?q=laksa", headers=auth).json()[0]["name"] == "laksa"


def test_unsupported_image_then_manual_and_corrections(client, auth):
    client.put(f"{API}/users/health-profile", headers=auth, json={
        "health_consent": True, "diabetes_status": "type2", "allergies": ["peanut"], "goals": ["carb_awareness"],
        "calorie_goal": 2000, "carb_goal_g": 200, "protein_goal_g": 80})
    meal = client.post(f"{API}/meals/capture", headers=auth, data={"description": "nasi lemak and teh tarik"},
                       files={"top": ("a.jpg", jpeg(), "image/jpeg"), "side": ("b.jpg", jpeg((90, 60, 30)), "image/jpeg")}).json()
    assert len(meal["images"]) == 2
    meal = client.post(f"{API}/meals/analyze", json={"meal_id": meal["id"]}, headers=auth).json()
    mid = meal["id"]
    keys = {f["nutrition_key"] for f in meal["foods"]}
    assert {"nasi_lemak", "teh_tarik"} <= keys
    assert not any(f["origin"] == "model" for f in meal["foods"])  # blank image -> no fabricated recognition
    assert next(s for s in meal["stages"] if s["key"] == "classify")["status"] == "uncertain"
    nl = next(f for f in meal["foods"] if f["nutrition_key"] == "nasi_lemak")
    assert nl["grams"] == 260 and nl["portion"]["uncertainty"] == "high"
    assert abs(nl["nutrients"]["calories_kcal"] - 494.0) < 0.5
    ins = meal["insights"]
    assert ins["glucose"]["level"] in ("LOW", "MODERATE", "HIGH", "UNCERTAIN")
    assert ins["allergy_warnings"] and "peanut" in ins["allergy_warnings"][0]
    assert any(r["tag"] == "drink" for r in ins["recommendations"])
    assert ins["energy"]["goal_progress"]
    kcal0 = meal["totals"]["calories_kcal"]

    # edit portion -> recalculated
    meal = client.put(f"{API}/meals/{mid}/foods/{nl['id']}", json={"grams": 130}, headers=auth).json()
    nl2 = next(f for f in meal["foods"] if f["id"] == nl["id"])
    assert abs(nl2["nutrients"]["calories_kcal"] - 247.0) < 0.5 and nl2["portion"]["method"] == "user_entered"
    assert meal["totals"]["calories_kcal"] < kcal0
    # edit food -> remapped, original preserved
    tt = next(f for f in meal["foods"] if f["nutrition_key"] == "teh_tarik")
    meal = client.put(f"{API}/meals/{mid}/foods/{tt['id']}", json={"nutrition_key": "coffee_black"}, headers=auth).json()
    tt2 = next(f for f in meal["foods"] if f["id"] == tt["id"])
    assert tt2["nutrition_key"] == "coffee_black" and tt2["user_corrected"]
    assert tt2["original_prediction"]["description_text"] == "teh tarik"
    assert not any(r["tag"] == "drink" for r in meal["insights"]["recommendations"])
    # add + remove
    meal = client.post(f"{API}/meals/{mid}/foods", json={"nutrition_key": "broccoli"}, headers=auth).json()
    br = next(f for f in meal["foods"] if f["nutrition_key"] == "broccoli")
    meal = client.post(f"{API}/meals/{mid}/foods", json={"label": "mystery stew"}, headers=auth).json()
    ms = next(f for f in meal["foods"] if f["label"] == "mystery stew")
    assert ms["mapping_quality"] == "none" and "mystery stew" in meal["totals"]["unmapped_items"]
    assert meal["insights"]["glucose"]["level"] == "UNCERTAIN"
    assert client.put(f"{API}/meals/{mid}/confirm", json={}, headers=auth).status_code == 422
    meal = client.delete(f"{API}/meals/{mid}/foods/{ms['id']}", headers=auth).json()
    assert not any(f["label"] == "mystery stew" and not f["removed"] for f in meal["foods"])
    # confirm and history/dashboard
    meal = client.put(f"{API}/meals/{mid}/confirm", json={"meal_type": "lunch"}, headers=auth).json()
    assert meal["status"] == "confirmed" and all(f["confirmed"] for f in meal["foods"] if not f["removed"])
    assert all(f["mapping_quality"] == "exact" for f in meal["foods"] if not f["removed"])
    h = client.get(f"{API}/meals/history", headers=auth).json()
    assert h["meals"][0]["id"] == mid and h["days"]
    d = client.get(f"{API}/dashboard/summary", headers=auth).json()
    assert d["today"]["calories_kcal"] == meal["totals"]["calories_kcal"] and d["recent_meals"]
    ai = client.get(f"{API}/ai/models", headers=auth).json()
    assert ai["corrections"]["edit_portion"] >= 1 and ai["corrections"]["add"] == 2
    assert ai["vision"]["models"][0]["latency"]["count"] >= 1
    # image access is owner-only
    assert client.get(f"{API}/meals/{mid}/images/top", headers=auth).status_code == 200
    other = client.post(f"{API}/auth/register", json={"email": "other@test.io", "password": "secret123"}).json()
    assert client.get(f"{API}/meals/{mid}", headers={"Authorization": f"Bearer {other['access_token']}"}).status_code == 404
    assert client.delete(f"{API}/meals/{mid}", headers=auth).status_code == 204


def test_capture_validation(client, auth):
    assert client.post(f"{API}/meals/capture", headers=auth).status_code == 422
    r = client.post(f"{API}/meals/capture", headers=auth, files={"top": ("x.jpg", b"notanimage", "image/jpeg")})
    assert r.status_code == 422


def test_portion_reference_scaling():
    from app.services import nutrition, portion
    ref = nutrition.get("white_rice")
    g, p = portion.estimate(ref, bbox={"x": 0, "y": 0, "w": 0.5, "h": 0.5}, reference_object="rice_bowl",
                            containers=[{"label": "bowl", "score": 0.9, "bbox": {"x": 0, "y": 0, "w": 0.5, "h": 0.5}}])
    assert p["method"] == "box_area_ratio" and p["uncertainty"] == "medium" and g > ref["default_serving_g"]
    g, p = portion.estimate(ref, bbox={"x": 0, "y": 0, "w": 0.5, "h": 0.5}, area_frac=0.11, has_mask=True,
                            reference_object="rice_bowl",
                            containers=[{"label": "bowl", "score": 0.9, "area_frac": 0.2, "bbox": {"x": 0, "y": 0, "w": 0.5, "h": 0.5}}])
    assert p["method"] == "mask_area_ratio" and g == ref["default_serving_g"]  # 0.11/0.2 = 0.55 = typical fill
    g, _ = portion.estimate(nutrition.get("banana"), instances=2)
    assert g == 2 * nutrition.get("banana")["default_serving_g"]
    g, p = portion.estimate(ref, note="2 bowls")
    assert g == 2 * ref["default_serving_g"] and p["uncertainty"] == "high"


def test_multi_food_plate_items_rename_merge_restore(client, auth):
    r = client.post(f"{API}/meals/capture", headers=auth,
                    files={"top": ("plate.jpg", (FIX / "multi_food_plate.jpg").read_bytes(), "image/jpeg")})
    meal = client.post(f"{API}/meals/analyze", json={"meal_id": r.json()["id"]}, headers=auth).json()
    mid = meal["id"]
    model = [f for f in meal["foods"] if f["origin"] == "model"]
    visible = [f for f in model if not f["removed"]]
    assert len(visible) >= 2, [f["label"] for f in visible]                     # more than one item from one photo
    assert all(f["original_prediction"]["bbox"] for f in visible)                # each item has its own box
    assert len({f["original_prediction"]["region_id"] for f in model}) == len(model)
    named = [f for f in visible if f["nutrition_key"]]
    unknown = [f for f in visible if f["label"].startswith("Unidentified")]
    assert named and unknown                                                     # weak region not forced into a class
    assert client.put(f"{API}/meals/{mid}/confirm", json={}, headers=auth).status_code == 422  # must be named first
    # name the unidentified region from its own top-3, then merge two items, then restore a hidden suggestion
    u = unknown[0]
    meal = client.put(f"{API}/meals/{mid}/foods/{u['id']}", headers=auth,
                      json={"candidate_class_id": u["original_prediction"]["candidates"][0]["class_id"]}).json()
    u2 = next(f for f in meal["foods"] if f["id"] == u["id"])
    assert u2["taxonomy_class"] == u["original_prediction"]["candidates"][0]["label"] and u2["nutrition_key"]
    kcal_before = meal["totals"]["calories_kcal"]
    ids = [f["id"] for f in meal["foods"] if not f["removed"] and f["origin"] == "model"][:2]
    meal = client.post(f"{API}/meals/{mid}/foods/merge", headers=auth, json={"food_ids": ids}).json()
    assert sum(1 for f in meal["foods"] if f["id"] in ids and not f["removed"]) == 1
    kept = next(f for f in meal["foods"] if f["id"] in ids and not f["removed"])
    assert kept["original_prediction"]["merged_from"] and meal["totals"]["calories_kcal"] is not None
    sugg = [f for f in meal["foods"] if f["removed"] and f["original_prediction"] and f["original_prediction"].get("kind") == "suggestion"]
    if sugg:
        meal = client.put(f"{API}/meals/{mid}/foods/{sugg[0]['id']}", headers=auth, json={"restore": True}).json()
        assert not next(f for f in meal["foods"] if f["id"] == sugg[0]["id"])["removed"]
    ai = client.get(f"{API}/ai/models", headers=auth).json()
    assert ai["corrections"].get("merge") == 1
    assert kcal_before is not None


def test_blank_photo_gives_no_items(client, auth):
    meal = client.post(f"{API}/meals/capture", headers=auth, files={"top": ("b.jpg", jpeg((90, 60, 30)), "image/jpeg")}).json()
    meal = client.post(f"{API}/meals/analyze", json={"meal_id": meal["id"]}, headers=auth).json()
    assert not any(f["origin"] == "model" and not f["removed"] for f in meal["foods"])


def test_portion_simulator_glucose_readings_personalised(client, auth):
    client.put(f"{API}/users/health-profile", headers=auth, json={
        "health_consent": True, "diabetes_status": "type1", "goals": ["heart_health"], "weight_kg": 70})
    meal = client.post(f"{API}/meals/capture", headers=auth, data={"description": "chicken rice and teh tarik"}).json()
    meal = client.post(f"{API}/meals/analyze", json={"meal_id": meal["id"]}, headers=auth).json()
    mid, foods = meal["id"], [f for f in meal["foods"] if not f["removed"] and f["nutrition_key"]]
    assert len(foods) == 2
    rice = next(f for f in foods if "rice" in f["label"].lower())
    half = round(rice["grams"] / 2)
    sim = client.post(f"{API}/meals/{mid}/simulate", headers=auth, json={"portions": {str(rice["id"]): half}}).json()
    assert sim["kind"] == "simulated" and sim["simulation_version"]
    o, m = sim["totals"]["original"], sim["totals"]["modified"]
    assert m["carbs_g"] < o["carbs_g"] and sim["totals"]["diff"]["carbs_g"]["pct"] < 0
    assert max(sim["curves"]["original"]) == 100 and max(sim["curves"]["modified"]) < 100
    assert all(lo <= hi for lo, hi in zip(sim["curves"]["modified_low"], sim["curves"]["modified_high"]))
    fr = next(f for f in sim["foods"] if f["id"] == rice["id"])
    assert fr["modified"]["grams"] == half and fr["diff"]["grams"]["pct"] == pytest.approx(-50, abs=1)
    # nothing saved until confirmed
    again = client.get(f"{API}/meals/{mid}", headers=auth).json()
    assert next(f for f in again["foods"] if f["id"] == rice["id"])["grams"] == rice["grams"]
    assert client.post(f"{API}/meals/{mid}/simulate", headers=auth, json={"portions": {"999999": 10}}).status_code == 422
    # personalised insights: type 1 → no dosing; heart-health → sodium vs WHO
    pers = {p["audience"]: p for p in meal["insights"]["personalised"]}
    assert "does not calculate" in pers["Type 1 diabetes"]["detail"] and "WHO" in pers["Heart health"]["detail"]
    # measured readings: mg/dL stored as mmol/L, linked to the meal, validated
    r = client.post(f"{API}/glucose", headers=auth, json={"value": 144, "unit": "mg/dL", "measured_at": "2026-10-23T08:30:00Z",
                                                           "context": "after_meal", "meal_id": mid})
    assert r.status_code == 201 and r.json()["value_mmol"] == pytest.approx(7.99, abs=0.01)
    assert client.post(f"{API}/glucose", headers=auth, json={"value": 90, "unit": "mmol/L", "measured_at": "2026-10-23T08:30:00Z"}).status_code == 422
    rows = client.get(f"{API}/glucose?meal_id={mid}", headers=auth).json()
    assert len(rows) == 1 and rows[0]["kind"] == "measured"
    assert client.delete(f"{API}/glucose/{rows[0]['id']}", headers=auth).status_code == 204
    assert client.get(f"{API}/glucose?meal_id={mid}", headers=auth).json() == []


def test_progress_and_deferred_slm_explanation(client, auth, monkeypatch):
    from app.services import slm
    monkeypatch.setattr(slm, "status", lambda force=False: {"available": True, "selected": "fake-slm", "models": ["fake-slm"], "error": None})
    calls = []
    monkeypatch.setattr(slm, "explain", lambda facts, timeout=None: calls.append(timeout) or slm.Explanation(summary="Mostly carbohydrate from rice."))
    meal = client.post(f"{API}/meals/capture", headers=auth, data={"description": "chicken rice"}).json()
    meal = client.post(f"{API}/meals/analyze", json={"meal_id": meal["id"]}, headers=auth).json()
    ctx = next(s for s in meal["stages"] if s["key"] == "contextualise")
    assert ctx["status"] == "deferred" and ctx["latency_ms"] < 1000 and not calls      # analysis never waits for the SLM
    assert meal["insights"]["explanation"]["source"] == "pending"
    p = client.get(f"{API}/meals/{meal['id']}/progress", headers=auth).json()
    assert p["done"] == p["total"] == 10 and p["current"] is None
    meal = client.post(f"{API}/meals/{meal['id']}/explain", headers=auth).json()
    assert meal["insights"]["explanation"]["text"] == "Mostly carbohydrate from rice." and calls == [90]
