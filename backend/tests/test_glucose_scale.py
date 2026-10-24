"""mmol/L view of the meal curve: baseline (measured, or unknown) + estimated rise; personal calibration from readings."""
from datetime import datetime, timedelta, timezone

import pytest

API = "/api/v1"


def meal_at(client, auth, when):
    m = client.post(f"{API}/meals/capture", headers=auth, data={"description": "chicken rice"}).json()
    client.post(f"{API}/meals/analyze", json={"meal_id": m["id"]}, headers=auth)
    r = client.put(f"{API}/meals/{m['id']}/confirm", headers=auth, json={"eaten_at": when.isoformat()})
    assert r.status_code == 200, r.text
    return r.json()


def reading(client, auth, value, at, context, mid=None):
    r = client.post(f"{API}/glucose", headers=auth, json={"value": value, "measured_at": at.isoformat(), "context": context, "meal_id": mid})
    assert r.status_code == 201, r.text


def scale_of(client, auth, mid):
    return client.post(f"{API}/meals/{mid}/simulate", headers=auth, json={"portions": {}}).json()["glucose_scale"]


def test_population_estimate_without_baseline(client, auth):
    m = meal_at(client, auth, datetime.now(timezone.utc))
    gs = scale_of(client, auth, m["id"])
    assert gs["baseline_mmol"] is None and gs["calibration"]["kind"] == "population"
    assert 0 < gs["band_mmol"][0] < gs["peak_rise_mmol"] < gs["band_mmol"][1]
    assert gs["peak_rise_mmol"] < 8   # a plate of chicken rice stays below the diabetes OGTT anchor for normal tolerance
    assert "Estimate only" in gs["note"] and "insulin" in gs["note"]
    fc = client.post(f"{API}/meals/{m['id']}/forecast", headers=auth, json={"scenarios": []}).json()
    assert fc["glucose_scale"]["peak_rise_mmol"] == pytest.approx(gs["peak_rise_mmol"], rel=0.01)


def test_diabetes_anchor_is_higher(client, auth):
    m = meal_at(client, auth, datetime.now(timezone.utc))
    normal = scale_of(client, auth, m["id"])["peak_rise_mmol"]
    client.put(f"{API}/users/health-profile", headers=auth, json={"health_consent": True, "diabetes_status": "type2"})
    assert scale_of(client, auth, m["id"])["peak_rise_mmol"] > normal * 1.5


def test_baseline_and_personal_calibration(client, auth):
    t0 = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    pop = None
    for d in range(3):
        when = t0 + timedelta(days=d)
        m = meal_at(client, auth, when)
        gs = scale_of(client, auth, m["id"])
        assert gs["calibration"]["kind"] == "population" and gs["calibration"]["n_meals"] == d
        pop = pop or gs["peak_rise_mmol"]
        reading(client, auth, 5.0, when - timedelta(minutes=10), "before_meal", m["id"])
        reading(client, auth, 5.0 + 2 * pop, when + timedelta(minutes=60), "after_meal", m["id"])   # rises twice the population estimate
    gs = scale_of(client, auth, m["id"])
    assert gs["baseline_mmol"] == 5.0 and "before meal" in gs["baseline_source"]
    assert gs["calibration"]["kind"] == "personal" and gs["calibration"]["n_meals"] == 3
    assert 1.5 < gs["calibration"]["factor_vs_population"] < 3   # measured rises at 60 min, scaled to the model's value there
    assert gs["band_mmol"][0] < gs["peak_rise_mmol"] < gs["band_mmol"][1]
