"""Local SLM via Ollama (text-only). Used for label normalisation, provisional food matches and
grounded explanations. Never used for nutrient numbers or visual recognition."""
import json
import logging
import time

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core import cache
from app.core.config import settings
from app.core.db import SessionLocal

log = logging.getLogger(__name__)
PREFERRED = ["qwen2.5", "qwen3", "llama3.2", "llama3.1", "phi3", "phi4", "gemma2", "gemma3", "mistral"]
_status = {"checked": 0.0, "data": None}


BACKOFF_S = 300  # after a timeout or error, skip the SLM for 5 minutes (rule-based fallback is used)


def status(force: bool = False) -> dict:
    if time.time() < _status.get("down_until", 0) and not force:
        return {"available": False, "url": settings.ollama_url, "models": [], "selected": None,
                "error": "SLM paused after a timeout/error; using rule-based fallback"}
    if not force and _status["data"] and time.time() - _status["checked"] < 30:
        return _status["data"]
    data = {"available": False, "url": settings.ollama_url, "models": [], "selected": None, "error": None}
    try:
        r = httpx.get(f"{settings.ollama_url}/api/tags", timeout=2)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
        text = [n for n in names if not any(v in n for v in ("embed", "llava", "vision", "clip"))]
        sel = settings.ollama_model if settings.ollama_model in names else next(
            (n for p in PREFERRED for n in text if n.startswith(p)), text[0] if text else None)
        data.update(available=bool(sel), models=names, selected=sel,
                    error=None if sel else "No text model installed in Ollama")
    except Exception as e:
        data["error"] = f"Ollama unreachable at {settings.ollama_url} ({type(e).__name__})"
    _status.update(checked=time.time(), data=data)
    return data


def _log(task, model, ok, ms, tokens=None, extra=None):
    from app.models import InferenceLog
    with SessionLocal() as db:
        db.add(InferenceLog(model_name=model or "ollama", model_version="ollama", task=task, ok=ok,
                            latency_ms=ms, tokens=tokens, extra=extra or {}))
        db.commit()


def chat_json(task: str, system: str, prompt: str, schema: type[BaseModel]):
    st = status()
    if not st["available"]:
        return None
    ck = f"slm:{st['selected']}:{task}:{hash((system, prompt))}"
    if (hit := cache.get(ck)) is not None:
        return schema.model_validate(hit)
    t0 = time.perf_counter()
    try:
        r = httpx.post(f"{settings.ollama_url}/api/chat", timeout=settings.ollama_timeout_s, json={
            "model": st["selected"], "stream": False, "format": schema.model_json_schema(),
            "options": {"temperature": 0.1},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
        r.raise_for_status()
        body = r.json()
        out = schema.model_validate(json.loads(body["message"]["content"]))
        ms = (time.perf_counter() - t0) * 1000
        _log(task, st["selected"], True, ms, body.get("eval_count", 0) + body.get("prompt_eval_count", 0))
        cache.set(ck, out.model_dump(), ttl=86400)
        return out
    except (httpx.HTTPError, ValidationError, json.JSONDecodeError, KeyError) as e:
        _log(task, st["selected"], False, (time.perf_counter() - t0) * 1000, extra={"error": str(e)[:300]})
        if isinstance(e, httpx.HTTPError):
            _status["down_until"] = time.time() + BACKOFF_S
        log.warning("SLM %s failed (%s); pausing SLM for %ss", task, type(e).__name__, BACKOFF_S)
        return None


class FoodMention(BaseModel):
    name: str = Field(description="Generic food or dish name in English, lower case")
    servings: float = Field(default=1.0, ge=0.1, le=10)


class Mentions(BaseModel):
    foods: list[FoodMention]


class Match(BaseModel):
    key: str | None = Field(description="Catalog key of the closest food, or null if none is close")
    reason: str


class Explanation(BaseModel):
    summary: str = Field(description="2-3 sentences, plain language, grounded only in the given numbers")


def parse_description(text: str):
    return chat_json("normalize_description",
                     "Extract the foods and drinks mentioned in a meal description. Normalise local names "
                     "(e.g. Singapore hawker dishes) to common names. Do not invent foods.",
                     text, Mentions)


def suggest_match(label: str, catalog: list[dict]):
    cat = "\n".join(f"{f['key']}: {f['name']}" for f in catalog)
    return chat_json("provisional_match",
                     "Pick the catalog entry that best matches the food. Return null if nothing is a "
                     "reasonable match. Only return keys from the catalog.",
                     f"Food: {label}\nCatalog:\n{cat}", Match)


def explain(facts: dict):
    return chat_json("insight_explanation",
                     "You explain meal nutrition facts for general education. Use ONLY the numbers given. "
                     "Do not predict the person's blood glucose, give medical advice, mention medication, "
                     "or cite studies. Mention uncertainty when stated.",
                     json.dumps(facts), Explanation)
