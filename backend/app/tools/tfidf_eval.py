"""TF-IDF nearest-neighbour matching of food names, against the app's fuzzy lookup (read-only).

    python -m app.tools.tfidf_eval > tfidf_eval.json

Food names are represented as TF-IDF vectors of character n-grams (3-5, within word boundaries), L2-normalised, and
a query is matched to its nearest alias by cosine similarity (1-nearest-neighbour); below a threshold it abstains.
Two test sets, both with known answers:
  1. the 15 unknown names of the language-model benchmark (slm_eval.MATCH: 10 in the table, 5 absent);
  2. leave-one-alias-out over the food table: each alias of a food with two or more names is removed from the index
     and looked up; the right answer is its own food.
The fuzzy lookup (nutrition.lookup, difflib ratio ≥ 0.78) is the baseline on the same inputs. NumPy only.
"""
import difflib
import json
import math
import re
import sys
from collections import Counter

import numpy as np

from app.services import nutrition
from app.tools.slm_eval import MATCH

THRESHOLDS = (0.3, 0.4, 0.5, 0.6)


def grams(text: str) -> Counter:
    c = Counter()
    for w in re.sub(r"[^a-z0-9 ]", " ", text.lower()).split():
        w = f" {w} "
        for n in (3, 4, 5):
            c.update(w[i:i + n] for i in range(max(1, len(w) - n + 1)))
    return c


class Index:
    def __init__(self, names: list[str]):
        self.names = names
        docs = [grams(n) for n in names]
        df = Counter(g for d in docs for g in d)
        self.vocab = {g: i for i, g in enumerate(df)}
        self.idf = np.array([math.log((1 + len(docs)) / (1 + df[g])) + 1 for g in self.vocab])
        self.M = np.vstack([self.vec(d) for d in docs])

    def vec(self, c: Counter) -> np.ndarray:
        v = np.zeros(len(self.vocab))
        for g, n in c.items():
            if g in self.vocab:
                v[self.vocab[g]] = (1 + math.log(n)) * self.idf[self.vocab[g]]
        return v / (np.linalg.norm(v) or 1)

    def nearest(self, q: str) -> tuple[str, float]:
        s = self.M @ self.vec(grams(q))
        i = int(s.argmax())
        return self.names[i], float(s[i])


def score(rows: list[dict], pred_key: str) -> dict:
    ok = sum(r[pred_key] == r["want"] for r in rows)
    wrong = sum(r[pred_key] is not None and r[pred_key] != r["want"] for r in rows)
    return {"correct": ok, "wrong": wrong, "no_match": len(rows) - ok - wrong, "n": len(rows)}


def run(rows_in: list[tuple[str, str | None]], alias: dict[str, str]) -> list[dict]:
    idx = Index(list(alias))
    out = []
    for q, want in rows_in:
        name, sim = idx.nearest(q)
        out.append({"query": q, "want": want, "tfidf_name": name, "tfidf_key": alias[name], "similarity": round(sim, 3)})
    return out


def main() -> int:
    alias = nutrition._db()["alias"]
    # 1. the 15 unknown names
    rows = run(MATCH, alias)
    for r in rows:
        r["lookup"] = nutrition.lookup(r["query"])[0]
    res1 = {"lookup": score(rows, "lookup")}
    for t in THRESHOLDS:
        for r in rows:
            r[f"tfidf@{t}"] = r["tfidf_key"] if r["similarity"] >= t else None
        res1[f"tfidf@{t}"] = score(rows, f"tfidf@{t}")
    # 2. leave-one-alias-out
    by_food: dict[str, list[str]] = {}
    for a, k in alias.items():
        by_food.setdefault(k, []).append(a)
    loo = []
    for k, names in by_food.items():
        if len(names) < 2:
            continue
        loo += [(a, k) for a in names]
    full = Index(list(alias))
    rows2 = []
    for a, k in loo:
        s = full.M @ full.vec(grams(a))
        s[full.names.index(a)] = -1                      # remove the alias itself from the index
        i = int(s.argmax())
        # baseline on the same task: difflib against the other aliases
        m = difflib.get_close_matches(a, [x for x in alias if x != a], n=1, cutoff=0.78)
        rows2.append({"query": a, "want": k, "tfidf_key": alias[full.names[i]], "similarity": float(s[i]),
                      "lookup": alias[m[0]] if m else None})
    res2 = {"lookup": score(rows2, "lookup")}
    for t in THRESHOLDS:
        for r in rows2:
            r[f"tfidf@{t}"] = r["tfidf_key"] if r["similarity"] >= t else None
        res2[f"tfidf@{t}"] = score(rows2, f"tfidf@{t}")
    out = {"method": "character 3-5-gram TF-IDF, cosine 1-nearest-neighbour; baseline difflib ratio >= 0.78",
           "aliases_indexed": len(alias), "vocabulary": len(full.vocab),
           "unknown_names": {"results": res1, "rows": rows},
           "leave_one_alias_out": {"results": res2, "n": len(rows2), "rows": rows2}}
    json.dump(out, sys.stdout, indent=1, default=str)
    print("\nSUMMARY", json.dumps({"unknown_names": res1, "leave_one_alias_out": res2}), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
