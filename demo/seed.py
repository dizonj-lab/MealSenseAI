"""Load the demo account: a fictional person with type 2 diabetes and a week of hawker meals.

    python3 seed.py http://127.0.0.1:8380 [photos-dir]

Everything goes through the public API, so every meal is really analysed by the
model, as if it had been captured in the app. A meal whose photo is in
photos/ (made by photos.py) is captured from that photo, with its description
as a hint; otherwise from the description alone. Meals the analysis cannot fully
match are saved from the description instead, so the history is always complete.

Stdlib only. Run again: an existing account is left as it is (delete the demo's
database volume to start over).
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

EMAIL, PASSWORD, NAME = "weiming@mealsense.example", "demo-mealsense-2026", "Wei Ming"
PROFILE = {
    "health_consent": True, "age": 52, "sex": "male", "height_cm": 172, "weight_kg": 78,
    "activity_level": "light", "diabetes_status": "type2", "glucose_unit": "mmol/L",
    "goals": ["carb_awareness", "diabetes_friendly"], "allergies": [],
    "calorie_goal": 1900, "carb_goal_g": 200, "protein_goal_g": 80,
}
# (days ago, hour SGT, meal type, photo key, description). Today's lunch is captured on camera.
MEALS = [
    (6, 8, "breakfast", "kaya_toast", "kaya toast and 2 soft boiled eggs and kopi"),
    (6, 13, "lunch", "nasi_lemak", "nasi lemak"),
    (5, 12, "lunch", "laksa", "laksa"),
    (5, 19, "dinner", "fish_soup", "sliced fish soup and rice"),
    (4, 8, "breakfast", None, "oatmeal and banana"),
    (4, 13, "lunch", "char_kway_teow", "char kway teow"),
    (3, 12, "lunch", "chicken_rice", "chicken rice"),
    (3, 19, "dinner", "yong_tau_foo", "yong tau foo"),
    (2, 8, "breakfast", "prata", "2 roti prata and teh tarik"),
    (2, 13, "lunch", "bak_chor_mee", "bak chor mee"),
    (1, 12, "lunch", "nasi_lemak", "nasi lemak and teh tarik"),
    (1, 19, "dinner", "fish_soup", "sliced fish soup and green leafy vegetables"),
    (0, 8, "breakfast", "kaya_toast", "kaya toast and kopi"),
]


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/") + "/api/v1"
        self.token: str | None = None

    def call(self, method: str, path: str, body: dict | None = None, form: tuple[bytes, str] | None = None):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        data = None
        if form:
            data, headers["Content-Type"] = form
        elif body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        for _ in range(20):
            req = Request(self.base + path, data=data, method=method, headers=headers)
            try:
                with urlopen(req, timeout=180) as r:
                    return json.loads(r.read() or b"null")
            except HTTPError as e:
                if e.code == 429:  # the front door's rate limit, meant for people: wait our turn
                    time.sleep(4)
                    continue
                raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode()[:300]}") from None
        raise RuntimeError(f"{method} {path}: still rate-limited")


def multipart(fields: dict[str, str], photo: Path | None) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    out = b""
    for k, v in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    if photo:
        out += (f'--{boundary}\r\nContent-Disposition: form-data; name="top"; filename="{photo.name}"\r\n'
                "Content-Type: image/jpeg\r\n\r\n").encode() + photo.read_bytes() + b"\r\n"
    return out + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def save(api: Api, description: str, photo: Path | None, meal_type: str, eaten: datetime) -> str:
    meal = api.call("POST", "/meals/capture", form=multipart({"description": description}, photo))
    meal = api.call("POST", "/meals/analyze", {"meal_id": meal["id"]})
    for f in meal["foods"]:  # what a person would do: drop what has no nutrition record
        if not f.get("removed") and not f.get("nutrition_key"):
            meal = api.call("DELETE", f"/meals/{meal['id']}/foods/{f['id']}")
    if not any(not f.get("removed") for f in meal["foods"]):
        api.call("DELETE", f"/meals/{meal['id']}")
        raise RuntimeError(f"nothing in {description!r} has a nutrition record")
    api.call("PUT", f"/meals/{meal['id']}/confirm", {"meal_type": meal_type, "eaten_at": eaten.isoformat()})
    return ", ".join(f["label"] for f in meal["foods"] if not f.get("removed"))


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8380"
    photos = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "photos"
    api = Api(base)
    try:
        api.token = api.call("POST", "/auth/login", {"email": EMAIL, "password": PASSWORD})["access_token"]
        print(f"{EMAIL} already exists; left as it is")
        return
    except RuntimeError:
        pass
    api.token = api.call("POST", "/auth/register", {"email": EMAIL, "password": PASSWORD, "name": NAME})["access_token"]
    api.call("PUT", "/users/health-profile", PROFILE)
    sgt = timezone(timedelta(hours=8))
    today = datetime.now(sgt).replace(minute=0, second=0, microsecond=0)
    for days, hour, kind, key, text in MEALS:
        eaten = (today - timedelta(days=days)).replace(hour=hour)
        photo = photos / f"{key}.jpg" if key else None
        photo = photo if photo and photo.exists() else None
        try:
            got = save(api, text, photo, kind, eaten)
        except RuntimeError as e:
            if not photo:
                raise
            print(f"   photo of {key} not saved as is ({e}); using the description")
            got = save(api, text, None, kind, eaten)
        print(f"  {eaten:%a %H:%M} {kind:9} {'photo' if photo else 'text ':5}  {got}")
    print(f"Loaded {len(MEALS)} meals for {NAME}: {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()
