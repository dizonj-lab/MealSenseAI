"""A food with no published GI borrows the GI of its main carbohydrate by fixed rules, labelled as borrowed."""
from app.services import nutrition

API = "/api/v1"


def test_rules_pick_the_staple_and_leave_the_rest_alone():
    by_name = {f["name"]: f["key"] for f in nutrition.all_foods()}
    borrowed = lambda name: (nutrition.gi_info(by_name[name]) or {}).get("borrowed_from")   # noqa: E731
    assert borrowed("Hainanese chicken rice") == "White rice, steamed"
    assert borrowed("Char kway teow") == "Udon (noodle soup)"          # rice noodles are noodles, not rice
    assert borrowed("Roti prata, plain") == "White bread"
    assert borrowed("Teh tarik / teh (condensed milk)").startswith("Soft drink")
    assert borrowed("Sliced fish soup (no noodles)") is None             # "no noodles" is not a staple
    assert borrowed("Cereal prawns") is None and borrowed("Water") is None and borrowed("Coffee, black (no sugar)") is None
    assert borrowed("Chicken breast, grilled") is None                   # nothing to borrow from: still no estimate
    own = nutrition.gi_info(by_name["White rice, steamed"])
    assert own["value"] == 73 and own["borrowed_from"] is None           # a published value is never replaced


def test_meal_glycaemic_load_uses_and_labels_a_borrowed_gi(client, auth):
    m = client.post(f"{API}/meals/capture", headers=auth, data={"description": "chicken rice"}).json()
    m = client.post(f"{API}/meals/analyze", json={"meal_id": m["id"]}, headers=auth).json()
    f = next(x for x in m["foods"] if not x["removed"])
    assert f["nutrition_source"]["gi_borrowed_from"] == "White rice, steamed" and f["nutrition_source"]["glycemic_index"] == 73
    g = m["insights"]["glucose"]
    avail = (f["nutrients"]["carbs_g"] or 0) - (f["nutrients"]["fiber_g"] or 0)
    assert g["glycemic_load"] == round(73 * avail / 100, 1) and g["level"] in ("LOW", "MODERATE", "HIGH")
    assert g["gi_borrowed"] == [{"food": f["label"], "from": "White rice, steamed", "gi": 73}]
    assert any("borrowed from White rice" in r for r in g["reasoning"])
