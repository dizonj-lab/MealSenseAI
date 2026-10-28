"""Stage 4: deterministic nutrition mapping against the sourced composition table."""
import difflib
import json
import re
from functools import lru_cache

from app.core import cache
from app.core.config import settings

NUTRIENTS = ["calories_kcal", "carbs_g", "protein_g", "fat_g", "sat_fat_g", "sugar_g", "fiber_g", "sodium_mg"]


@lru_cache
def _db() -> dict:
    data = json.loads(settings.nutrition_db.read_text())
    foods = {f["key"]: f for f in data["foods"]}
    alias = {}
    for f in data["foods"]:
        for a in [f["key"].replace("_", " "), f["name"].lower(), *f["aliases"]]:
            alias.setdefault(a.lower(), f["key"])
    return {"version": data["version"], "foods": foods, "alias": alias}


def version() -> str:
    return _db()["version"]


CUSTOM: dict[str, dict] = {}   # user-defined foods ("custom_<id>"), loaded from the database (services/custom_foods.py)


def get(key: str | None) -> dict | None:
    if not key:
        return None
    return CUSTOM.get(key) or _db()["foods"].get(key)


def all_foods() -> list[dict]:
    return list(_db()["foods"].values())


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9\- ]", " ", text.lower()).strip()


def lookup(text: str) -> tuple[str | None, str]:
    """Return (key, quality) where quality is exact|fuzzy|none."""
    q = _norm(text)
    if not q:
        return None, "none"
    hit = cache.get(f"lookup:{q}")
    if hit is not None:
        return hit["key"], hit["quality"]
    alias = _db()["alias"]
    if q in alias:
        res = (alias[q], "exact")
    else:
        m = difflib.get_close_matches(q, alias.keys(), n=1, cutoff=0.78)
        if m:
            res = (alias[m[0]], "fuzzy")
        else:  # alias contained as a whole word in the text, longest first
            cands = sorted((a for a in alias if re.search(rf"\b{re.escape(a)}\b", q)), key=len, reverse=True)
            res = (alias[cands[0]], "fuzzy") if cands else (None, "none")
    cache.set(f"lookup:{q}", {"key": res[0], "quality": res[1]}, ttl=86400)
    return res


def search(q: str, limit: int = 12) -> list[dict]:
    qn = _norm(q)
    scored = []
    for f in all_foods():
        names = [f["name"].lower(), *f["aliases"]]
        s = max(difflib.SequenceMatcher(None, qn, n).ratio() + (0.5 if qn and qn in n else 0) for n in names)
        scored.append((s, f))
    scored.sort(key=lambda x: -x[0])
    return [summary(f) for _, f in scored[:limit]]


def summary(f: dict) -> dict:
    return {"key": f["key"], "name": f["name"], "category": f["category"], "region": f["region"],
            "default_serving_g": f["default_serving_g"], "serving_desc": f["serving_desc"]}


def compute(key: str, grams: float) -> dict:
    """Scale per-100 g composition to the portion. Missing values stay None (never invented)."""
    ck = f"nutr2:{key}:{round(grams, 1)}"
    hit = None if key in CUSTOM else cache.get(ck)   # custom foods can be edited: never served from cache
    if hit is not None:
        return hit
    f = get(key)
    per = f["per_100g"]
    out = {n: (None if per.get(n) is None else round(per[n] * grams / 100, 1)) for n in NUTRIENTS}
    if key not in CUSTOM:
        cache.set(ck, out, ttl=86400)
    return out


# A food with no published GI borrows the GI of its main carbohydrate when the name says what that is unambiguously.
# Fixed rules, checked in order (noodles before rice, so "rice noodles" are noodles); no rule means no estimate.
# Where a choice exists the higher-GI staple is used, so a borrowed value errs towards a higher glycaemic load.
GI_RULES: list[tuple[str, str, str | None]] = [   # (pattern on name, aliases and key; reference food; only in this category)
    (r"porridge|congee|\bjook\b|bubur", "porridge", None),
    (r"\b(pau|bao|mantou|steamed bun)", "steamed_bun", None),
    (r"noodle|\bmee\b|\bmee[ _-]|\bmian\b|\bmein\b|kway teow|kuey teow|koay teow|bee hoon|beehoon|vermicelli|hor fun|\bpho\b|ramen|soba|laksa|pad thai|kway chap",
     "udon", None),
    (r"spaghetti|pasta|lasagn|macaroni|penne|fettuccine|linguine|carbonara|bolognese|gnocchi", "pasta", None),
    (r"rice|\bnasi\b|biryani|briyani|lontong|ketupat|risotto|paella|onigiri|bibimbap|donburi", "white_rice", None),
    (r"\bbread\b|toast|\broti\b|prata|naan|chapat+i|paratha|sandwich|burger|\bbun\b|croissant|murtabak|\bpita\b|\bwrap\b|tortilla|hot ?dog",
     "white_bread", None),
    (r"potato|fries|hash ?brown|wedges", "french_fries", None),
    (r"doughnut|donut|you ?tiao|you char kway|churro", "donut", None),
    (r"pancake|waffle|\bapam\b|appam|dosa|thosai|crepe", "pancake", None),
    (r"ice cream|gelato", "ice_cream", None),
    (r"granola|breakfast cereal", "muesli", None),
    (r"juice", "fruit_juice", "beverage"),
    (r".", "cola", "beverage"),   # any other drink with carbohydrate (see SWEET_DRINK_CARBS) is treated as sugar-sweetened
]
SWEET_DRINK_CARBS = 4.0   # g/100 g: water, black coffee, wine and beer stay without a GI
NOT_A_STAPLE = re.compile(r"\bno (noodles?|rice|bread)\b")


def gi_info(key: str | None) -> dict | None:
    """The GI used for a food: its own published value, or one borrowed from a reference food by GI_RULES."""
    f = get(key)
    if not f:
        return None
    if f.get("glycemic_index") is not None:
        return {"value": f["glycemic_index"], "source": f.get("gi_source"), "borrowed_from": None}
    text = " ".join([f["name"], *(f.get("aliases") or []), f["key"].replace("_", " ")]).lower()
    if NOT_A_STAPLE.search(text):
        return None
    for pattern, ref_key, category in GI_RULES:
        ref = _db()["foods"].get(ref_key)
        if category == "beverage" and ((f.get("per_100g") or {}).get("carbs_g") or 0) < SWEET_DRINK_CARBS:
            continue
        if ref and (category is None or f.get("category") == category) and re.search(pattern, text):
            return {"value": ref["glycemic_index"], "source": f"borrowed from {ref['name']} ({ref.get('gi_source')})",
                    "borrowed_from": ref["name"]}
    return None


def source_info(key: str) -> dict:
    f = get(key)
    gi = gi_info(key) or {}
    return {"table": "Your custom foods" if key in CUSTOM else f"MealSenseAI reference table {version()}", "record": f["key"], "name": f["name"],
            "source": f["source"], "verification": f["verification"],
            "glycemic_index": gi.get("value"), "gi_source": gi.get("source"), "gi_borrowed_from": gi.get("borrowed_from")}


def empty_nutrients() -> dict:
    return {n: None for n in NUTRIENTS}
