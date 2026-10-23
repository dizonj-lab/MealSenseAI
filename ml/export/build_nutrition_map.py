"""Map each EXP-002 class (exact taxonomy, unchanged IDs) to a nutrition record with an explicit match type.

  exact - the class and the record describe the same food
  proxy - nearest available record; the UI says "approximated using <record>" and invites correction
  none  - no suitable record; the user chooses a food manually
Output: ml/models/exp002/nutrition_map.json and evidence/nutrition_coverage.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services import nutrition  # noqa: E402

# Reviewed overrides: (nutrition_key | None, match)
MANUAL = {
    "alcoholic beverage": ("alcoholic_beverage", "proxy"), "bagel & croissant": ("bagel", "proxy"),
    "baby back ribs": ("char_siew", "proxy"), "beef carpaccio": ("beef_steak", "proxy"), "beef tartare": ("beef_steak", "proxy"),
    "beef noodle soup": ("pho", "proxy"), "beet salad": ("green_salad", "proxy"), "beignets": ("donut", "proxy"),
    "bee hoon, goreng": ("bee_hoon_goreng", "exact"), "bee hoon, soto": ("soto_bee_hoon", "exact"),
    "breakfast burrito": ("burrito", "proxy"), "bubble milk tea": ("bubble_tea", "exact"), "burger": ("cheeseburger", "proxy"),
    "cake": ("chocolate_cake", "proxy"), "cake rolls": ("chocolate_cake", "proxy"), "cannoli": ("cheesecake", "proxy"),
    "caprese salad": ("green_salad", "proxy"), "carrot cake": ("carrot_cake_dessert", "exact"),
    "ceviche": ("sashimi", "proxy"), "chai tow kuay": ("fried_carrot_cake", "exact"), "chap chye, nonya": ("chap_chye", "exact"),
    "cheese fries": ("french_fries", "proxy"), "cheese plate": (None, "none"), "chicken masala": ("chicken_curry", "proxy"),
    "chicken pie": ("pot_pie", "exact"), "chicken quesadilla": ("burrito", "proxy"), "club sandwich": ("sandwich", "proxy"),
    "cooked brown rice": ("brown_rice", "exact"), "cooked white rice": ("white_rice", "exact"), "crab cakes": ("fried_prawn", "proxy"),
    "croque madame": ("sandwich", "proxy"), "deviled eggs": ("boiled_egg", "proxy"), "don, chicken teriyaki": ("chicken_rice", "proxy"),
    "don, unagi": ("duck_rice", "proxy"), "donuts": ("donut", "exact"), "drunken prawn": (None, "none"),
    "dumpling noodle soup": ("ban_mian", "proxy"), "escargots": (None, "none"), "filet mignon": ("beef_steak", "proxy"),
    "foie gras": (None, "none"), "french onion soup": ("vegetable_soup", "proxy"), "greek salad": ("green_salad", "proxy"),
    "grilled cheese sandwich": ("sandwich", "proxy"), "grilled salmon": ("salmon", "exact"), "salmon grilled": ("salmon", "exact"),
    "hamburger": ("cheeseburger", "proxy"), "hot and sour soup": ("vegetable_soup", "proxy"), "huevos rancheros": ("omelette", "proxy"),
    "ice cream chocolate": ("ice_cream", "proxy"), "ice cream vanilla": ("ice_cream", "exact"), "indian prata": ("roti_prata", "exact"),
    "instant cereal drink": ("milo", "proxy"), "kebab beef": ("beef_steak", "proxy"), "kebab chicken": ("roast_chicken", "proxy"),
    "kopi teh milo": ("kopi", "proxy"), "lobster bisque": ("cream_soup", "proxy"), "lobster roll sandwich": ("sandwich", "proxy"),
    "mee siam, fried": ("mee_siam", "proxy"), "miso ramen, with fishcake": ("ramen", "exact"), "miso soup": ("consomme", "proxy"),
    "mushroom soup": ("cream_soup", "proxy"), "clam chowder": ("cream_soup", "proxy"), "pasta fettuccine": ("pasta", "proxy"),
    "pasta red sauce": ("spaghetti_bolognese", "proxy"), "pilaf, pea": ("nasi_goreng", "proxy"), "poutine": ("french_fries", "proxy"),
    "prime rib": ("beef_steak", "proxy"), "pulled pork sandwich": ("sandwich", "proxy"), "red velvet cake": ("chocolate_cake", "proxy"),
    "rice, chicken katsu with japanese curry": ("katsudon", "proxy"), "rice, korean bulgogi beef": ("duck_rice", "proxy"),
    "rice, with dakgalbi": ("duck_rice", "proxy"), "seafood noodles soup": ("prawn_noodle_soup", "proxy"),
    "seaweed salad": ("green_salad", "proxy"), "seaweed snack": (None, "none"), "shrimp and grits": (None, "none"),
    "sirloin steak": ("beef_steak", "exact"), "soft boiled eggs": ("boiled_egg", "exact"),
    "strawberry shortcake": ("chocolate_cake", "proxy"), "tandoori chicken": ("roast_chicken", "proxy"),
    "tom yum noodle soup": ("prawn_noodle_soup", "proxy"), "tuna tartare": ("sashimi", "proxy"), "tumpeng": ("nasi_ambeng", "proxy"),
    "wanton mee, dry": ("wanton_mee", "exact"), "whole wheat": ("whole_grain_bread", "proxy"), "steak": ("beef_steak", "exact"),
    "dumpling": ("dumpling", "exact"), "spring rolls": ("spring_roll_fried", "exact"), "chicken soup": ("chicken_soup", "exact"),
    "kway teow": ("kway_teow_plain", "exact"), "fried noodles": ("mee_goreng", "proxy"), "sweets": ("candy", "exact"),
    "chicken wing": ("chicken_wing", "exact"), "green leafy vegetables": ("stir_fried_greens", "exact"),
    "fish ball noodles": ("fishball_noodles", "exact"), "mee pok": ("fishball_noodles", "exact"), "rice dumpling": ("rice_dumpling", "exact"),
    "porridge": ("porridge", "exact"), "sliced fish soup": ("sliced_fish_soup", "exact"),
    "tacos and nachos": ("tacos", "proxy"), "kueh lapis rainbow": ("kueh_lapis", "proxy"), "macaroni": ("pasta", "exact"),
    "salad": ("green_salad", "proxy"), "sandwich": ("sandwich", "proxy"), "corn": ("corn", "exact"),
}


def main():
    nutrition._db.cache_clear()
    tax = json.loads((ROOT / "ml/models/exp002/class_mapping.json").read_text())
    out = {}
    for name, idx in sorted(tax.items(), key=lambda kv: kv[1]):
        if name in MANUAL:
            key, match = MANUAL[name]
        else:
            k, q = nutrition.lookup(name)
            key, match = (k, "exact") if q == "exact" else (None, "none")
        if key and not nutrition.get(key):
            raise SystemExit(f"{name}: unknown nutrition key {key}")
        rec = nutrition.get(key)
        out[name] = {"class_id": idx, "nutrition_key": key, "match": match,
                     "record_name": rec["name"] if rec else None,
                     "record_verification": rec["verification"] if rec else None}
    (ROOT / "ml/models/exp002/nutrition_map.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    c = Counter(v["match"] for v in out.values())
    cov = {"classes": len(out), "by_match": dict(c), "none": sorted(k for k, v in out.items() if v["match"] == "none"),
           "nutrition_table_version": nutrition.version(), "nutrition_records": len(nutrition.all_foods())}
    (ROOT / "ml/models/exp002/evidence/nutrition_coverage.json").write_text(json.dumps(cov, indent=2))
    print(json.dumps(cov, indent=2))


if __name__ == "__main__":
    main()
