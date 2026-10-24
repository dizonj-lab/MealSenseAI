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


WHO_SODIUM_MG = 2000      # WHO 2012 sodium guideline: < 2 g/day for adults
WHO_SAT_FAT_PCT = 10      # WHO 2023 saturated fatty acid guideline: < 10% of energy


def personalised(foods: list[dict], t: dict, g: dict, profile) -> list[dict]:
    """Condition- and goal-specific observations from the computed composition. Educational; no dosing or
    medication guidance (type 1 users are explicitly pointed to their own care plan)."""
    status = profile.diabetes_status if profile else None
    goals = set(profile.goals or []) if profile else set()
    out = []
    carb_foods = sorted(((f["label"], max((f["nutrients"].get("carbs_g") or 0) - (f["nutrients"].get("fiber_g") or 0), 0))
                         for f in foods), key=lambda x: -x[1])
    avail = sum(c for _, c in carb_foods)
    top = [(n, c) for n, c in carb_foods if c >= 5][:3]
    contrib = ", ".join(f"{n} {c:.0f} g ({c / avail * 100:.0f}%)" for n, c in top) if avail else ""
    sugary = [f["label"] for f in foods if (f["nutrients"].get("sugar_g") or 0) >= 10]
    if status == "type1":
        out.append({"audience": "Type 1 diabetes", "title": f"About {avail:.0f} g available carbohydrate (photo-based estimate)",
                    "detail": (f"Main sources: {contrib}. " if contrib else "") + "Portions are estimated from a photo and can be "
                              "off by a third or more — weigh or check servings where it matters. This app does not calculate "
                              "or advise insulin doses; follow your own diabetes care plan.", "basis": "composition"})
    elif status in ("type2", "prediabetes", "gestational") or "diabetes_friendly" in goals:
        label = {"type2": "Type 2 diabetes", "prediabetes": "Prediabetes", "gestational": "Gestational diabetes"}.get(status, "Diabetes-friendly goal")
        detail = f"Carbohydrate mainly from {contrib}. " if contrib else "Little digestible carbohydrate in this meal. "
        if top and avail >= 30:
            detail += f"Reducing the {top[0][0]} portion changes the glycaemic load the most; try it in the portion simulator. "
        if sugary:
            detail += f"Sugar-rich items: {', '.join(sugary)}. "
        detail += "Eating vegetables and protein first and a short walk afterwards are commonly suggested strategies. "
        detail += "Do not change medication based on this app."
        out.append({"audience": label, "title": f"Glycaemic load {g['glycemic_load'] if g['glycemic_load'] is not None else 'not estimated'}",
                    "detail": detail, "basis": "composition + GI table"})
    if "heart_health" in goals:
        na, sf, kcal = t.get("sodium_mg"), t.get("sat_fat_g"), t.get("calories_kcal") or 0
        parts = []
        if na is not None:
            parts.append(f"sodium {na:.0f} mg = {na / WHO_SODIUM_MG * 100:.0f}% of the WHO daily limit (2,000 mg)")
        if sf is not None and kcal:
            pct = sf * 9 / kcal * 100
            parts.append(f"saturated fat {sf:.1f} g ≈ {pct:.0f}% of this meal's energy (WHO: under {WHO_SAT_FAT_PCT}%)")
        if "sat_fat_g" in t.get("incomplete_nutrients", []):
            parts.append("saturated fat is missing for some foods, so the true value is higher than shown")
        out.append({"audience": "Heart health", "title": "Salt and saturated fat",
                    "detail": ("; ".join(parts) or "No sodium or saturated-fat data for these foods") + ".",
                    "basis": "WHO guidelines (2012 sodium, 2023 saturated fat)"})
    if goals & {"weight_management", "calorie_awareness"} and t.get("grams"):
        density = (t.get("calories_kcal") or 0) / t["grams"]
        out.append({"audience": "Weight management", "title": f"Energy density {density:.1f} kcal/g",
                    "detail": "Below ~1.5 kcal/g is considered low energy density; above ~4 is high. Swapping part of a "
                              "dense item for vegetables lowers calories while keeping volume.", "basis": "composition"})
    if not out:
        out.append({"audience": "General wellness", "title": "Balance check",
                    "detail": f"Carbohydrate mainly from {contrib}." if contrib else "Low-carbohydrate meal.",
                    "basis": "composition"})
    return out


def core(foods: list[dict], profile) -> tuple[dict, dict]:
    """Stages 7 and 9: aggregation, glucose/energy assessment and rule-based recommendations."""
    t = totals(foods)
    g = glucose(foods, t)
    return t, {"glucose": g, "energy": energy(t, profile), "recommendations": recommendations(foods, t, g, profile),
               "allergy_warnings": allergy_warnings(foods, profile), "personalised": personalised(foods, t, g, profile)}


def contextualise(foods: list[dict], t: dict, ins: dict, profile, timeout: float | None = None) -> dict:
    """Stage 8: SLM explanation grounded in the computed numbers and the user's stated goals."""
    if not foods:
        return {"text": None, "source": "none"}
    facts = {"foods": [{"name": f["label"], "grams": f["grams"]} for f in foods],
             "totals": {k: t[k] for k in nutrition.NUTRIENTS}, "glucose_level": ins["glucose"]["level"],
             "glycemic_load": ins["glucose"]["glycemic_load"], "portion_uncertainty": "photo-based estimates, ±35–50%",
             "user_goals": list(profile.goals or []) if profile else [],
             "recommendations": [r["title"] for r in ins["recommendations"]]}
    res = slm.explain(facts, timeout=timeout)
    return {"text": res.summary, "source": f"slm:{slm.status()['selected']}"} if res else {"text": None, "source": "none"}


def pending_explanation(foods: list[dict]) -> dict:
    """The SLM explanation is written after results are shown (POST /meals/{id}/explain), never inline."""
    st = slm.status()
    return {"text": None, "source": "pending", "model": st["selected"]} if foods and st["available"] else {"text": None, "source": "none"}


def build(foods: list[dict], profile, use_slm: bool = True) -> tuple[dict, dict]:
    t, ins = core(foods, profile)
    ins["explanation"] = pending_explanation(foods) if use_slm else {"text": None, "source": "none"}
    ins["generated_at"] = datetime.now(timezone.utc).isoformat()
    return t, ins
