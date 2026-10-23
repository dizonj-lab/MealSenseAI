"""Forecast model properties: physics, timing, safety cautions and advisory."""
from types import SimpleNamespace

from app.services import forecast, insights, nutrition

API = "/api/v1"


def profile(**kw):
    base = dict(weight_kg=70, diabetes_status=None, goals=[], calorie_goal=None, carb_goal_g=None,
                protein_goal_g=None, diet_preferences=[], allergies=[])
    return SimpleNamespace(**{**base, **kw})


def meal(*items):
    foods = [{"label": nutrition.get(k)["name"], "grams": g, "nutrition_key": k, "nutrients": nutrition.compute(k, g)}
             for k, g in items]
    t, ins = insights.core(foods, profile())
    return foods, t, ins


def walk(start, dur=20, act="brisk_walk", inten="moderate"):
    return {"activity": act, "intensity": inten, "start_min": start, "duration_min": dur}


def test_energy_follows_met_physics():
    foods, t, ins = meal(("nasi_lemak", 260))
    r = forecast.forecast(foods, t, ins, profile(weight_kg=80), [walk(30, 60, "running", "moderate")])
    s = r["scenarios"][0]
    assert s["exercise_kcal"] == round(8.3 * 80 * 1.0, 1)                  # E = MET x kg x h
    assert s["net_extra_kcal"] == round((8.3 - 1.5) * 80 * 1.0, 1)        # minus desk-work baseline
    assert s["cho_oxidised_g"] == round(8.3 * 80 * 0.65 / 4, 1)           # f_CHO 0.65 at 6-9 MET, 4 kcal/g
    assert r["energy"]["tef_kcal"] == round(t["calories_kcal"] * 0.1, 1)


def test_baseline_is_relative_index_and_peaks_after_meal():
    foods, t, ins = meal(("chicken_rice", 380))
    b = forecast.forecast(foods, t, ins, profile(), [])["baseline"]
    assert b["peak_index"] == 100 and 30 <= b["peak_time_min"] <= 90 and b["glucose_index"][0] == 0


def test_timing_matters_and_post_meal_walk_lowers_peak():
    foods, t, ins = meal(("chicken_rice", 380), ("kopi", 230))
    r = forecast.forecast(foods, t, ins, profile(), [walk(30), walk(180)])
    early, late = r["scenarios"]
    assert early["peak_change_pct"] < -3 and late["peak_change_pct"] == 0
    assert early["auc_change_pct"] < late["auc_change_pct"] < 0


def test_reduced_insulin_sensitivity_prolongs_excursion():
    foods, t, ins = meal(("chicken_rice", 380))
    normal = forecast.forecast(foods, t, ins, profile(), [])["baseline"]
    t2d = forecast.forecast(foods, t, ins, profile(diabetes_status="type2"), [])["baseline"]
    assert t2d["peak_time_min"] > normal["peak_time_min"] and t2d["auc_index"] > normal["auc_index"]


def test_cautions_for_vigorous_exercise_right_after_large_meal_and_insulin_users():
    foods, t, ins = meal(("char_kway_teow", 384), ("bubble_tea", 500))
    r = forecast.forecast(foods, t, ins, profile(diabetes_status="type1"), [walk(5, 30, "running", "high")])
    levels = [c["level"] for c in r["scenarios"][0]["cautions"]]
    texts = " ".join(c["text"] for c in r["scenarios"][0]["cautions"])
    assert levels.count("warning") >= 3 and "hypoglycaemia" in texts and "within 15 min" in texts
    assert all(ref in forecast.REFERENCES for c in r["scenarios"][0]["cautions"] for ref in c["refs"])


def test_unhealthy_meal_advisory():
    foods, t, ins = meal(("char_kway_teow", 384), ("bubble_tea", 500))
    adv = forecast.meal_advisory(t, ins, foods)
    assert adv["rating"] == "unhealthy" and adv["tips"]
    foods, t, ins = meal(("kaya_toast", 70), ("boiled_egg", 100), ("kopi", 230))
    assert forecast.meal_advisory(t, ins, foods)["rating"] == "needs_attention"
    foods, t, ins = meal(("green_salad", 150), ("broccoli", 150), ("chicken_breast", 120), ("brown_rice", 100))
    assert forecast.meal_advisory(t, ins, foods)["rating"] == "balanced"


def test_forecast_endpoint(client, auth):
    m = client.post(f"{API}/meals/capture", headers=auth, data={"description": "chicken rice and kopi"}).json()
    client.post(f"{API}/meals/analyze", json={"meal_id": m["id"]}, headers=auth)
    r = client.post(f"{API}/meals/{m['id']}/forecast", headers=auth, json={"scenarios": [walk(30), walk(10, 30, "rowing", "high")]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["scenarios"]) == 2 and len(d["time_min"]) == len(d["baseline"]["glucose_index"])
    assert "NOT a prediction" in d["disclaimer"] and d["references"]["reynolds2016"]["doi"]
    bad = client.post(f"{API}/meals/{m['id']}/forecast", headers=auth, json={"scenarios": [walk(30, act="skydiving")]})
    assert bad.status_code == 422
