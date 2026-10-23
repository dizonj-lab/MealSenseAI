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


def get(key: str | None) -> dict | None:
    return _db()["foods"].get(key) if key else None


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
    hit = cache.get(ck)
    if hit is not None:
        return hit
    f = get(key)
    per = f["per_100g"]
    out = {n: (None if per.get(n) is None else round(per[n] * grams / 100, 1)) for n in NUTRIENTS}
    cache.set(ck, out, ttl=86400)
    return out


def source_info(key: str) -> dict:
    f = get(key)
    return {"table": f"MealSenseAI reference table {version()}", "record": f["key"], "name": f["name"],
            "source": f["source"], "verification": f["verification"],
            "glycemic_index": f["glycemic_index"], "gi_source": f["gi_source"]}


def empty_nutrients() -> dict:
    return {n: None for n in NUTRIENTS}
