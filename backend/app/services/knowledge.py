"""Level-4 evidence: the only general health statements the Meal Advisor may use. Each entry is a short, non-diagnostic
statement with its source. Add entries only with a verifiable source; the assistant never cites anything else."""
import re

KNOWLEDGE = {
    "carbs_glucose": {
        "text": "Carbohydrate is the part of food that raises blood glucose the most after a meal. The actual rise depends on "
                "the amount and type of carbohydrate, what it is eaten with, activity, medication and individual metabolism.",
        "source": "American Diabetes Association, Standards of Care in Diabetes (nutrition therapy)",
        "match": r"\b(carbs?|carbohydrates?)\b.*\b(glucose|sugar|spike)|\b(glucose|blood sugar|spike)\b"},
    "gi": {
        "text": "Glycaemic index (GI) ranks carbohydrate foods by how quickly they raise blood glucose compared with pure glucose "
                "(100): low is 55 or less, medium 56–69, high 70 or more.",
        "source": "International Tables of Glycemic Index and Glycemic Load Values (Atkinson et al., 2021)",
        "match": r"\b(gi|glyc(a)?emic index)\b"},
    "gl": {
        "text": "Glycaemic load (GL) combines quality and quantity: GL = GI × available carbohydrate (g) ÷ 100. "
                "Per serving, 10 or less is low, 11–19 medium and 20 or more high.",
        "source": "International Tables of Glycemic Index and Glycemic Load Values (Atkinson et al., 2021)",
        "match": r"\b(gl|glyc(a)?emic load)\b"},
    "fibre": {
        "text": "Adults are advised to eat at least 25 g of naturally occurring dietary fibre a day, from vegetables, fruit, "
                "legumes and wholegrains.",
        "source": "WHO guideline on carbohydrate intake for adults and children (2023)",
        "match": r"\bfib(re|er)\b"},
    "sodium": {
        "text": "WHO recommends less than 2,000 mg of sodium a day for adults (about 5 g of salt).",
        "source": "WHO guideline: Sodium intake for adults and children (2012)",
        "match": r"\b(sodium|salt|salty)\b"},
    "sugar": {
        "text": "WHO recommends keeping free sugars below 10% of total energy, and ideally below 5%. MealSenseAI tracks total "
                "sugar, which also includes natural sugars in fruit and milk.",
        "source": "WHO guideline: Sugars intake for adults and children (2015)",
        "match": r"\b(sugar|sugars|sweet)\b"},
    "sat_fat": {
        "text": "WHO recommends limiting saturated fat to less than 10% of total energy.",
        "source": "WHO guideline: Saturated fatty acid and trans-fatty acid intake (2023)",
        "match": r"\b(saturated|sat(\.)? fat|fat)\b"},
    "plate": {
        "text": "A balanced plate is about half vegetables and fruit, a quarter wholegrains and a quarter protein.",
        "source": "Health Promotion Board Singapore, My Healthy Plate",
        "match": r"\b(balanced|healthy plate|healthier|healthy)\b"},
}


def relevant(text: str, limit: int = 3) -> list[dict]:
    """Approved statements whose topic appears in the text."""
    out = [{"id": k, **{x: v[x] for x in ("text", "source")}} for k, v in KNOWLEDGE.items() if re.search(v["match"], text, re.I)]
    return out[:limit]
