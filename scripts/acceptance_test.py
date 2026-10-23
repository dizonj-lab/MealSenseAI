#!/usr/bin/env python3
"""MealSenseAI acceptance tests against a running deployment (standard library only).

  python3 scripts/acceptance_test.py run    [--url http://localhost:8080] [--image path.jpg]
  python3 scripts/acceptance_test.py verify [--url ...]      # after a restart: data must still be there
Maps to the NUS acceptance tests 3-9 (1-2 = deployment, 9 = restart, 10 = --offline run of acceptance.sh).
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "test-results" / "acceptance_state.json"
RESULTS = []


def call(url, method="GET", token=None, json_body=None, files=None, data=None, raw=False):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    body = None
    if json_body is not None:
        body, headers["Content-Type"] = json.dumps(json_body).encode(), "application/json"
    elif files or data:
        b = uuid.uuid4().hex
        parts = []
        for k, v in (data or {}).items():
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (fname, content, ctype) in (files or {}).items():
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fname}"\r\n'
                         f'Content-Type: {ctype}\r\n\r\n'.encode() + content + b"\r\n")
        body = b"".join(parts) + f"--{b}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={b}"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            payload = r.read()
            return r.status, (payload if raw else json.loads(payload or b"null"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def check(no, name, cond, evidence=""):
    RESULTS.append({"test": no, "name": name, "passed": bool(cond), "evidence": evidence})
    print(f"[{'PASS' if cond else 'FAIL'}] AT{no} {name}" + (f" — {evidence}" if evidence else ""))
    return cond


def run(base, image):
    api = f"{base}/api/v1"
    s, h = call(f"{api}/health")
    check(1, "deployment reachable and healthy", s == 200 and h["database"], json.dumps(h))
    email, pw = f"at-{uuid.uuid4().hex[:8]}@mealsense.ai", "Acceptance#2026"
    s, r = call(f"{api}/auth/register", "POST", json_body={"email": email, "password": pw, "name": "Acceptance"})
    tok = r["access_token"] if s == 201 else None
    s, ai = call(f"{api}/ai/models", token=tok)
    clf = next((m for m in ai["vision"]["models"] if "EXP-002" in m["name"]), {}) if s == 200 else {}
    s2, srch = call(f"{api}/taxonomy/search?q=chicken%20rice", token=tok)
    check(3, "model loaded, 320-class taxonomy aligned", h["vision"] and clf.get("food_classes") == 320
          and s2 == 200 and srch[0]["name"] == "chicken rice" and srch[0]["id"] == 63,
          f"{clf.get('name')} on {clf.get('device')}, sha256 {str(clf.get('sha256'))[:12]}…, classes {clf.get('food_classes')}")
    s, me = call(f"{api}/users/health-profile", "PUT", tok, json_body={
        "health_consent": True, "age": 52, "weight_kg": 72, "activity_level": "light", "diabetes_status": "type2",
        "glucose_unit": "mmol/L", "hba1c": 7.2, "goals": ["carb_awareness", "diabetes_friendly"],
        "calorie_goal": 1800, "carb_goal_g": 180})
    check("1b", "login + onboarding + diabetes health profile", s == 200 and me["onboarded"]
          and me["profile"]["diabetes_status"] == "type2")
    img = Path(image)
    s, meal = call(f"{api}/meals/capture", "POST", tok, files={"top": (img.name, img.read_bytes(), "image/jpeg")})
    s, meal = call(f"{api}/meals/analyze", "POST", tok, json_body={"meal_id": meal["id"]})
    top = next(st for st in meal["stages"] if st["key"] == "classify")["per_view"][0]["top_labels"]
    check(4, "unseen photo uploaded and classified", s == 200, f"{img.name}: stage status "
          + next(st for st in meal['stages'] if st['key'] == 'classify')['status'])
    check(5, "top-3 food predictions returned", len(top) == 3,
          "; ".join(f"{t['label']} {t['score']:.1%}" for t in top))
    food = next((f for f in meal["foods"] if f["origin"] == "model"), None)
    if food is None:  # low confidence: user picks candidate 1
        s, meal = call(f"{api}/meals/{meal['id']}/foods", "POST", tok, json_body={"candidate_class_id": top[0]["class_id"]})
        food = next(f for f in meal["foods"] if f["taxonomy_class"] == top[0]["label"])
    alt = top[1]
    s, m2 = call(f"{api}/meals/{meal['id']}/foods/{food['id']}", "PUT", tok, json_body={"candidate_class_id": alt["class_id"]})
    f2 = next(f for f in m2["foods"] if f["id"] == food["id"])
    s, m3 = call(f"{api}/meals/{meal['id']}/foods/{food['id']}", "PUT", tok, json_body={"candidate_class_id": top[0]["class_id"]})
    f3 = next(f for f in m3["foods"] if f["id"] == food["id"])
    check(6, "override to candidate 2, then back to candidate 1", f2["taxonomy_class"] == alt["label"]
          and f3["taxonomy_class"] == top[0]["label"], f"{top[0]['label']} -> {alt['label']} -> {top[0]['label']}")
    if not f3["nutrition_key"]:
        s, m3 = call(f"{api}/meals/{meal['id']}/foods/{food['id']}", "PUT", tok, json_body={"nutrition_key": "white_rice"})
    s, m4 = call(f"{api}/meals/{meal['id']}/foods/{food['id']}", "PUT", tok, json_body={"grams": 250})
    f4 = next(f for f in m4["foods"] if f["id"] == food["id"])
    ins = m4["insights"]
    s, fc = call(f"{api}/meals/{meal['id']}/forecast", "POST", tok, json_body={"scenarios": [
        {"activity": "brisk_walk", "intensity": "moderate", "start_min": 30, "duration_min": 15}]})
    check(7, "portion correction, nutrition with provenance, diabetes-aware insights",
          f4["portion"]["method"] == "user_entered" and f4["nutrients"]["calories_kcal"] is not None
          and f4["nutrition_source"]["source"] and ins["glucose"]["level"] and ins["recommendations"]
          and s == 200 and any("hypoglycaemia" in c["text"] for c in fc["scenarios"][0]["cautions"]),
          f"{f4['label']} 250 g = {f4['nutrients']['calories_kcal']} kcal ({f4['nutrition_source']['match']}, "
          f"{f4['nutrition_source']['verification']}); glucose {ins['glucose']['level']}; {len(ins['recommendations'])} recommendation(s)")
    s, saved = call(f"{api}/meals/{meal['id']}/confirm", "PUT", tok, json_body={"meal_type": "lunch"})
    s, hist = call(f"{api}/meals/history", token=tok)
    s2, dash = call(f"{api}/dashboard/summary", token=tok)
    check(8, "meal saved; history and dashboard retrieve it", saved["status"] == "confirmed"
          and hist["meals"][0]["id"] == meal["id"] and dash["total_meals"] >= 1,
          f"history {len(hist['meals'])} meal(s); today {dash['today']['calories_kcal']} kcal")
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"email": email, "password": pw, "meal_id": meal["id"],
                                 "kcal": saved["totals"]["calories_kcal"], "label": f4["label"]}))


def verify(base):
    api = f"{base}/api/v1"
    st = json.loads(STATE.read_text())
    s, r = call(f"{api}/auth/login", "POST", json_body={"email": st["email"], "password": st["password"]})
    tok = r["access_token"] if s == 200 else None
    s, meal = call(f"{api}/meals/{st['meal_id']}", token=tok)
    si, _ = call(f"{api}/meals/{st['meal_id']}/images/top", token=tok, raw=True)
    check(9, "data persists after restart (account, meal, nutrition, photo)", s == 200 and meal["status"] == "confirmed"
          and meal["totals"]["calories_kcal"] == st["kcal"] and si == 200,
          f"meal {st['meal_id']} ({st['label']}) {meal['totals']['calories_kcal'] if s == 200 else '?'} kcal, photo HTTP {si}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "verify"])
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--image", default=str(ROOT / "backend/tests/fixtures/coffee.png"))
    a = ap.parse_args()
    for _ in range(60):  # wait for readiness
        try:
            if call(f"{a.url}/api/v1/health")[0] == 200:
                break
        except Exception:
            pass
        time.sleep(2)
    run(a.url, a.image) if a.mode == "run" else verify(a.url)
    out = ROOT / "test-results" / f"acceptance_{a.mode}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"url": a.url, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "results": RESULTS}, indent=2))
    sys.exit(0 if all(r["passed"] for r in RESULTS) else 1)


if __name__ == "__main__":
    main()
