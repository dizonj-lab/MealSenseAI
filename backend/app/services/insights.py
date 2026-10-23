"""Stage 6: deterministic, composition-grounded insights. Educational only — no prediction of an
individual's glucose response, no clinical targets, no medication guidance."""
from datetime import datetime, timezone

from app.services import nutrition, slm

DISCLAIMER = ("General educational information based on food composition, not a prediction of your "
              "personal glucose response or medical advice. Follow your clinician's guidance.")
SUGARY_DRINKS = {"cola", "bubble_tea", "kopi", "teh_tarik", "orange_juice"}


def _sum(foods, n):
    vals = [f["nutrients"].get(n) for f in foods]
    known = [v for v in vals if v is not None]
    return round(sum(known), 1) if known else None, len(known) < len(vals)


def totals(foods: list[dict]) -> dict:
    out, partial = {}, []
    for n in nutrition.NUTRIENTS:
        out[n], miss = _sum(foods, n)
        if miss:
            partial.append(n)
    out["grams"] = round(sum(f["grams"] for f in foods))
    out["item_count"] = len(foods)
    out["incomplete_nutrients"] = partial
    out["unmapped_items"] = [f["label"] for f in foods if not f.get("nutrition_key")]
    return out


def glucose(foods: list[dict], t: dict) -> dict:
    carbs, fiber, sugar = t["carbs_g"] or 0, t["fiber_g"] or 0, t["sugar_g"]
    gl, covered, carb_mass, reasons = 0.0, 0.0, 0.0, []
    for f in foods:
        ref = nutrition.get(f.get("nutrition_key"))
        c = f["nutrients"].get("carbs_g") or 0
        avail = max(c - (f["nutrients"].get("fiber_g") or 0), 0)
        carb_mass += avail
        if ref and ref["glycemic_index"] is not None:
            gl += ref["glycemic_index"] * avail / 100
            covered += avail
        elif avail < 5:
            covered += avail  # negligible available carbohydrate contributes ~0 GL
    coverage = covered / carb_mass if carb_mass else 1.0
    avail_total = round(max(carbs - fiber, 0), 1)
    gl_val = round(gl, 1) if coverage >= 0.7 else None

    if t["unmapped_items"] or carb_mass == 0 and t["item_count"] == 0:
        level = "UNCERTAIN"
    elif gl_val is not None:
        level = "LOW" if gl_val < 10 else "MODERATE" if gl_val < 20 else "HIGH"
    else:  # no supported GI for most carbs: fall back to carbohydrate amount, flagged uncertain
        level = "UNCERTAIN"

    reasons.append(f"About {avail_total} g available carbohydrate (total {carbs} g minus {fiber} g fibre).")
    if gl_val is not None:
        reasons.append(f"Estimated glycemic load ≈ {gl_val} using published GI values for "
                       f"{coverage:.0%} of the carbohydrate (GL <10 low, 10–19 moderate, ≥20 high).")
    else:
        reasons.append("Glycemic load not estimated: reference GI values cover only "
                       f"{coverage:.0%} of the carbohydrate in this meal.")
        if avail_total >= 60:
            reasons.append("Carbohydrate quantity is high, which typically raises glycemic impact.")
        elif avail_total >= 30:
            reasons.append("Carbohydrate quantity is moderate.")
    refined = [f["label"] for f in foods if (nutrition.get(f.get("nutrition_key")) or {}).get("refined_carb")
               and (f["nutrients"].get("carbs_g") or 0) >= 15]
    if refined:
        reasons.append("Main carbohydrate sources are refined: " + ", ".join(refined) + ".")
    if sugar is not None and sugar >= 25:
        reasons.append(f"Sugar content is notable ({sugar} g).")
    if fiber >= 8:
        reasons.append(f"Fibre ({fiber} g) may moderate the rate of carbohydrate absorption.")
    if t["unmapped_items"]:
        reasons.append("Some items have no nutrition match, so this assessment is incomplete.")
    return {"level": level, "carbs_g": carbs, "available_carbs_g": avail_total, "sugar_g": sugar,
            "fiber_g": fiber, "glycemic_load": gl_val, "gi_coverage": round(coverage, 2),
            "reasoning": reasons, "disclaimer": DISCLAIMER}


def energy(t: dict, profile) -> dict:
    kcal = t["calories_kcal"] or 0
    macro = {}
    if kcal:
        for n, k in (("carbs_g", 4), ("protein_g", 4), ("fat_g", 9)):
            macro[n.split("_")[0]] = round((t[n] or 0) * k / kcal * 100)
    goals = []
    if profile:
        for label, val, goal, unit in (("Calories", kcal, profile.calorie_goal, "kcal"),
                                       ("Carbohydrate", t["carbs_g"], profile.carb_goal_g, "g"),
                                       ("Protein", t["protein_g"], profile.protein_goal_g, "g")):
            if goal and val is not None:
                goals.append({"label": label, "value": val, "goal": goal, "unit": unit,
                              "pct": round(val / goal * 100)})
    notes = []
    if not goals:
        notes.append("Set optional daily goals in Health Profile to see progress.")
    if t["sodium_mg"] and t["sodium_mg"] > 1000:
        notes.append(f"Sodium is high for one meal ({int(t['sodium_mg'])} mg).")
    return {"calories_kcal": kcal, "carbs_g": t["carbs_g"], "protein_g": t["protein_g"], "fat_g": t["fat_g"],
            "fiber_g": t["fiber_g"], "sugar_g": t["sugar_g"], "sodium_mg": t["sodium_mg"],
            "macro_energy_pct": macro, "goal_progress": goals, "notes": notes}


def recommendations(foods: list[dict], t: dict, g: dict, profile) -> list[dict]:
    recs = []
    prefs = set(profile.diet_preferences or []) if profile else set()
    goals = set(profile.goals or []) if profile else set()
    diabetes = profile and profile.diabetes_status not in (None, "none", "prefer_not_to_disclose")
    keys = {f.get("nutrition_key") for f in foods}
    big_refined = [f for f in foods if (nutrition.get(f.get("nutrition_key")) or {}).get("refined_carb")
                   and (f["nutrients"].get("carbs_g") or 0) >= 45]
    if big_refined:
        names = ", ".join(f["label"] for f in big_refined)
        recs.append({"tag": "carbs", "title": "Consider a smaller refined-carb portion",
                     "detail": f"{names} provides most of the carbohydrate. Asking for less rice/noodles, or "
                               "choosing brown rice / wholegrain where available, lowers the carbohydrate load."})
    if (t["fiber_g"] or 0) < 6:
        recs.append({"tag": "fiber", "title": "Add non-starchy vegetables",
                     "detail": "This meal is low in fibre. Adding a side of leafy greens, broccoli or "
                               "cucumber adds fibre and volume with few calories."})
    if keys & SUGARY_DRINKS:
        recs.append({"tag": "drink", "title": "Swap the sweetened drink",
                     "detail": "Try kopi-o/teh-o kosong (no sugar), siew dai (less sweet), or plain water."})
    if (t["protein_g"] or 0) < 15 and t["item_count"]:
        alt = "tofu, egg or beans" if prefs & {"vegetarian", "vegan"} else "egg, tofu, fish or lean chicken"
        if "vegan" in prefs:
            alt = "tofu, tempeh or beans"
        recs.append({"tag": "protein", "title": "Include a protein source",
                     "detail": f"Protein is modest here (~{t['protein_g']} g); adding {alt} makes the meal more balanced."})
    if (t["sodium_mg"] or 0) > 1000:
        recs.append({"tag": "sodium", "title": "Go easy on gravy, sauces and soup",
                     "detail": "Leaving some soup or sauce behind is a simple way to reduce sodium."})
    if (t["calories_kcal"] or 0) > 800 and goals & {"calorie_awareness", "weight_management"}:
        recs.append({"tag": "portion", "title": "Share or save part of the meal",
                     "detail": f"At ~{int(t['calories_kcal'])} kcal this is a large meal relative to typical needs."})
    if g["level"] in ("MODERATE", "HIGH") or (diabetes and (g["available_carbs_g"] or 0) >= 45):
        recs.append({"tag": "activity", "title": "A gentle walk after eating may help",
                     "detail": "A light 10–15 minute walk after a carbohydrate-rich meal is a common general "
                               "suggestion — only if it's comfortable and appropriate for you."})
    if not recs:
        recs.append({"tag": "balanced", "title": "Looks reasonably balanced",
                     "detail": "No specific adjustments flagged from the composition data."})
    return recs


def allergy_warnings(foods: list[dict], profile) -> list[str]:
    if not profile or not profile.allergies:
        return []
    allergies = {a.lower() for a in profile.allergies}
    out = []
    for f in foods:
        ref = nutrition.get(f.get("nutrition_key"))
        hit = allergies & set(ref["allergens"]) if ref else set()
        if hit:
            out.append(f"{f['label']} commonly contains {', '.join(sorted(hit))} — check with the vendor.")
    return out


def core(foods: list[dict], profile) -> tuple[dict, dict]:
    """Stages 7 and 9: aggregation, glucose/energy assessment and rule-based recommendations."""
    t = totals(foods)
    g = glucose(foods, t)
    return t, {"glucose": g, "energy": energy(t, profile), "recommendations": recommendations(foods, t, g, profile),
               "allergy_warnings": allergy_warnings(foods, profile)}


def contextualise(foods: list[dict], t: dict, ins: dict, profile) -> dict:
    """Stage 8: SLM explanation grounded in the computed numbers and the user's stated goals."""
    if not foods:
        return {"text": None, "source": "none"}
    facts = {"foods": [{"name": f["label"], "grams": f["grams"]} for f in foods],
             "totals": {k: t[k] for k in nutrition.NUTRIENTS}, "glucose_level": ins["glucose"]["level"],
             "glycemic_load": ins["glucose"]["glycemic_load"], "portion_uncertainty": "photo-based estimates, ±35–50%",
             "user_goals": list(profile.goals or []) if profile else [],
             "recommendations": [r["title"] for r in ins["recommendations"]]}
    res = slm.explain(facts)
    return {"text": res.summary, "source": f"slm:{slm.status()['selected']}"} if res else {"text": None, "source": "none"}


def build(foods: list[dict], profile, use_slm: bool = True) -> tuple[dict, dict]:
    t, ins = core(foods, profile)
    ins["explanation"] = contextualise(foods, t, ins, profile) if use_slm else {"text": None, "source": "none"}
    ins["generated_at"] = datetime.now(timezone.utc).isoformat()
    return t, ins
