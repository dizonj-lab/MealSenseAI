"""Meal Advisor personality: tone by context, no humour on serious topics, humour never adds facts."""
import re
from pathlib import Path

import pytest

from app.services import persona

API = "/api/v1"
FIX = Path(__file__).parent / "fixtures"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


@pytest.fixture(autouse=True)
def slm_off(monkeypatch):
    from app.services import slm
    monkeypatch.setattr(slm, "status", lambda force=False: {"available": False, "selected": None, "models": [], "error": "off"})


def ask(client, auth, msg, **kw):
    r = client.post(f"{API}/advisor/chat", headers=auth, json={"message": msg, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def meal(client, auth, desc="chicken rice and teh tarik"):
    m = client.post(f"{API}/meals/capture", headers=auth, data={"description": desc}).json()
    return client.post(f"{API}/meals/analyze", json={"meal_id": m["id"]}, headers=auth).json()


def food(client, auth, key):
    return client.get(f"{API}/foods/{key}", headers=auth).json()


def per_serving(rec, n):
    return round((rec["per_100g"][n] or 0) * rec["default_serving_g"] / 100, 1)


def test_openers_never_carry_facts():
    for pool in [*persona.OPENERS.values(), persona.CAREFUL_OPENERS, *persona.CLOSERS.values()]:
        for s in pool:
            assert not re.search(r"\d", s), s   # no numbers in any joke/opener/closer
    assert all(not EMOJI.search(s) for s in persona.CAREFUL_OPENERS)


def test_greeting_and_rotation(client, auth):
    r1 = ask(client, auth, "hi")
    assert r1["tone"] == "playful" and r1["reply"].split("\n")[0] in persona.OPENERS["greet"] and r1["reply"].rstrip().endswith("?")
    r2 = ask(client, auth, "hi", thread_id=r1["thread_id"])
    assert r2["reply"].split("\n")[0] != r1["reply"].split("\n")[0]   # no repeated catchphrase back to back
    assert "doing well" in ask(client, auth, "how are you?")["reply"]


def test_food_identification_is_friendly_and_grounded(client, auth):
    m = meal(client, auth)
    r = ask(client, auth, "What's in my meal?", meal_id=m["id"])
    first = r["reply"].split("\n")[0].lower()
    labels = [f["label"].split(",")[0].split("(")[0].strip().lower() for f in m["foods"] if not f["removed"]]
    assert any(l in first for l in labels) or "plate" in first   # opener names only a food that is in the meal
    assert "missed anything" in r["reply"] or "add or fix" in r["reply"]


def test_multi_turn_food_conversation(client, auth):
    nl, rice = food(client, auth, "nasi_lemak"), food(client, auth, "white_rice")
    r1 = ask(client, auth, "Is nasi lemak healthy?")
    assert "WHO daily limit" in r1["reply"] and "no food is simply" in r1["reply"]
    r2 = ask(client, auth, "What if I skip the rice?", thread_id=r1["thread_id"])
    assert "doesn't split nasi lemak" in r2["reply"].lower() and str(per_serving(nl, "carbs_g")) in r2["reply"] and str(per_serving(rice, "carbs_g")) in r2["reply"]
    r3 = ask(client, auth, "What about adding an egg?", thread_id=r1["thread_id"])
    egg_key = client.get(f"{API}/foods/search?q=egg", headers=auth).json()[0]["key"]
    egg = food(client, auth, egg_key)
    total = round(per_serving(nl, "carbs_g") + per_serving(egg, "carbs_g"), 1)
    assert "Nasi lemak" in r3["reply"] and f"{total} g carbs" in r3["reply"] and "Nothing is saved" in r3["reply"]


def test_missing_food_offers_add_action_without_claiming_it(client, auth):
    m = meal(client, auth)
    r = ask(client, auth, "You missed my egg!", meal_id=m["id"])
    assert "egg" in r["reply"].split("\n")[0].lower() and "Tap **Add egg**" in r["reply"]
    act = r["actions"][0]
    assert act["type"] == "add_food" and act["meal_id"] == m["id"] and "egg" in act["nutrition_key"]
    assert "added" not in r["reply"].lower()   # nothing is claimed as done before the user taps
    before = len([f for f in m["foods"] if not f["removed"]])
    after = client.post(f"{API}/meals/{m['id']}/foods", headers=auth, json={"nutrition_key": act["nutrition_key"]}).json()
    assert len([f for f in after["foods"] if not f["removed"]]) == before + 1


def test_unknown_dish_and_unknown_answers(client, auth):
    r = client.post(f"{API}/meals/capture", headers=auth,
                    files={"top": ("p.jpg", (FIX / "multi_food_plate.jpg").read_bytes(), "image/jpeg")}).json()
    m = client.post(f"{API}/meals/analyze", json={"meal_id": r["id"]}, headers=auth).json()
    if any(not f["nutrition_key"] for f in m["foods"] if not f["removed"]):
        r = ask(client, auth, "What is this mysterious dish?", meal_id=m["id"])
        assert "can't identify" in r["reply"] and "Name it" in r["reply"]
    r = ask(client, auth, "Exactly how much will my glucose rise?", meal_id=m["id"])
    assert r["reply"].split("\n")[0] in persona.OPENERS["cant_know"] and "can't predict" in r["reply"]
    r = ask(client, auth, "Write me a poem about cars")
    assert "don't have information" in r["reply"] and not re.search(r"\d", r["reply"])


def test_missing_nutrition_is_not_invented(client, auth):
    cf = client.post(f"{API}/foods/custom", headers=auth, json={"name": "Auntie bean soup", "serving_g": 300, "per_100g": {"calories_kcal": 60}}).json()
    r = ask(client, auth, "How many carbs in auntie bean soup?")
    assert "180 kcal" in r["reply"] and "g carbs" not in r["reply"]


def test_diabetes_tone_is_careful(client, auth):
    client.put(f"{API}/users/health-profile", headers=auth, json={"health_consent": True, "diabetes_status": "type1", "carb_goal_g": 150})
    m = meal(client, auth)
    for q in ("How many carbohydrates did I have?", "Is this too much rice?", "Can I eat pizza?"):
        r = ask(client, auth, q, meal_id=m["id"] if "pizza" not in q else None)
        assert r["tone"] == "careful", q
        assert r["reply"].split("\n")[0] in persona.CAREFUL_OPENERS and not EMOJI.search(r["reply"].split("\n")[0]), q
    r = ask(client, auth, "Is this too much rice?", meal_id=m["id"])
    rice = next(f for f in m["foods"] if "rice" in f["label"].lower())
    assert f"about {round(rice['nutrients']['carbs_g'])} g of carbohydrate" in r["reply"]


def test_playful_general_food_question(client, auth):
    r = ask(client, auth, "Can I eat pizza?")
    assert r["tone"] == "playful" and r["reply"].split("\n")[0] in [o.replace("{food}", "Pizza") for o in persona.OPENERS["can_eat"]]
    assert "Portion size" in r["reply"]


def test_serious_topics_have_no_humour(client, auth):
    for q in ("I have chest pain after eating", "How many units of insulin should I take?", "Do I have diabetes?"):
        r = ask(client, auth, q)
        assert r["tone"] == "serious" and not EMOJI.search(r["reply"]), q
