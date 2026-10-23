"""Seed a demo account with a profile and a few days of meals through the public API.
Usage (inside the app container): python -m app.seed [--base http://localhost:8000]
Login: demo@mealsense.ai / demo12345
"""
import argparse
from datetime import datetime, timedelta, timezone

import httpx

EMAIL, PASSWORD = "demo@mealsense.ai", "demo12345"
MEALS = [  # (days ago, hour, type, description)
    (2, 8, "breakfast", "kaya toast and 2 boiled eggs and kopi"),
    (2, 13, "lunch", "chicken rice"),
    (1, 12, "lunch", "laksa"),
    (1, 19, "dinner", "fish soup and green salad"),
    (0, 8, "breakfast", "oatmeal and banana"),
    (0, 13, "lunch", "nasi lemak and teh tarik"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    a = ap.parse_args()
    api = httpx.Client(base_url=f"{a.base}/api/v1", timeout=60)
    r = api.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        print(f"demo user already exists: {EMAIL}")
        return
    tok = api.post("/auth/register", json={"email": EMAIL, "password": PASSWORD, "name": "Demo"}).json()["access_token"]
    api.headers["Authorization"] = f"Bearer {tok}"
    api.put("/users/health-profile", json={
        "health_consent": True, "age": 45, "activity_level": "light", "diabetes_status": "type2",
        "allergies": ["peanut"], "goals": ["carb_awareness", "diabetes_friendly"],
        "calorie_goal": 1900, "carb_goal_g": 180, "protein_goal_g": 80}).raise_for_status()
    now = datetime.now(timezone.utc)
    for days, hour, mtype, desc in MEALS:
        m = api.post("/meals/capture", data={"description": desc}).json()
        api.post("/meals/analyze", json={"meal_id": m["id"]}).raise_for_status()
        eaten = (now - timedelta(days=days)).replace(hour=hour, minute=0) - timedelta(hours=8)  # SGT -> UTC
        api.put(f"/meals/{m['id']}/confirm", json={"meal_type": mtype, "eaten_at": eaten.isoformat()}).raise_for_status()
    print(f"seeded {len(MEALS)} meals for {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()
