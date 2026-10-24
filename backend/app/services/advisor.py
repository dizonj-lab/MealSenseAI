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
SWAP = re.compile(r"\b(swaps?|instead|alternatives?|replace\w*|substitut\w*|lower[- ]?(carb|calorie|sugar)\w*|healthier|less (carbs?|sugar|calories))\b", re.I)
TODAY = re.compile(r"\b(today|tonight|so far today|this (morning|afternoon|evening)|my day|daily)\b", re.I)
WEEK = re.compile(r"\b(weeks?|weekly|7[- ]days?|seven days|last few days|lately|recent\w*|trends?|trajector\w*|pattern\w*|progress\w*|over ?all|overview|habits?|consistent\w*)\b", re.I)
ADVICE = re.compile(r"\b(advice|advise|tips?|suggest\w*|recommend\w*|improve\w*|should i|what (can|could|should) i|better|help me|plan)\b", re.I)
MEAL = re.compile(r"\b(this (meal|plate|dish)|my meal|the meal|is (it|this) (ok|okay|good|healthy|fine|bad)|too much|enough|most carbs?|biggest)\b", re.I)
STATUS = re.compile(r"\b(how (am i|is my|are my|'?s my)|how('?s| is) (it|my)|going|doing|status|summary|nutrition(al)?|eating)\b", re.I)
SMALLTALK = re.compile(r"^\s*(hi|hello|hey|yo|good (morning|afternoon|evening)|how are you\w*|how'?s it going|thanks?( you)?|thank you|ok(ay)?|cool|great|bye)\b[\s!?.]*$", re.I)
ALCOHOL = re.compile(r"\b(wine|beer|lager|stout|sake|soju|whisky|whiskey|vodka|gin|rum|liquor|cocktail)\b", re.I)
HELP = re.compile(r"\b(what can you do|help|who are you|what are you|how do(es)? (you|this) work)\b", re.I)
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
        if f["key"] == rec["key"] or f["category"] != rec.get("category") or ALCOHOL.search(f["name"]):
            continue
        c = (f["per_100g"].get("carbs_g") or 0) * f["default_serving_g"] / 100
        k = (f["per_100g"].get("calories_kcal") or 0) * f["default_serving_g"] / 100
        meal_like = rec.get("category") in ("sg_dish", "mixed", "protein")   # a swap for a main dish must still be a meal
        if f["per_100g"].get("carbs_g") is not None and c < base_c * 0.8 and k <= base_k * 1.1 and (not meal_like or k >= 0.5 * base_k):
            cands.append((c, f))
    cands.sort(key=lambda x: abs(x[0] - 0.6 * base_c))   # a realistic step down (~40% fewer carbs), not a different kind of meal
    return [{"name": f["name"], "serving": f"{f['serving_desc']} ≈ {f['default_serving_g']} g", "carbs_g": round(c, 1),
             "kcal": round((f["per_100g"].get("calories_kcal") or 0) * f["default_serving_g"] / 100)} for c, f in cands[:n]]


WEEK_KEYS = ("calories_kcal", "carbs_g", "sugar_g", "protein_g", "fiber_g", "sodium_mg")


def _slope(ys: list[float]) -> float:
    n = len(ys)
    if n < 3:
        return 0.0
    mx, my = (n - 1) / 2, sum(ys) / n
    den = sum((i - mx) ** 2 for i in range(n))
    return sum((i - mx) * (y - my) for i, y in enumerate(ys)) / den if den else 0.0


def week_summary(meals: list[Meal], tz, today, goals: dict) -> dict:
    """Per-day totals for the last 7 days, averages over the days actually logged, trend and top contributors."""
    days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        ms = [m for m in meals if m.eaten_at.astimezone(tz).date() == d]
        days.append({"date": d.isoformat(), "weekday": d.strftime("%a"), "meals": len(ms),
                     **{k: round(sum((m.totals or {}).get(k) or 0 for m in ms), 1) for k in WEEK_KEYS}})
    logged = [d for d in days if d["meals"]]
    out = {"saved_meals": len(meals), "days": days, "logged_days": len(logged)}
    if not logged:
        return out
    avg = {k: round(sum(d[k] for d in logged) / len(logged), 1) for k in WEEK_KEYS}
    trend = {}
    for k in ("calories_kcal", "carbs_g"):
        sl, mean = _slope([d[k] for d in logged]), avg[k] or 1
        trend[k] = "rising" if sl > 0.05 * mean else "falling" if sl < -0.05 * mean else "steady"
    carbs, count, high = {}, {}, 0
    for m in meals:
        if (m.insights or {}).get("glucose", {}).get("level") == "HIGH":
            high += 1
        for f in m.foods:
            if not f.removed:
                carbs[f.label] = carbs.get(f.label, 0) + ((f.nutrients or {}).get("carbs_g") or 0)
                count[f.label] = count.get(f.label, 0) + 1
    total_c = sum(carbs.values()) or 1
    mpd = round(len(meals) / len(logged), 1)
    out.update(avg_per_logged_day=avg, trend=trend, meals_per_logged_day=mpd, partial_days=mpd < 2.5, high_glucose_impact_meals=high,
               top_carb_sources=[{"food": f, "carbs_g": round(c), "share_pct": round(c / total_c * 100)}
                                 for f, c in sorted(carbs.items(), key=lambda x: -x[1])[:3] if c > 0],
               most_frequent=[{"food": f, "times": n} for f, n in sorted(count.items(), key=lambda x: -x[1])[:3] if n > 1],
               days_over_goal={k: sum(1 for d in logged if d[k] > v) for k, v in goals.items() if k in WEEK_KEYS})
    return out


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
        "today_meals": [{"type": m.meal_type, "kcal": _r((m.totals or {}).get("calories_kcal")), "carbs_g": _r((m.totals or {}).get("carbs_g")),
                         "foods": [f.label for f in m.foods if not f.removed]} for m in reversed(todays)],
        "last_7_days": week_summary(meals, tz, today, _profile(user).get("daily_goals", {})) | {"recent": [_meal_brief(m) for m in meals[:5]]},
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
    t = fx["today"]["totals"]
    g.append({"kind": "today", "label": "Today", "detail": f"{_n(fx['today']['meals'], 'saved meal')}, {round(t['calories_kcal']):,} kcal, {round(t['carbs_g'])} g carbs"})
    w = fx["last_7_days"]
    if w.get("logged_days"):
        g.append({"kind": "week", "label": "Last 7 days", "detail": f"{w['saved_meals']} saved meals on {w['logged_days']} day(s); daily totals per day"})
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


def _n(k: int, word: str) -> str:
    return f"{k} {word}{'' if k == 1 else 's'}"


GOAL_NAMES = {"calories_kcal": ("calories", "kcal"), "carbs_g": ("carbs", "g"), "protein_g": ("protein", "g")}


def _today_text(fx: dict) -> str:
    t, goals = fx["today"]["totals"], fx["profile"].get("daily_goals", {})
    if not fx["today"]["meals"]:
        return "You haven't saved a meal today yet. Capture one and I can break it down for you."
    meals = "; ".join(f"{(m['type'] or 'meal').capitalize()}: {', '.join(m['foods'][:3])} ({m['kcal']} kcal, {m['carbs_g']} g carbs)"
                      for m in fx["today_meals"])
    txt = f"Today so far ({_n(fx['today']['meals'], 'meal')}): {round(t['calories_kcal']):,} kcal, {round(t['carbs_g'])} g carbs, {round(t['protein_g'])} g protein.\n{meals}."
    left = [f"{GOAL_NAMES[k][0]} {round(v - t[k]):,} {GOAL_NAMES[k][1]} left" if t[k] <= v else f"{GOAL_NAMES[k][0]} {round(t[k] - v):,} {GOAL_NAMES[k][1]} over"
            for k, v in goals.items() if k in GOAL_NAMES]
    return txt + (f"\nAgainst your daily goals: {'; '.join(left)}." if left else "")


def _week_text(fx: dict) -> str:
    w = fx["last_7_days"]
    if not w.get("logged_days"):
        return "There are no saved meals in the last 7 days yet, so I can't show a trend. Save a few meals and ask again."
    a, tr = w["avg_per_logged_day"], w["trend"]
    series = " · ".join(f"{d['weekday']} {round(d['calories_kcal']):,}" if d["meals"] else f"{d['weekday']} –" for d in w["days"])
    lines = [f"Last 7 days: {_n(w['saved_meals'], 'meal')} saved on {w['logged_days']} of 7 days. On the days you logged you averaged "
             f"{round(a['calories_kcal']):,} kcal, {round(a['carbs_g'])} g carbs, {round(a['sugar_g'])} g sugar and {round(a['protein_g'])} g protein.",
             f"Calories by day: {series} (– = nothing logged).",
             f"Trajectory: calories {tr['calories_kcal']}, carbs {tr['carbs_g']}" + (" (based on only a few days)." if w["logged_days"] < 4 else ".")
             if w["logged_days"] >= 3 else "Trajectory: not enough logged days yet for a trend (needs at least 3)."]
    if w["partial_days"]:
        lines.append(f"Note: you logged about {w['meals_per_logged_day']:g} meal{'' if w['meals_per_logged_day'] == 1 else 's'} per day, so these daily totals are probably partial.")
    if w.get("days_over_goal") and (not w["partial_days"] or any(w["days_over_goal"].values())):
        lines.append("Days over your goal: " + ", ".join(f"{GOAL_NAMES[k][0]} {n}/{w['logged_days']}" for k, n in w["days_over_goal"].items() if k in GOAL_NAMES) + ".")
    if w.get("top_carb_sources"):
        lines.append("Biggest carb sources: " + ", ".join(f"{s['food']} ({s['share_pct']}%)" for s in w["top_carb_sources"]) + ".")
    return "\n".join(lines)


def advice(fx: dict) -> list[str]:
    """Up to 4 practical tips derived from the user's week, today and goals (no clinical targets, no medication)."""
    p, w = fx["profile"], fx["last_7_days"]
    goals, tips = p.get("daily_goals", {}), []
    carb_focus = bool(set(p.get("goals", [])) & {"carb_awareness", "diabetes_friendly"} or p.get("condition"))
    if not w.get("logged_days"):
        return ["Save your meals for a few days. Advice gets specific once there is a week of data."]
    a = w["avg_per_logged_day"]
    top = (w.get("top_carb_sources") or [None])[0]
    if top and top["share_pct"] >= 25 and (carb_focus or "carbs_g" in goals):
        rec = nutrition.get(nutrition.lookup(top["food"])[0]) if nutrition.lookup(top["food"])[0] else None
        simple = rec and rec.get("category") in ("grain", "beverage", "snack", "dessert")   # swaps make sense for simple items
        alt = swaps(rec, 2) if simple else []
        staple = rec and rec.get("refined_carb") and rec.get("category") in ("sg_dish", "mixed")
        tips.append(f"{top['food']} gives {top['share_pct']}% of your carbs this week. "
                    + ("Asking for less rice or noodles (or brown rice where offered) cuts carbs the most"
                       if staple else "A smaller portion would cut carbs the most")
                    + (f"; lower-carb options from the food table: {' or '.join(o['name'] for o in alt)}." if alt else "."))
    if "carbs_g" in goals and w.get("days_over_goal", {}).get("carbs_g", 0) >= 2:
        tips.append(f"Carbs went over your {round(goals['carbs_g'])} g goal on {w['days_over_goal']['carbs_g']} day(s). Spreading carbs across meals helps.")
    if carb_focus and w.get("high_glucose_impact_meals"):
        tips.append(f"{_n(w['high_glucose_impact_meals'], 'meal')} this week had a HIGH potential glucose impact. Adding vegetables or protein "
                    "to those meals, and a light walk afterwards, are common general strategies.")
    if "calories_kcal" in goals:
        diff = a["calories_kcal"] - goals["calories_kcal"]
        if diff > 0.1 * goals["calories_kcal"] or (diff < -0.1 * goals["calories_kcal"] and not w["partial_days"]):
            tips.append(f"You averaged {round(abs(diff)):,} kcal {'above' if diff > 0 else 'below'} your {round(goals['calories_kcal']):,} kcal goal on logged days"
                        + (", and the trend is rising." if diff > 0 and w["trend"]["calories_kcal"] == "rising" else "."))
    elif "weight_management" in p.get("goals", []) and w["trend"]["calories_kcal"] == "rising":
        tips.append("Your daily calories are trending up. Setting a calorie goal in your profile lets me compare against it.")
    per_meal_fibre = a["fiber_g"] / w["meals_per_logged_day"]
    if (not w["partial_days"] and a["fiber_g"] < 20) or per_meal_fibre < 5:
        tips.append((f"Fibre averaged {round(a['fiber_g'])} g/day" if not w["partial_days"] else f"Your logged meals had about {round(per_meal_fibre)} g fibre each")
                    + ". Adding vegetables, legumes or wholegrains raises it (common guidance is 25–30 g a day).")
    if a["sodium_mg"] > 2000:
        tips.append(f"Sodium averaged {round(a['sodium_mg']):,} mg/day, above the WHO limit of 2,000 mg. Leaving some gravy or soup helps.")
    if "protein_g" in goals and a["protein_g"] < 0.8 * goals["protein_g"]:
        tips.append(f"Protein averaged {round(a['protein_g'])} g, below your {round(goals['protein_g'])} g goal. Eggs, tofu, fish or lean meat at each meal can help.")
    if w["logged_days"] < 4 or w["partial_days"]:
        tips.append("Logging every meal on most days makes these daily totals and trends reliable.")
    return tips[:4] or ["Nothing stands out this week. Your logged meals look in line with your goals."]


HELP_TEXT = ("I'm your Meal Advisor. I answer from your saved meals, your goals and the food table, for example:\n"
             "• “How am I doing today?” or “How was my week?”\n• “Any advice?”\n• “How many carbs in chicken rice?”\n"
             "• “What's a lower-carb swap for nasi lemak?”\n• On a meal: “Is this meal OK for my goal?”")


def rules_answer(message: str, fx: dict) -> str:
    if SMALLTALK.match(message):
        greet = "You're welcome!" if re.match(r"\s*thank", message, re.I) else "I'm doing well, thanks for asking!"
        t = fx["today"]
        return (f"{greet} " + (f"You've saved {_n(t['meals'], 'meal')} today ({round(t['totals']['calories_kcal']):,} kcal). " if t["meals"] else "")
                + "Ask me about your day, your week, a food, or tap a suggestion below.")
    if HELP.search(message) and not (fx["foods_mentioned"] or WEEK.search(message) or TODAY.search(message)):
        return HELP_TEXT
    parts = []
    if fx.get("swaps"):
        for name, opts in fx["swaps"].items():
            parts.append(f"Lower-carb options in the same category as {name}: " + ("; ".join(
                f"{o['name']} ({o['serving']}, {o['carbs_g']} g carbs, {o['kcal']} kcal)" for o in opts) if opts else "none found in the food table."))
    elif fx["foods_mentioned"]:
        parts += [_fmt_food(f) for f in fx["foods_mentioned"]]
    if fx.get("this_meal") and (MEAL.search(message) or not parts):
        m, t = fx["this_meal"], fx["this_meal"]["totals"]
        top = sorted(m["foods"], key=lambda f: -(f["carbs_g"] or 0))[:2]
        parts.append(f"This meal: about {round(t['calories_kcal'] or 0)} kcal and {round(t['carbs_g'] or 0)} g carbohydrate"
                     + (f", mostly from {' and '.join(f['name'] for f in top if f['carbs_g'])}" if top and top[0]["carbs_g"] else "")
                     + f". Potential glucose impact: {m['glucose_level'] or 'not assessed'}"
                     + (f" (glycaemic load {m['glycemic_load']})." if m["glycemic_load"] is not None else "."))
        if m["recommendations"]:
            parts.append("Suggestions: " + "; ".join(m["recommendations"][:3]) + ".")
    week, today, adv = WEEK.search(message), TODAY.search(message), ADVICE.search(message)
    general = not parts and not week and not today   # e.g. "how is my nutrition going?"
    if today or (general and STATUS.search(message)) or (general and not adv):
        parts.append(_today_text(fx))
    if week or (general and STATUS.search(message)):
        parts.append(_week_text(fx))
    if adv or week or (general and STATUS.search(message)):
        parts.append("Advice:\n" + "\n".join(f"• {t}" for t in advice(fx)))
    return "\n\n".join(parts) if parts else HELP_TEXT


SYSTEM = ("You are MealSenseAI's Meal Advisor. Answer ONLY from FACTS (the user's logged meals, profile and the food table). "
          "If FACTS do not contain the answer, say you don't have that information and suggest logging the meal or naming "
          "the food. Never invent foods, numbers or studies. Never give medication or insulin advice. Do not predict the "
          "user's blood glucose. Use grams and kcal from FACTS, say values are estimates, keep it short and practical, and "
          "respect allergies and diet preferences in FACTS. For questions about the week or progress use last_7_days "
          "(days, avg_per_logged_day, trend, top_carb_sources, days_over_goal) and say how many days were logged. "
          "When asked for advice, give 2-4 specific tips tied to the user's goals and the foods in FACTS. Reply to "
          "greetings briefly and offer what you can help with.")


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
