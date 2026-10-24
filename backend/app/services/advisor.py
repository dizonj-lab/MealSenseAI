"""Meal Advisor: a chat grounded in the user's own data and the foods the system knows.

Every answer is built from a facts bundle assembled here (never from the model's general knowledge):
  - profile: goals, optional health context (only with consent), allergies, daily goals
  - today's totals and the last 7 days of saved meals
  - the meal being discussed (items, grams, nutrients, glucose assessment)
  - nutrition records for foods mentioned in the question (reference table + the user's custom foods), and whether
    EXP-002 recognises each food from photos
  - lower-carbohydrate / lower-energy swaps from the same food category when asked
The local SLM (Ollama) phrases the answer from those facts when available; otherwise a deterministic rule engine
answers. Medication / insulin questions always get a fixed safety reply.
"""
import re
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Meal, User
from app.services import custom_foods, nutrition, slm, vision

SAFETY = re.compile(r"\b(insulin|bolus|basal|dos(e|es|age|ing)|units? of|metformin|sulfonylurea|gliclazide|medication|medicine|"
                    r"tablet|pill|drug|prescri\w*|hypo(glycaemia|glycemia)? treatment)\b", re.I)
SWAP = re.compile(r"\b(swap|instead|alternative|replace|substitut\w*|lower[- ]?(carb|calorie|sugar)|healthier|less (carb|sugar|calories))\b", re.I)
TODAY = re.compile(r"\b(today|so far|this day|how am i doing|my day|daily)\b", re.I)
WEEK = re.compile(r"\b(week|7 days|seven days|lately|recently|trend)\b", re.I)
MEAL = re.compile(r"\b(this meal|my meal|this plate|the meal|is it (ok|okay|good|healthy)|too much|enough)\b", re.I)
SAFETY_REPLY = ("I can't help with medication or insulin doses. Those decisions depend on your treatment plan, so please "
                "ask your doctor, diabetes nurse or pharmacist. I can tell you the estimated carbohydrate in a meal so you "
                "have the numbers ready for that conversation.")
DISCLAIMER = "Educational information from your logged meals and the food table, not medical advice."


class Reply(BaseModel):
    reply: str = Field(description="2-6 short sentences or a few bullet lines, plain language, grounded only in FACTS")


def _r(v, d=0):
    return None if v is None else round(v, d) if d else round(v)


def _profile(user: User) -> dict:
    p = user.profile
    if not p:
        return {}
    out = {"goals": p.goals or [], "diet_preferences": p.diet_preferences or [], "allergies": p.allergies or [],
           "daily_goals": {k: v for k, v in (("calories_kcal", p.calorie_goal), ("carbs_g", p.carb_goal_g),
                                             ("protein_g", p.protein_goal_g)) if v}}
    if p.health_consent and p.diabetes_status not in (None, "none", "prefer_not_to_disclose"):
        out["condition"] = p.diabetes_status
    return out


def _meal_brief(m: Meal) -> dict:
    t = m.totals or {}
    return {"id": m.id, "when": m.eaten_at.isoformat(timespec="minutes"), "type": m.meal_type, "status": m.status,
            "foods": [{"name": f.label, "grams": _r(f.grams), "kcal": _r((f.nutrients or {}).get("calories_kcal")),
                       "carbs_g": _r((f.nutrients or {}).get("carbs_g"), 1), "sugar_g": _r((f.nutrients or {}).get("sugar_g"), 1)}
                      for f in m.foods if not f.removed],
            "totals": {k: t.get(k) for k in ("calories_kcal", "carbs_g", "sugar_g", "protein_g", "fat_g", "fiber_g", "sodium_mg")},
            "glucose_level": (m.insights or {}).get("glucose", {}).get("level"),
            "glycemic_load": (m.insights or {}).get("glucose", {}).get("glycemic_load")}


def _food_fact(rec: dict, photo_keys: set[str]) -> dict:
    per = rec["per_100g"]
    g = rec["default_serving_g"]
    return {"key": rec["key"], "name": rec["name"], "category": rec.get("category"),
            "serving": f"{rec['serving_desc']} ≈ {g} g",
            "per_serving": {n: None if per.get(n) is None else round(per[n] * g / 100, 1) for n in nutrition.NUTRIENTS},
            "glycemic_index": rec.get("glycemic_index"), "source": rec.get("source"), "verification": rec.get("verification"),
            "recognised_from_photos": rec["key"] in photo_keys,
            "custom": rec["key"] in nutrition.CUSTOM}


def mentioned_foods(text: str, user_id: int, limit: int = 4) -> list[dict]:
    q = " " + re.sub(r"[^a-z0-9 ]", " ", text.lower()) + " "
    hits: dict[str, str] = {}   # key -> longest alias matched
    for rec in nutrition.CUSTOM.values():
        if rec["user_id"] == user_id:
            for a in [rec["name"].lower(), *rec["aliases"]]:
                if f" {re.sub(r'[^a-z0-9 ]', ' ', a).strip()} " in q:
                    hits[rec["key"]] = max(hits.get(rec["key"], ""), a, key=len)
    for alias, key in nutrition._db()["alias"].items():
        if len(alias) >= 3 and f" {alias} " in q:
            hits[key] = max(hits.get(key, ""), alias, key=len)
    keys = sorted(hits, key=lambda k: -len(hits[k]))
    out = [k for i, k in enumerate(keys)   # drop a match inside a longer one ("rice" inside "chicken rice")
           if not any(re.search(rf"\b{re.escape(hits[k])}\b", hits[o]) for o in keys[:i])]
    return [nutrition.get(k) for k in out[:limit]]


def swaps(rec: dict, n: int = 3) -> list[dict]:
    per = rec["per_100g"]
    base_c = (per.get("carbs_g") or 0) * rec["default_serving_g"] / 100
    base_k = (per.get("calories_kcal") or 0) * rec["default_serving_g"] / 100
    cands = []
    for f in nutrition.all_foods():
        if f["key"] == rec["key"] or f["category"] != rec.get("category"):
            continue
        c = (f["per_100g"].get("carbs_g") or 0) * f["default_serving_g"] / 100
        k = (f["per_100g"].get("calories_kcal") or 0) * f["default_serving_g"] / 100
        if f["per_100g"].get("carbs_g") is not None and c < base_c * 0.8 and k <= base_k * 1.1:
            cands.append((c, f))
    cands.sort(key=lambda x: x[0])
    return [{"name": f["name"], "serving": f"{f['serving_desc']} ≈ {f['default_serving_g']} g", "carbs_g": round(c, 1),
             "kcal": round((f["per_100g"].get("calories_kcal") or 0) * f["default_serving_g"] / 100)} for c, f in cands[:n]]


def facts(db: Session, user: User, message: str, meal: Meal | None, tz_offset_min: int = 0) -> dict:
    tz = timezone(timedelta(minutes=tz_offset_min))
    today = datetime.now(tz).date()
    start = datetime.combine(today - timedelta(days=6), datetime.min.time(), tz)
    meals = db.scalars(select(Meal).where(Meal.user_id == user.id, Meal.status == "confirmed", Meal.eaten_at >= start)
                       .order_by(Meal.eaten_at.desc())).all()
    todays = [m for m in meals if m.eaten_at.astimezone(tz).date() == today]
    tot = lambda ms, k: round(sum((m.totals or {}).get(k) or 0 for m in ms), 1)
    cls = vision._state.get("cls") or {}
    photo_keys = {m.get("nutrition_key") for m in (cls.get("map") or {}).values() if m.get("match") == "exact"}
    foods = mentioned_foods(message, user.id)
    out = {
        "profile": _profile(user),
        "today": {"date": today.isoformat(), "meals": len(todays),
                  "totals": {k: tot(todays, k) for k in ("calories_kcal", "carbs_g", "sugar_g", "protein_g", "fat_g", "sodium_mg")}},
        "last_7_days": {"saved_meals": len(meals), "avg_daily_kcal": round(tot(meals, "calories_kcal") / 7) if meals else None,
                        "avg_daily_carbs_g": round(tot(meals, "carbs_g") / 7, 1) if meals else None,
                        "recent": [_meal_brief(m) for m in meals[:5]]},
        "foods_mentioned": [_food_fact(r, photo_keys) for r in foods],
        "photo_model": {"name": "EXP-002", "classes": len(cls.get("names") or [])},
    }
    if meal:
        out["this_meal"] = _meal_brief(meal) | {
            "recommendations": [r["title"] for r in (meal.insights or {}).get("recommendations", [])],
            "personalised": [f"{p['audience']}: {p['title']}" for p in (meal.insights or {}).get("personalised", [])]}
    if foods and SWAP.search(message):
        out["swaps"] = {r["name"]: swaps(r) for r in foods}
    elif meal and SWAP.search(message):
        top = max((f for f in meal.foods if not f.removed and f.nutrition_key and nutrition.get(f.nutrition_key)),
                  key=lambda f: (f.nutrients or {}).get("carbs_g") or 0, default=None)
        if top:
            out["swaps"] = {top.label: swaps(nutrition.get(top.nutrition_key))}
    return out


def grounding(fx: dict) -> list[dict]:
    """Human-readable list of the facts an answer may draw on (shown under each reply)."""
    g = []
    if fx["profile"].get("goals") or fx["profile"].get("condition"):
        g.append({"kind": "profile", "label": "Your profile",
                  "detail": ", ".join(fx["profile"].get("goals", []) + ([fx["profile"]["condition"]] if fx["profile"].get("condition") else []))})
    g.append({"kind": "today", "label": "Today", "detail": f"{fx['today']['meals']} saved meal(s), {fx['today']['totals']['calories_kcal']} kcal, {fx['today']['totals']['carbs_g']} g carbs"})
    if fx.get("this_meal"):
        m = fx["this_meal"]
        g.append({"kind": "meal", "label": "This meal", "detail": ", ".join(f"{f['name']} {f['grams']} g" for f in m["foods"])})
    for f in fx["foods_mentioned"]:
        g.append({"kind": "food", "label": f["name"], "detail": f"{f['source']} ({f['verification'].replace('_', ' ')})"})
    if fx.get("swaps"):
        g.append({"kind": "swaps", "label": "Swaps", "detail": "same category, ≥20% fewer carbs per typical serving"})
    return g


def _fmt_food(f: dict) -> str:
    p = f["per_serving"]
    parts = [f"{round(p['calories_kcal'])} kcal" if p["calories_kcal"] is not None else None,
             f"{p['carbs_g']} g carbs" if p["carbs_g"] is not None else None,
             f"{p['sugar_g']} g sugar" if p["sugar_g"] is not None else None,
             f"{p['protein_g']} g protein" if p["protein_g"] is not None else None,
             f"{round(p['sodium_mg'])} mg sodium" if p["sodium_mg"] is not None else None]
    gi = f" GI {f['glycemic_index']:g}." if f["glycemic_index"] is not None else ""
    seen = "" if f["custom"] else (" The photo model recognises it." if f["recognised_from_photos"] else
                                   " The photo model doesn't have it as a class, so name it when you log it.")
    return f"{f['name']} ({f['serving']}): {', '.join(x for x in parts if x) or 'no nutrient values recorded'}.{gi}{seen}"


def rules_answer(message: str, fx: dict) -> str:
    lines = []
    if fx.get("swaps"):
        for name, opts in fx["swaps"].items():
            lines.append(f"Lower-carb options in the same category as {name}: " + ("; ".join(
                f"{o['name']} ({o['serving']}, {o['carbs_g']} g carbs, {o['kcal']} kcal)" for o in opts) if opts else "none found in the food table."))
    if fx["foods_mentioned"] and not fx.get("swaps"):
        lines += [_fmt_food(f) for f in fx["foods_mentioned"]]
    if fx.get("this_meal") and (MEAL.search(message) or not lines):
        m = fx["this_meal"]
        t = m["totals"]
        top = sorted(m["foods"], key=lambda f: -(f["carbs_g"] or 0))[:2]
        lines.append(f"This meal: about {round(t['calories_kcal'] or 0)} kcal and {round(t['carbs_g'] or 0)} g carbohydrate"
                     + (f", mostly from {' and '.join(f['name'] for f in top if f['carbs_g'])}" if top and top[0]["carbs_g"] else "")
                     + f". Potential glucose impact: {m['glucose_level'] or 'not assessed'}"
                     + (f" (glycaemic load {m['glycemic_load']})." if m["glycemic_load"] is not None else "."))
        if m["recommendations"]:
            lines.append("Suggestions: " + "; ".join(m["recommendations"][:3]) + ".")
    if TODAY.search(message) or (not lines and not fx.get("this_meal")):
        t, goals = fx["today"]["totals"], fx["profile"].get("daily_goals", {})
        unit = {"calories_kcal": " kcal", "carbs_g": " g", "protein_g": " g"}
        prog = "; ".join(f"{k.split('_')[0]} {round(t[k]):,} of {round(v):,}{unit.get(k, '')}" for k, v in goals.items() if k in t)
        lines.append(f"Today you've saved {fx['today']['meals']} meal(s): {round(t['calories_kcal']):,} kcal, {round(t['carbs_g'])} g carbs, "
                     f"{round(t['protein_g'])} g protein." + (f" Against your goals: {prog}." if prog else ""))
    if WEEK.search(message) and fx["last_7_days"]["saved_meals"]:
        w = fx["last_7_days"]
        lines.append(f"Over the last 7 days: {w['saved_meals']} saved meals, about {w['avg_daily_kcal']} kcal and "
                     f"{w['avg_daily_carbs_g']} g carbs per day on average.")
    if not lines:
        lines.append("I can answer from your logged meals and the food table, for example: “How many carbs in chicken rice?”, "
                     "“What's a lower-carb swap for nasi lemak?”, “How am I doing today?” or, from a meal page, “Is this meal OK for my goal?”.")
    return "\n".join(lines)


SYSTEM = ("You are MealSenseAI's Meal Advisor. Answer ONLY from FACTS (the user's logged meals, profile and the food table). "
          "If FACTS do not contain the answer, say you don't have that information and suggest logging the meal or naming "
          "the food. Never invent foods, numbers or studies. Never give medication or insulin advice. Do not predict the "
          "user's blood glucose. Use grams and kcal from FACTS, say values are estimates, keep it short and practical, and "
          "respect allergies and diet preferences in FACTS.")


def answer(db: Session, user: User, message: str, history: list[dict], meal: Meal | None, tz_offset_min: int = 0) -> dict:
    if SAFETY.search(message):
        return {"reply": SAFETY_REPLY, "source": "safety", "grounding": [], "disclaimer": DISCLAIMER}
    fx = facts(db, user, message, meal, tz_offset_min)
    st = slm.status()
    reply, source = None, "rules"
    if st["available"]:
        import json
        convo = "\n".join(f"{h['role'].upper()}: {h['content']}" for h in history[-6:])
        res = slm.chat_json("advisor", SYSTEM, f"FACTS:\n{json.dumps(fx, default=str)}\n\nCONVERSATION:\n{convo}\nUSER: {message}",
                            Reply, timeout=60)
        if res and res.reply.strip() and not SAFETY.search(res.reply):
            reply, source = res.reply.strip(), f"slm:{st['selected']}"
    if reply is None:
        reply = rules_answer(message, fx)
    return {"reply": reply, "source": source, "grounding": grounding(fx), "disclaimer": DISCLAIMER}
