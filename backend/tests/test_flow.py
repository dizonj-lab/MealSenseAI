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


def test_real_model_inference_on_photo(client, auth):
    r = client.post(f"{API}/meals/capture", headers=auth,
                    files={"top": ("coffee.png", (FIX / "coffee.png").read_bytes(), "image/png")})
    assert r.status_code == 201, r.text
    meal = client.post(f"{API}/meals/analyze", json={"meal_id": r.json()["id"]}, headers=auth).json()
    keys = [s["key"] for s in meal["stages"]]
    assert keys == ["capture", "preprocess", "detect", "classify", "portion", "nutrition", "aggregate",
                    "contextualise", "recommend", "output"]
    rec = next(s for s in meal["stages"] if s["key"] == "classify")
    top = rec["per_view"][0]["top_labels"]
    assert top and rec["latency_ms"] > 0
    print("top labels:", top)
    labels = [f["original_prediction"]["model_label"] for f in meal["foods"] if f["origin"] == "model"]
    assert "espresso" in labels  # verified pretrained ImageNet class on the skimage 'coffee' photo
    f = next(f for f in meal["foods"] if f["original_prediction"]["model_label"] == "espresso")
    assert f["original_prediction"]["score_type"].startswith("raw")
    assert f["nutrition_source"]["source"]
    assert client.get(f"{API}/meals/{meal['id']}/images/top_overlay", headers=auth).status_code == 200


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
    assert next(s for s in meal["stages"] if s["key"] == "classify")["status"] == "unsupported"
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
