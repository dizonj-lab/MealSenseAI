"""Stage 3: portion estimation. Honest by construction: without a known scale or depth,
grams come from typical serving sizes with wide uncertainty bands."""
import re

UNCERTAINTY = {"low": 0.15, "medium": 0.35, "high": 0.5}
REFERENCE_OBJECTS = {
    "none": "No reference",
    "dinner_plate": "Standard dinner plate (~26 cm)",
    "rice_bowl": "Rice bowl (~11 cm)",
    "credit_card": "Credit card",
    "hand": "Hand / palm",
}
TYPICAL_FILL = {"dinner_plate": 0.30, "rice_bowl": 0.55}
SIZE_WORDS = {"half": 0.5, "small": 0.7, "large": 1.3, "big": 1.3, "double": 2.0, "extra large": 1.6}


def size_hint(note: str | None) -> tuple[float, str | None]:
    if not note:
        return 1.0, None
    n = note.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:x|pieces?|pcs|servings?|portions?|plates?|bowls?|cups?|sticks?)\b", n)
    if m:
        return float(m.group(1)), f"user hint '{m.group(0)}'"
    for w in sorted(SIZE_WORDS, key=len, reverse=True):
        if w in n:
            return SIZE_WORDS[w], f"user hint '{w}'"
    return 1.0, None


def _band(grams: float, level: str) -> dict:
    u = UNCERTAINTY[level]
    return {"uncertainty": level, "range_g": [round(grams * (1 - u)), round(grams * (1 + u))],
            "relative_error": f"±{int(u * 100)}%"}


def user_entered(grams: float) -> dict:
    return {"method": "user_entered", **_band(grams, "low"),
            "notes": ["Portion entered by user; accuracy depends on how it was measured."]}


def estimate(food: dict, *, bbox=None, area_frac=None, containers=None, reference_object=None, n_views=1,
             note: str | None = None, servings: float = 1.0, instances: int = 1, has_mask: bool = False) -> tuple[float, dict]:
    base = food["default_serving_g"]
    mult, hint = size_hint(note)
    mult *= servings
    notes = [f"Typical serving prior: {base} g ({food['serving_desc']})."]
    level, method = "high", "typical_serving"
    if instances > 1:
        mult *= instances
        notes.append(f"{instances} separate instances detected; counted as {instances} servings.")

    ref = reference_object if reference_object in TYPICAL_FILL else None
    container = None
    if bbox and ref:
        want = {"bowl"} if ref == "rice_bowl" else {"dining table", "bowl"}
        container = max((c for c in (containers or []) if c["label"] in want),
                        key=lambda c: c.get("area_frac") or c["bbox"]["w"] * c["bbox"]["h"], default=None)
    if container:
        food_area = area_frac if area_frac is not None else bbox["w"] * bbox["h"]
        cont_area = container.get("area_frac") or container["bbox"]["w"] * container["bbox"]["h"]
        ratio = food_area / max(cont_area, 1e-6)
        factor = max(0.5, min(2.0, ratio / TYPICAL_FILL[ref]))
        mult *= factor
        level, method = "medium", "mask_area_ratio" if has_mask else "box_area_ratio"
        notes.append(f"Food {'mask' if has_mask else 'box'} covers ~{ratio:.0%} of the detected {container['label']} "
                     f"({REFERENCE_OBJECTS[ref]}); scaled serving by {factor:.2f}× (area only, thickness unknown).")
    elif ref:
        notes.append("Reference object selected but not located by the detector; area scaling skipped.")
    if hint:
        notes.append(f"Applied {hint} (×{mult:.2f} total).")
    if n_views > 1:
        notes.append("Second view used for detection and review only; no depth/volume reconstruction is performed.")
    notes.append("Photos without a calibrated scale cannot measure volume — please correct grams if known.")
    grams = round(base * mult)
    return grams, {"method": method, **_band(grams, level), "notes": notes}
