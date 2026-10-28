"""Marking foods on the photo: a box the user drew becomes an item (classified by the model), and an item without a
box can be given one. Real model, real PostgreSQL."""
import uuid
from pathlib import Path

API = "/api/v1"
FIX = Path(__file__).parent / "fixtures"
PIZZA = {"x": 0.17, "y": 0.16, "w": 0.30, "h": 0.40}    # the pizza slice in multi_food_plate.jpg


def plate(client, h, description=None):
    data = {"description": description} if description else {}
    r = client.post(f"{API}/meals/capture", headers=h, data=data,
                    files={"top": ("plate.jpg", (FIX / "multi_food_plate.jpg").read_bytes(), "image/jpeg")})
    return client.post(f"{API}/meals/analyze", json={"meal_id": r.json()["id"]}, headers=h).json()


def test_a_drawn_box_becomes_a_classified_item(client, auth):
    meal = plate(client, auth)
    before = {f["id"] for f in meal["foods"]}
    r = client.post(f"{API}/meals/{meal['id']}/regions", headers=auth, json={"view": "top", "bbox": PIZZA})
    assert r.status_code == 201, r.text
    new = [f for f in r.json()["foods"] if f["id"] not in before]
    assert len(new) == 1
    f = new[0]
    pred = f["original_prediction"]
    assert f["origin"] == "drawn" and pred["drawn"] and pred["bbox"] == PIZZA and pred["view"] == "top"
    assert len(pred["candidates"]) == 3 and pred["fingerprint"]
    assert "pizza" in [c["label"] for c in pred["candidates"]]            # the model sees what is in the box
    if f["nutrition_key"]:
        assert f["grams"] > 0 and f["portion"]["method"] != "unknown"
    else:
        assert f["label"].startswith("Unidentified food")                 # named from its own top-3 next
    # it survives a re-analysis, like any item the user made
    again = client.post(f"{API}/meals/analyze", json={"meal_id": meal["id"]}, headers=auth).json()
    assert any(x["id"] == f["id"] for x in again["foods"])


def test_an_item_without_a_box_can_be_marked(client, auth):
    meal = plate(client, auth, description="teh tarik")
    drink = next(f for f in meal["foods"] if f["origin"] == "description")
    assert not (drink["original_prediction"] or {}).get("bbox")
    box = {"x": 0.55, "y": 0.6, "w": 0.2, "h": 0.25}
    r = client.put(f"{API}/meals/{meal['id']}/foods/{drink['id']}/region", headers=auth, json={"view": "top", "bbox": box})
    assert r.status_code == 200, r.text
    f = next(x for x in r.json()["foods"] if x["id"] == drink["id"])
    assert f["label"] == drink["label"] and f["original_prediction"]["bbox"] == box   # the name stays


def test_region_validation_and_ownership(client, auth):
    meal = plate(client, auth)
    url = f"{API}/meals/{meal['id']}/regions"
    assert client.post(url, headers=auth, json={"view": "top", "bbox": {"x": 0.1, "y": 0.1, "w": 0.01, "h": 0.3}}).status_code == 422
    assert client.post(url, headers=auth, json={"view": "side", "bbox": PIZZA}).status_code == 422      # no side photo
    assert client.post(url, headers=auth, json={"view": "top", "bbox": {"x": 1.2, "y": 0, "w": 0.2, "h": 0.2}}).status_code == 422
    r = client.post(f"{API}/auth/register", json={"email": f"o{uuid.uuid4().hex[:8]}@test.io", "password": "secret123"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    client.put(f"{API}/users/health-profile", json={}, headers=other)
    assert client.post(url, headers=other, json={"view": "top", "bbox": PIZZA}).status_code == 404
