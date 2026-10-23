"""Post-meal forecast and what-if activity analysis (educational, population-level).

Two deterministic models, both explicit about their assumptions:

1. Energy (physics): activity energy E = MET x body mass (kg) x time (h)  [1 MET ~ 1 kcal/kg/h, Ainsworth 2011]
   Carbohydrate oxidised = E x f_CHO / 4 kcal/g   [Atwater factor; f_CHO from the 'crossover' concept]
   Thermic effect of food ~10% of meal energy     [Westerterp 2004]

2. Glucose (mass balance, one compartment):
     dG/dt = Ra(t) - k * G - U_ex(t)
   G   = meal-derived glucose excess (g), Ra = gut appearance of the meal's glycaemic carbohydrate
         (available carbs x GI/100, gamma-shaped absorption whose peak is delayed by fat, fibre and protein),
   k   = insulin-mediated clearance rate (slower with reduced insulin sensitivity — illustrative values),
   U_ex = extra uptake by working muscle = CHO oxidation rate x fraction drawn from blood glucose.
   Output is a RELATIVE index (meal-only peak = 100). It is not a prediction of anyone's blood glucose;
   individual responses vary widely and need a validated, personalised model (e.g. CGM-calibrated).
"""
import math

from app.services import insights, nutrition

REFERENCES = {
    "ainsworth2011": {"cite": "Ainsworth BE, et al. 2011 Compendium of Physical Activities: a second update of codes and MET values. Med Sci Sports Exerc. 2011;43(8):1575-1581.", "doi": "10.1249/MSS.0b013e31821ece12"},
    "colberg2016": {"cite": "Colberg SR, et al. Physical Activity/Exercise and Diabetes: A Position Statement of the American Diabetes Association. Diabetes Care. 2016;39(11):2065-2079.", "doi": "10.2337/dc16-1728"},
    "riddell2017": {"cite": "Riddell MC, et al. Exercise management in type 1 diabetes: a consensus statement. Lancet Diabetes Endocrinol. 2017;5(5):377-390.", "doi": "10.1016/S2213-8587(17)30014-1"},
    "reynolds2016": {"cite": "Reynolds AN, Mann JI, Williams S, Venn BJ. Advice to walk after meals is more effective for lowering postprandial glycaemia in type 2 diabetes mellitus than advice that does not specify timing: a randomised crossover study. Diabetologia. 2016;59(12):2572-2578.", "doi": "10.1007/s00125-016-4085-2"},
    "dipietro2013": {"cite": "DiPietro L, et al. Three 15-min bouts of moderate postmeal walking significantly improves 24-h glycemic control in older people at risk for impaired glucose tolerance. Diabetes Care. 2013;36(10):3262-3268.", "doi": "10.2337/dc13-0084"},
    "colberg2009": {"cite": "Colberg SR, et al. Postprandial walking is better for lowering the glycemic effect of dinner than pre-dinner exercise in type 2 diabetic individuals. J Am Med Dir Assoc. 2009;10(6):394-397.", "doi": "10.1016/j.jamda.2009.03.015"},
    "dunstan2012": {"cite": "Dunstan DW, et al. Breaking up prolonged sitting reduces postprandial glucose and insulin responses. Diabetes Care. 2012;35(5):976-983.", "doi": "10.2337/dc11-1931"},
    "buffey2022": {"cite": "Buffey AJ, et al. The Acute Effects of Interrupting Prolonged Sitting Time in Adults with Standing and Light-Intensity Walking on Biomarkers of Cardiometabolic Health in Adults: A Systematic Review and Meta-analysis. Sports Med. 2022;52(8):1765-1787.", "doi": "10.1007/s40279-022-01649-4"},
    "richter2013": {"cite": "Richter EA, Hargreaves M. Exercise, GLUT4, and skeletal muscle glucose uptake. Physiol Rev. 2013;93(3):993-1017.", "doi": "10.1152/physrev.00038.2012"},
    "brooks1994": {"cite": "Brooks GA, Mercier J. Balance of carbohydrate and lipid utilization during exercise: the 'crossover' concept. J Appl Physiol. 1994;76(6):2253-2261.", "doi": "10.1152/jappl.1994.76.6.2253"},
    "romijn1993": {"cite": "Romijn JA, et al. Regulation of endogenous fat and carbohydrate metabolism in relation to exercise intensity and duration. Am J Physiol. 1993;265(3 Pt 1):E380-E391.", "doi": "10.1152/ajpendo.1993.265.3.E380"},
    "marliss2002": {"cite": "Marliss EB, Vranic M. Intense exercise has unique effects on both insulin release and its roles in glucoregulation: implications for diabetes. Diabetes. 2002;51(Suppl 1):S271-S283.", "doi": "10.2337/diabetes.51.2007.S271"},
    "deoliveira2011": {"cite": "de Oliveira EP, Burini RC. Food-dependent, exercise-induced gastrointestinal distress. J Int Soc Sports Nutr. 2011;8:12.", "doi": "10.1186/1550-2783-8-12"},
    "westerterp2004": {"cite": "Westerterp KR. Diet induced thermogenesis. Nutr Metab (Lond). 2004;1(1):5.", "doi": "10.1186/1743-7075-1-5"},
    "atkinson2021": {"cite": "Atkinson FS, et al. International tables of glycemic index and glycemic load values 2021: a systematic review. Am J Clin Nutr. 2021;114(5):1625-1632.", "doi": "10.1093/ajcn/nqab233"},
    "salmeron1997": {"cite": "Salmerón J, et al. Dietary fiber, glycemic load, and risk of non-insulin-dependent diabetes mellitus in women. JAMA. 1997;277(6):472-477.", "doi": "10.1001/jama.1997.03540300040031"},
    "fao2003": {"cite": "FAO. Food energy – methods of analysis and conversion factors. FAO Food and Nutrition Paper 77. Rome; 2003.", "url": "https://www.fao.org/4/y5022e/y5022e00.htm"},
    "who2015sugar": {"cite": "WHO. Guideline: Sugars intake for adults and children. Geneva: World Health Organization; 2015.", "url": "https://www.who.int/publications/i/item/9789241549028"},
    "who2012sodium": {"cite": "WHO. Guideline: Sodium intake for adults and children. Geneva: World Health Organization; 2012.", "url": "https://www.who.int/publications/i/item/9789241504836"},
    "bull2020": {"cite": "Bull FC, et al. World Health Organization 2020 guidelines on physical activity and sedentary behaviour. Br J Sports Med. 2020;54(24):1451-1462.", "doi": "10.1136/bjsports-2020-102955"},
    "hpb_plate": {"cite": "Health Promotion Board Singapore. My Healthy Plate (healthy eating guide)."},
}

# MET values approximate 2011 Compendium codes (Ainsworth 2011); "moderate" / "high" effort variants.
ACTIVITIES = {
    "sitting":         {"label": "Desk / office work (sitting)", "moderate": 1.5, "high": 1.5, "impact": "low"},
    "light_walk":      {"label": "Leisurely walk (~4 km/h)", "moderate": 3.0, "high": 3.5, "impact": "low"},
    "brisk_walk":      {"label": "Brisk walking (5.6 / 7.2 km/h)", "moderate": 4.3, "high": 7.0, "impact": "low"},
    "stairs":          {"label": "Stair climbing", "moderate": 4.0, "high": 8.8, "impact": "medium"},
    "cycling":         {"label": "Cycling, stationary (~100 / ~150 W)", "moderate": 6.8, "high": 8.8, "impact": "low"},
    "rowing":          {"label": "Rowing, stationary (~100 / ~150 W)", "moderate": 7.0, "high": 8.5, "impact": "medium"},
    "swimming":        {"label": "Swimming laps, freestyle", "moderate": 5.8, "high": 9.8, "impact": "medium"},
    "running":         {"label": "Running (8 / 11 km/h)", "moderate": 8.3, "high": 11.0, "impact": "high"},
    "badminton":       {"label": "Badminton (social / competitive)", "moderate": 5.5, "high": 7.0, "impact": "medium"},
    "resistance":      {"label": "Resistance training", "moderate": 3.5, "high": 6.0, "impact": "medium"},
}
SITTING_MET = ACTIVITIES["sitting"]["moderate"]
DEFAULT_WEIGHT_KG = 70.0
BLOOD_GLUCOSE_SHARE = 0.35
UPTAKE_KM_G = 4.0  # half-saturation of meal-glucose uptake vs glucose excess (mass action)
DEFAULT_GI = 60  # assumed medium GI where the table has no supported value (flagged in output)

# Model assumptions (named so the UI can list them)
ASSUMPTIONS = [
    "Carbohydrate share of energy during exercise: ~35% at <3 MET, ~50% at 3–6 MET, ~65% at 6–9 MET, ~75% at ≥9 MET "
    "(approximation of the crossover concept: Brooks & Mercier 1994; Romijn 1993).",
    "About 35% of carbohydrate burned during post-meal exercise is drawn from blood glucose; the rest comes from muscle "
    "glycogen (modelling assumption; muscle glucose uptake rises with contraction and insulin: Richter & Hargreaves 2013).",
    "Muscle uptake of meal glucose scales with how elevated glucose is at that moment (saturating, mass-action term), "
    "so exercise during the rise or peak removes more meal glucose than exercise after it has passed.",
    "At ≥8 MET, counter-regulatory hormones raise liver glucose output, offsetting about half of that extra uptake "
    "(qualitative basis: Marliss & Vranic 2002).",
    "Insulin-mediated clearance half-life of about 25 min with normal insulin sensitivity, about 38 min with prediabetes and "
    "about 52 min with type 2 / other diabetes (illustrative values, not measured for you).",
    "Glycaemic carbohydrate = available carbohydrate × GI/100; foods without a published GI are assumed GI 60.",
    "Gut glucose appearance peaks about 30 min after eating (blood excursion peaks later, about 45–70 min); it is delayed by "
    "fat (>15 g), fibre (>8 g) and protein (>25 g).",
]


def _cho_fraction(met: float) -> float:
    return 0.35 if met < 3 else 0.50 if met < 6 else 0.65 if met < 9 else 0.75


def _clearance_k(diabetes_status: str | None) -> tuple[float, str]:
    half = {"prediabetes": 38.0, "type2": 52.0, "type1": 52.0, "gestational": 52.0}.get(diabetes_status or "", 25.0)
    label = "normal insulin sensitivity (assumed)" if half == 25.0 else f"reduced insulin sensitivity ({diabetes_status})"
    return math.log(2) / half, label


def _meal_inputs(foods: list[dict], totals: dict) -> dict:
    glyc_carbs, avail_total, gi_assumed = 0.0, 0.0, []
    for f in foods:
        n = f["nutrients"] or {}
        avail = max((n.get("carbs_g") or 0) - (n.get("fiber_g") or 0), 0)
        ref = nutrition.get(f.get("nutrition_key"))
        gi = ref["glycemic_index"] if ref and ref.get("glycemic_index") is not None else None
        if gi is None and avail >= 5:
            gi_assumed.append(f["label"])
        glyc_carbs += avail * (gi if gi is not None else DEFAULT_GI) / 100
        avail_total += avail
    fat, fiber, prot = totals.get("fat_g") or 0, totals.get("fiber_g") or 0, totals.get("protein_g") or 0
    tp = 30 + (10 if fat > 15 else 0) + (5 if fiber > 8 else 0) + (5 if prot > 25 else 0)
    return {"glycemic_carbs_g": round(glyc_carbs, 1), "available_carbs_g": round(avail_total, 1),
            "absorption_peak_min": tp, "gi_assumed_for": gi_assumed, "kcal": totals.get("calories_kcal") or 0}


def _simulate(meal: dict, k: float, weight: float, scenario: dict | None, horizon: int) -> dict:
    shape, scale = 3.0, meal["absorption_peak_min"] / 2.0  # gamma mode = (shape-1)*scale = peak time
    norm = math.gamma(shape) * scale ** shape
    A = meal["glycemic_carbs_g"]
    act = None
    if scenario:
        met = ACTIVITIES[scenario["activity"]][scenario["intensity"]]
        act = {"start": scenario["start_min"], "end": scenario["start_min"] + scenario["duration_min"], "met": met}
    G, series, uptake_g, cho_g, ex_kcal = 0.0, [], 0.0, 0.0, 0.0
    for t in range(horizon + 1):
        ra = A * (t ** (shape - 1)) * math.exp(-t / scale) / norm if t > 0 else 0.0
        u = 0.0
        if act and act["start"] <= t < act["end"]:
            kcal_min = act["met"] * weight / 60
            ex_kcal += kcal_min
            cho = kcal_min * _cho_fraction(act["met"]) / 4.0
            cho_g += cho
            u = cho * BLOOD_GLUCOSE_SHARE * (0.5 if act["met"] >= 8 else 1.0) * G / (G + UPTAKE_KM_G)
        free = max(G + ra - k * G, 0.0)
        taken = min(u, free)            # muscle can only clear meal glucose that is present;
        uptake_g += taken               # the rest of its uptake comes from liver output (baseline)
        G = free - taken
        if t % 5 == 0:
            series.append(round(G, 3))
    return {"series": series, "exercise_kcal": round(ex_kcal, 1), "cho_oxidised_g": round(cho_g, 1),
            "meal_glucose_taken_up_g": round(max(uptake_g, 0), 1)}


def _energy_timeline(meal_kcal: float, weight: float, scenario: dict | None, horizon: int) -> dict:
    """Cumulative expenditure: sitting baseline (office work), activity replaces sitting time, TEF ~10%."""
    cum, series = 0.0, []
    tef_total = 0.10 * meal_kcal
    for t in range(horizon + 1):
        met = SITTING_MET
        if scenario and scenario["start_min"] <= t < scenario["start_min"] + scenario["duration_min"]:
            met = ACTIVITIES[scenario["activity"]][scenario["intensity"]]
        cum += met * weight / 60
        tef = tef_total * min(t / 300, 1)  # spread over ~5 h
        if t % 5 == 0:
            series.append(round(cum + tef, 1))
    return {"series": series, "total_kcal": series[-1]}


def _cautions(scenario: dict, meal: dict, profile, horizon: int) -> list[dict]:
    met = ACTIVITIES[scenario["activity"]][scenario["intensity"]]
    a = ACTIVITIES[scenario["activity"]]
    start, kcal = scenario["start_min"], meal["kcal"]
    out = []
    if start < 15 and met >= 6:
        out.append({"level": "warning", "text": "Vigorous or high-impact exercise within 15 min of eating can cause cramps, reflux, "
                    "nausea or a stitch, because blood flow is redirected from the gut to the muscles. Start with a light walk "
                    "and build up.", "refs": ["deoliveira2011"]})
    elif start < 15 and met < 6:
        out.append({"level": "info", "text": "Gentle movement soon after eating is generally well tolerated. Keep the first minutes easy.",
                    "refs": ["deoliveira2011", "buffey2022"]})
    if met >= 6 and start < 60 and kcal >= 700:
        out.append({"level": "warning", "text": f"This is a large meal (~{int(kcal)} kcal). Leave 1–2 h before high-intensity "
                    "or high-impact training such as running or rowing.", "refs": ["deoliveira2011"]})
    if a["impact"] == "high" and start < 60:
        out.append({"level": "caution", "text": "Running jostles the stomach; GI symptoms are more common in running than "
                    "in cycling or rowing after food.", "refs": ["deoliveira2011"]})
    if met >= 8:
        out.append({"level": "info", "text": "Very intense efforts can briefly RAISE blood glucose (adrenaline drives liver "
                    "glucose release) before it falls afterwards.", "refs": ["marliss2002"]})
    if 15 <= start <= 45 and met < 6:
        out.append({"level": "good", "text": "Light to moderate activity starting 15–45 min after a meal falls in the window "
                    "studies use to blunt the post-meal glucose rise.", "refs": ["reynolds2016", "colberg2009", "dipietro2013"]})
    if start >= 120:
        out.append({"level": "info", "text": "By 2 h after eating, most of the meal's glucose peak has passed. Exercise still "
                    "burns energy and improves insulin sensitivity, but changes this meal's peak less.", "refs": ["colberg2016"]})
    status = getattr(profile, "diabetes_status", None) if profile else None
    if status in ("type1", "type2", "gestational"):
        out.append({"level": "warning", "text": "If you use insulin or insulin-secretagogues (e.g. sulfonylureas), exercise can "
                    "cause hypoglycaemia during or for hours after activity. Check glucose before and after, carry fast-acting "
                    "carbohydrate, and follow your care team's plan.", "refs": ["colberg2016", "riddell2017"]})
    if status == "type1":
        out.append({"level": "warning", "text": "Type 1 diabetes: glucose responses depend on insulin dose and timing, which "
                    "this model does not include. Use the consensus guidance with your clinician.", "refs": ["riddell2017"]})
    if scenario["start_min"] + scenario["duration_min"] > horizon:
        out.append({"level": "info", "text": "Part of this activity falls after the forecast window.", "refs": []})
    out.append({"level": "info", "text": "Stop if you get chest pain, dizziness or unusual breathlessness. Check with a doctor "
                "before starting vigorous exercise if you have a heart condition or complications.", "refs": ["colberg2016"]})
    return out


def meal_advisory(totals: dict, ins: dict, foods: list[dict]) -> dict:
    """Flags meals that are unhealthy against public-health reference points (per meal, ~1/3 of daily guidance)."""
    kcal = totals.get("calories_kcal") or 0
    flags = []
    if kcal > 800:
        flags.append({"severity": 2, "text": f"High energy for one meal (~{int(kcal)} kcal, over 40% of a 2,000 kcal day).", "refs": ["bull2020"]})
    sugar = totals.get("sugar_g") or 0
    if sugar > 25:
        flags.append({"severity": 2 if sugar > 40 else 1, "text": f"Sugar is {sugar:.0f} g. WHO advises keeping free sugars under 10% of energy "
                      "(about 50 g a day), ideally under 5% (about 25 g).", "refs": ["who2015sugar"]})
    na = totals.get("sodium_mg") or 0
    if na > 1000:
        flags.append({"severity": 2 if na > 1500 else 1, "text": f"Sodium is {na:.0f} mg, over half of WHO's daily limit of under 2,000 mg.",
                      "refs": ["who2012sodium"]})
    gl = (ins.get("glucose") or {}).get("glycemic_load")
    avail = (ins.get("glucose") or {}).get("available_carbs_g") or 0
    if (gl is not None and gl >= 20) or (gl is None and avail >= 75):
        flags.append({"severity": 2, "text": "High glycaemic load (refined starch or sugar), which drives larger post-meal glucose rises.",
                      "refs": ["salmeron1997", "atkinson2021"]})
    if (totals.get("fiber_g") or 0) < 5 and kcal > 300:
        flags.append({"severity": 1, "text": "Low fibre: half the plate should be vegetables and fruit.", "refs": ["hpb_plate"]})
    fat = totals.get("fat_g") or 0
    if kcal and fat * 9 / kcal > 0.40:
        flags.append({"severity": 1, "text": f"About {fat * 9 / kcal:.0%} of the energy comes from fat (rich gravy, coconut milk or frying).", "refs": ["hpb_plate"]})
    score = sum(f["severity"] for f in flags)
    major = sum(1 for f in flags if f["severity"] > 1)
    rating = "balanced" if score == 0 else "unhealthy" if major >= 2 or score >= 5 else "needs_attention"
    tips = []
    if rating != "balanced":
        tips = ["Follow My Healthy Plate: ½ vegetables and fruit, ¼ wholegrains, ¼ protein.",
                "Ask for less rice or noodles, less gravy, and 'kosong' or 'siew dai' drinks.",
                "Choose soup or steamed and grilled dishes over deep-fried or coconut-milk dishes more often."]
    return {"rating": rating, "score": score, "flags": flags, "tips": tips}


def forecast(foods: list[dict], totals: dict, ins: dict, profile, scenarios: list[dict], horizon: int = 300) -> dict:
    weight = (profile.weight_kg if profile and profile.weight_kg else None) or DEFAULT_WEIGHT_KG
    k, k_label = _clearance_k(getattr(profile, "diabetes_status", None) if profile else None)
    meal = _meal_inputs(foods, totals)
    base = _simulate(meal, k, weight, None, horizon)
    peak = max(base["series"]) or 1.0
    to_index = lambda s: [round(v / peak * 100, 1) for v in s]
    base_energy = _energy_timeline(meal["kcal"], weight, None, horizon)

    def summarize(sim, idx):
        return {"peak_index": max(idx), "peak_time_min": idx.index(max(idx)) * 5,
                "auc_index": round(sum(idx) * 5 / 60, 1)}

    b_idx = to_index(base["series"])
    baseline = {"name": "Office day (no workout)", "glucose_index": b_idx, "energy_cum_kcal": base_energy["series"],
                **summarize(base, b_idx), "exercise_kcal": 0, "cho_oxidised_g": 0}
    out_scen = []
    for sc in scenarios:
        sim = _simulate(meal, k, weight, sc, horizon)
        idx = to_index(sim["series"])
        en = _energy_timeline(meal["kcal"], weight, sc, horizon)
        a = ACTIVITIES[sc["activity"]]
        met = a[sc["intensity"]]
        net = (met - SITTING_MET) * weight * sc["duration_min"] / 60
        s = summarize(sim, idx)
        out_scen.append({
            "name": f"{a['label'].split(' (')[0]} · {sc['intensity']} · {sc['duration_min']} min at +{sc['start_min']} min",
            **sc, "met": met, "glucose_index": idx, "energy_cum_kcal": en["series"], **s,
            "peak_change_pct": round((s["peak_index"] - 100), 1),
            "auc_change_pct": round((s["auc_index"] / baseline["auc_index"] - 1) * 100, 1) if baseline["auc_index"] else 0,
            "exercise_kcal": sim["exercise_kcal"], "net_extra_kcal": round(net, 1),
            "cho_oxidised_g": sim["cho_oxidised_g"], "meal_glucose_taken_up_g": sim["meal_glucose_taken_up_g"],
            "share_of_meal_energy_pct": round(net / meal["kcal"] * 100) if meal["kcal"] else None,
            "cautions": _cautions(sc, meal, profile, horizon),
        })
    offset = {key: round(meal["kcal"] / ((a["moderate"] - SITTING_MET) * weight / 60)) if meal["kcal"] and a["moderate"] > SITTING_MET else None
              for key, a in ACTIVITIES.items() if key != "sitting"}
    return {
        "disclaimer": "Educational simulation from population-average physiology. It is NOT a prediction of your blood "
                      "glucose and not medical advice. Individual responses vary widely (sleep, stress, medication, "
                      "fitness, insulin sensitivity). Use a glucose meter or CGM and your care team's guidance.",
        "time_min": list(range(0, horizon + 1, 5)),
        "inputs": {**meal, "body_mass_kg": weight, "body_mass_source": "profile" if profile and profile.weight_kg else "default 70 kg",
                   "clearance": k_label, "clearance_half_life_min": round(math.log(2) / k)},
        "baseline": baseline, "scenarios": out_scen,
        "energy": {"meal_kcal": meal["kcal"], "tef_kcal": round(meal["kcal"] * 0.10, 1),
                   "sitting_kcal_per_hour": round(SITTING_MET * weight, 1),
                   "hours_sitting_to_use_meal_energy": round(meal["kcal"] / (SITTING_MET * weight), 1) if meal["kcal"] else None,
                   "minutes_moderate_activity_to_offset_meal": offset},
        "advisory": meal_advisory(totals, ins, foods),
        "equations": [
            "Activity energy: E (kcal) = MET × body mass (kg) × time (h); 1 MET ≈ 3.5 mL O₂/kg/min ≈ 1 kcal/kg/h [ainsworth2011]",
            "Extra energy over desk work = (MET − 1.5) × kg × h [ainsworth2011]",
            "Carbohydrate oxidised (g) = E × f_CHO ÷ 4 kcal/g [fao2003, brooks1994, romijn1993]",
            "Glucose mass balance: dG/dt = Ra(t) − k·G − U_ex(t); Ra = meal glycaemic carbohydrate × gamma absorption curve [atkinson2021]",
            "Thermic effect of food ≈ 10% of meal energy [westerterp2004]",
        ],
        "assumptions": ASSUMPTIONS,
        "references": REFERENCES,
        "activities": {k: {"label": v["label"], "moderate_met": v["moderate"], "high_met": v["high"]}
                       for k, v in ACTIVITIES.items() if k != "sitting"},
    }


SIM_VERSION = "meal-sim 1.0 (gamma absorption + first-order clearance; Atkinson 2021 GI/GL)"
WHATIF_NUTRIENTS = ("calories_kcal", "carbs_g", "sugar_g", "protein_g", "fat_g", "sat_fat_g", "fiber_g", "sodium_mg")


def _gl(nutrients: dict, key: str | None) -> float | None:
    ref = nutrition.get(key)
    if not ref or ref.get("glycemic_index") is None:
        return None
    avail = max((nutrients.get("carbs_g") or 0) - (nutrients.get("fiber_g") or 0), 0)
    return round(ref["glycemic_index"] * avail / 100, 1)


def _diff(a, b):
    if a is None or b is None:
        return {"abs": None, "pct": None}
    return {"abs": round(b - a, 1), "pct": round((b - a) / a * 100, 1) if a else None}


def portion_whatif(items: list[dict], profile, horizon: int = 240) -> dict:
    """Original vs modified portions (nothing is saved). items: {id, label, nutrition_key, grams, new_grams, range_g}.
    The glucose curves are a relative index (original peak = 100), not mmol/L. The band around the modified curve
    re-runs the simulation at the low and high ends of each food's portion-uncertainty range; it reflects portion
    uncertainty only, not individual physiological variation."""
    weight = (profile.weight_kg if profile and profile.weight_kg else None) or DEFAULT_WEIGHT_KG
    k, k_label = _clearance_k(getattr(profile, "diabetes_status", None) if profile else None)

    def build(grams_of):
        foods = [{"label": it["label"], "nutrition_key": it["nutrition_key"], "grams": grams_of(it),
                  "nutrients": nutrition.compute(it["nutrition_key"], grams_of(it))} for it in items]
        return foods, insights.totals(foods)

    def scaled(it, end):
        r = it.get("range_g")
        if not r or not it["grams"]:
            return it["new_grams"]
        return it["new_grams"] * r[end] / it["grams"]

    runs = {name: build(fn) for name, fn in (("original", lambda it: it["grams"]), ("modified", lambda it: it["new_grams"]),
                                             ("low", lambda it: scaled(it, 0)), ("high", lambda it: scaled(it, 1)))}
    sims = {name: _simulate(_meal_inputs(f, t), k, weight, None, horizon) for name, (f, t) in runs.items()}
    peak = max(sims["original"]["series"]) or 1.0
    idx = {name: [round(v / peak * 100, 1) for v in s["series"]] for name, s in sims.items()}

    def summary(name):
        f, t = runs[name]
        gls = [_gl(x["nutrients"], x["nutrition_key"]) for x in f]
        carb_items = [x for x in f if (x["nutrients"].get("carbs_g") or 0) >= 5]
        return {**{n: t[n] for n in WHATIF_NUTRIENTS}, "grams": t["grams"],
                "glycemic_load": round(sum(g for g in gls if g is not None), 1) if any(g is not None for g in gls) else None,
                "gl_coverage": f"{sum(1 for x, g in zip(f, gls) if g is not None and x in carb_items)}/{len(carb_items)} carbohydrate foods have a GI value",
                "peak_index": max(idx[name]), "peak_time_min": idx[name].index(max(idx[name])) * 5,
                "auc_index": round(sum(idx[name]) * 5 / 60, 1)}

    orig, mod = summary("original"), summary("modified")
    foods = []
    for it, fo, fm in zip(items, runs["original"][0], runs["modified"][0]):
        o = {**fo["nutrients"], "grams": fo["grams"], "glycemic_load": _gl(fo["nutrients"], it["nutrition_key"])}
        m = {**fm["nutrients"], "grams": fm["grams"], "glycemic_load": _gl(fm["nutrients"], it["nutrition_key"])}
        foods.append({"id": it["id"], "label": it["label"], "original": o, "modified": m,
                      "diff": {n: _diff(o.get(n), m.get(n)) for n in (*WHATIF_NUTRIENTS, "grams", "glycemic_load")}})
    return {
        "simulation_version": SIM_VERSION, "kind": "simulated",
        "time_min": list(range(0, horizon + 1, 5)),
        "curves": {"original": idx["original"], "modified": idx["modified"],
                   "modified_low": [min(a, b) for a, b in zip(idx["low"], idx["high"])],
                   "modified_high": [max(a, b) for a, b in zip(idx["low"], idx["high"])]},
        "band": "portion-uncertainty range of each food (low–high grams); not physiological variation",
        "foods": foods, "totals": {"original": orig, "modified": mod,
                                   "diff": {n: _diff(orig.get(n), mod.get(n)) for n in (*WHATIF_NUTRIENTS, "grams", "glycemic_load", "peak_index", "auc_index")}},
        "assumptions": [f"Clearance: {k_label}, half-life {round(math.log(2) / k)} min", f"Body mass {weight} kg",
                        f"Foods without a GI value use an assumed GI of {DEFAULT_GI}",
                        "Curves are a relative index (original peak = 100), not blood-glucose concentrations",
                        "Nutrients scale linearly with grams from the same reference record"],
        "disclaimer": "Illustrative simulation from population-average physiology — not a prediction of your blood glucose "
                      "and not medical advice. Do not use it to adjust medication or insulin.",
    }
