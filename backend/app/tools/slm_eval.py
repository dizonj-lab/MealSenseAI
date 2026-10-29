"""Evaluate the local language model (Ollama) on the four jobs MealSenseAI gives it, with fixed inputs and known answers.

    docker compose exec -T backend python -m app.tools.slm_eval > slm_eval.json

Read-only: nothing is written to the database (the SLM call log and the response cache are bypassed), so it is safe
on the live server. Takes a few minutes on a CPU. A summary goes to stderr, the full results to stdout as JSON.

  1. parse      meal descriptions → foods, against the rule-based splitter (both mapped with nutrition.lookup)
  2. match      names the food table does not know → a catalog key, or null when nothing is close
  3. explain    plain-language meal explanations: every number must come from the facts (the advisor's own validator)
  4. rewrite    Meal Advisor drafts reworded in the persona: validator pass rate (numbers, food names, safety)
"""
import json
import platform
import statistics
import sys
import time

from app.services import advisor, analysis, insights, nutrition, persona, slm, tuning

# ---- fixed inputs and expected answers (catalog keys of datasets/nutrition/foods.json)
PARSE = [
    ("chicken rice and teh tarik", {"chicken_rice", "teh_tarik"}),
    ("2 roti prata with teh tarik", {"roti_prata", "teh_tarik"}),
    ("nasi lemak, fried egg and kopi", {"nasi_lemak", "fried_egg", "kopi"}),
    ("char kway teow", {"char_kway_teow"}),
    ("laksa plus iced milo", {"laksa", "milo"}),
    ("kaya toast with 2 soft boiled eggs and kopi", {"kaya_toast", "boiled_egg", "kopi"}),
    ("bak chor mee and a coke", {"bak_chor_mee", "cola"}),
    ("wanton mee", {"wanton_mee"}),
    ("I had mee goreng and some satay", {"mee_goreng", "chicken_satay"}),
    ("fishball noodles with a glass of orange juice", {"fishball_noodles", "orange_juice"}),
    ("yong tau foo", {"yong_tau_foo"}),
    ("spaghetti bolognese and a green salad", {"spaghetti_bolognese", "green_salad"}),
    ("cheeseburger with french fries and coke", {"cheeseburger", "french_fries", "cola"}),
    ("duck rice and bubble tea", {"duck_rice", "bubble_tea"}),
    ("half a plate of hokkien mee", {"hokkien_mee"}),
    ("oatmeal with banana for breakfast", {"oatmeal", "banana"}),
    ("my lunch was sushi and ramen", {"sushi", "ramen"}),
    ("ice kacang", {"ice_kacang"}),
    ("popiah and two curry puffs", {"popiah", "curry_puff"}),
    ("steamed fish, brown rice and stir fried greens", {"steamed_fish", "brown_rice", "stir_fried_greens"}),
]
MATCH = [
    ("otah", "otak"), ("min jiang kueh", "peanut_pancake"), ("soft boiled eggs", "boiled_egg"),
    ("mung bean soup", "tau_suan"), ("kopi peng", "kopi"), ("teh peng", "teh_tarik"),
    ("fishball soup with bee hoon", "fish_soup_beehoon"), ("ang ku kueh", "pung_kueh"),
    ("curry chicken with potatoes", "chicken_curry"), ("roast duck rice", "duck_rice"),
    ("tau huay", None), ("ondeh ondeh", None), ("bandung", None), ("nasi padang", None), ("sugarcane juice", None),
]
MEALS = [   # (food key, grams) — real records, the same arithmetic as the app
    [("chicken_rice", 380), ("teh_tarik", 230)],
    [("nasi_lemak", 350), ("kopi", 230)],
    [("char_kway_teow", 384)],
    [("kaya_toast", 70), ("boiled_egg", 100), ("kopi", 230)],
    [("green_salad", 150), ("chicken_breast", 120), ("brown_rice", 100)],
    [("laksa", 500), ("bubble_tea", 500)],
]
DRAFTS = [   # rule-engine answers, as the app writes them (test-results/advisor_eval.json)
    ("What is in my meal?", "Your lunch has 2 items:\n1. Hainanese chicken rice: 380 g, 608 kcal, 75 g carbs (83% of calories)\n"
     "2. Teh tarik / teh (condensed milk): 230 g, 126 kcal, 21 g carbs (17% of calories)\nTotal: about 734 kcal and 96 g carbs."),
    ("How many carbohydrates did I have?", "Your saved meal has an estimated 96 g of carbohydrate, from Hainanese chicken rice 75 g, "
     "Teh tarik / teh 21 g. Portions are estimated from the photo, so treat this as an estimate."),
    ("What if I remove the teh tarik?", "Hypothetically, without the Teh tarik / teh (condensed milk), the meal would have about 75 g "
     "carbohydrate instead of 96 g (-21 g) and 608 kcal instead of 734. Your saved meal is unchanged; you can apply this in the portion simulator."),
    ("Is nasi lemak healthy?", "Nasi lemak (1 plate, 350 g) has about 644 kcal and 77 g carbohydrate, mostly from coconut rice. "
     "It is high in fat and sodium for one meal. A smaller rice portion with more vegetables lowers the carbohydrate."),
    ("How was my week?", "Over the last 7 days you logged 13 meals. Your average was 1,742 kcal and 214 g carbohydrate a day, "
     "a little above your 200 g goal on 4 of 7 days. Your biggest carbohydrate sources were nasi lemak and char kway teow."),
    ("Can I eat pizza?", "You can fit pizza into a meal plan. Two slices (214 g) have about 571 kcal and 71 g carbohydrate. "
     "Pairing it with a salad and keeping to two slices helps keep the carbohydrate moderate."),
    ("Should I take more insulin?", "I can't advise on insulin or medication doses. Please follow your care team's plan, "
     "and contact them if your readings are unusual."),
    ("What's a lower-carb swap for char kway teow?", "Lower-carb options in the same category as char kway teow: "
     "Sliced fish bee hoon soup (1 bowl, 33 g carbs, 318 kcal); Yong tau foo (soup) (1 bowl, 27 g carbs, 292 kcal)."),
]


def _quiet():
    """No database writes, no cached answers, no back-off between calls."""
    slm._log = lambda *a, **k: None
    slm.cache.get = lambda *a, **k: None
    slm.cache.set = lambda *a, **k: None


def _call(task, system, prompt, schema, timeout=None):
    slm._status["down_until"] = 0
    stats: dict = {}
    t0 = time.perf_counter()
    out = slm.chat_json(task, system, prompt, schema, timeout=timeout, stats=stats)
    return out, round((time.perf_counter() - t0) * 1000), stats


def _prf(found: set, want: set) -> tuple[int, int, int]:
    return len(found & want), len(found - want), len(want - found)


def _rate(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0}


def _lat(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return {"n": len(xs), "mean": round(statistics.mean(xs)), "p50": xs[len(xs) // 2], "p95": xs[min(len(xs) - 1, int(0.95 * len(xs)))]}


def run() -> dict:
    _quiet()
    st = slm.status(force=True)
    if not st["available"]:
        sys.exit(f"The language model is not available: {st['error']}")
    log = lambda m: print(m, file=sys.stderr, flush=True)  # noqa: E731
    out = {"model": st["selected"], "ollama_url": st["url"], "temperature": tuning.get("slm.temperature"),
           "host": platform.machine(), "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    speeds = []

    # 1. parsing descriptions
    rows, slm_t, rule_t = [], [0, 0, 0], [0, 0, 0]
    for text, want in PARSE:
        res, ms, stats = _call("normalize_description", tuning.prompt("meal.parse_description"), text, slm.Mentions)
        found_slm = {nutrition.lookup(m.name)[0] for m in (res.foods if res else [])} - {None}
        slm._status["data"] = {"available": False}   # the rule-based splitter is what runs when the SLM is off
        slm._status["checked"] = time.time()
        rule, _ = analysis._parse_description(text)
        slm._status["checked"] = 0
        found_rule = {nutrition.lookup(n)[0] for n, _ in rule} - {None}
        for agg, found in ((slm_t, found_slm), (rule_t, found_rule)):
            for k, v in enumerate(_prf(found, want)):
                agg[k] += v
        speeds.append(stats.get("tokens_per_s"))
        rows.append({"text": text, "want": sorted(want), "slm": sorted(found_slm), "rules": sorted(found_rule), "ms": ms,
                     "ok": res is not None})
        log(f"parse   {ms:6} ms  {text!r}: slm {sorted(found_slm)} rules {sorted(found_rule)}")
    out["parse"] = {"n": len(PARSE), "slm": _rate(*slm_t), "rules": _rate(*rule_t),
                    "slm_exact_sets": sum(set(r["slm"]) == set(r["want"]) for r in rows),
                    "rules_exact_sets": sum(set(r["rules"]) == set(r["want"]) for r in rows),
                    "latency_ms": _lat([r["ms"] for r in rows]), "failures": sum(not r["ok"] for r in rows), "rows": rows}

    # 2. matching unknown names to the catalog
    catalog = [nutrition.summary(f) for f in nutrition.all_foods()]
    rows = []
    for label, want in MATCH:
        cat = "\n".join(f"{f['key']}: {f['name']}" for f in catalog)
        res, ms, stats = _call("provisional_match", tuning.prompt("meal.provisional_match"), f"Food: {label}\nCatalog:\n{cat}", slm.Match)
        got = res.key if res and res.key and nutrition.get(res.key) else None
        speeds.append(stats.get("tokens_per_s"))
        rows.append({"label": label, "want": want, "slm": got, "lookup": nutrition.lookup(label)[0], "correct": got == want, "ms": ms})
        log(f"match   {ms:6} ms  {label!r}: {got} (want {want})")
    known = [r for r in rows if r["want"]]
    unknown = [r for r in rows if not r["want"]]
    out["match"] = {"n": len(rows), "accuracy": round(sum(r["correct"] for r in rows) / len(rows), 3),
                    "correct_when_in_table": f"{sum(r['correct'] for r in known)}/{len(known)}",
                    "abstained_when_absent": f"{sum(r['correct'] for r in unknown)}/{len(unknown)}",
                    # the baseline: the app's fuzzy text lookup alone, which runs before the SLM is ever asked
                    "lookup_accuracy": round(sum(r["lookup"] == r["want"] for r in rows) / len(rows), 3),
                    "lookup_wrong_match": sum(r["lookup"] is not None and r["lookup"] != r["want"] for r in rows),
                    "slm_wrong_match": sum(r["slm"] is not None and r["slm"] != r["want"] for r in rows),
                    "latency_ms": _lat([r["ms"] for r in rows]), "rows": rows}

    # 3. explanations grounded in the meal's numbers
    rows = []
    for meal in MEALS:
        foods = []
        for key, grams in meal:
            ref = nutrition.get(key)
            foods.append({"label": ref["name"], "grams": grams, "nutrition_key": key, "nutrients": nutrition.compute(key, grams)})
        t, ins = insights.core(foods, None)
        facts = {"foods": [{"name": f["label"], "grams": f["grams"]} for f in foods], "totals": {k: t[k] for k in nutrition.NUTRIENTS},
                 "glucose_level": ins["glucose"]["level"], "glycemic_load": ins["glucose"]["glycemic_load"],
                 "portion_uncertainty": "photo-based estimates, ±35–50%", "user_goals": [],
                 "recommendations": [r["title"] for r in ins["recommendations"]]}
        res, ms, stats = _call("insight_explanation", tuning.prompt("meal.explanation"), json.dumps(facts), slm.Explanation)
        text = res.summary if res else ""
        v = advisor.validate(text, "", facts) if text else {"ok": False}
        speeds.append(stats.get("tokens_per_s"))
        rows.append({"meal": [k for k, _ in meal], "ms": ms, "summary": text, "valid": v["ok"], "check": v, "tokens": stats})
        log(f"explain {ms:6} ms  {[k for k, _ in meal]}: {'grounded' if v['ok'] else 'NOT grounded'}")
    out["explain"] = {"n": len(rows), "grounded": f"{sum(r['valid'] for r in rows)}/{len(rows)}",
                      "latency_ms": _lat([r["ms"] for r in rows]), "rows": rows}

    # 4. Meal Advisor rewording, checked by the same validator the app uses
    rows = []
    system = persona.persona_prompt("careful") + " " + tuning.prompt("advisor.rewrite")
    fx = {"note": "drafts from the rule engine"}
    for msg, draft in DRAFTS:
        prompt = (f"<<FACTS>>\n{json.dumps(fx)}\n<</FACTS>>\n<<CONVERSATION>>\n\n<</CONVERSATION>>\nUSER: {msg}\n"
                  f"<<DRAFT>>\n{draft}\n<</DRAFT>>")
        res, ms, stats = _call("advisor", system, prompt, advisor.Reply, timeout=tuning.get("slm.advisor_timeout_s"))
        reply = res.reply.strip() if res else ""
        v = advisor.validate(reply, draft, fx) if reply else {"ok": False, "failed": True}
        speeds.append(stats.get("tokens_per_s"))
        rows.append({"question": msg, "ms": ms, "reply": reply, "valid": v.get("ok", False), "check": v, "tokens": stats})
        log(f"rewrite {ms:6} ms  {msg!r}: {'shown' if v.get('ok') else 'rule answer used'}")
    out["rewrite"] = {"n": len(rows), "passed_validator": f"{sum(r['valid'] for r in rows)}/{len(rows)}",
                      "latency_ms": _lat([r["ms"] for r in rows]), "rows": rows}

    sp = [s for s in speeds if s]
    out["tokens_per_s"] = {"mean": round(statistics.mean(sp), 1), "min": min(sp), "max": max(sp)} if sp else None
    out["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    log("\nSUMMARY " + json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "rows"} if isinstance(v, dict) else v
                                    for k, v in out.items()}, indent=1))
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
