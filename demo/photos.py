"""Choose the demo's meal photos: freely licensed pictures of Singapore hawker dishes.

    python photos.py /demo/photos        # inside the backend image (run.sh does this)

For each dish it searches Wikimedia Commons, keeps only files under a free
licence (CC0, public domain, CC BY, CC BY-SA; never NC or ND), downloads a
1280 px copy, and runs MealSenseAI's own analysis on it. The photo kept is the
one the model recognises best as that dish, with the fewest other regions in the
frame. A dish with no recognised free photo is left out: the demo then logs it
from its description.

Writes photos/<dish>.jpg, photos/credits.json and photos/CREDITS.md (author,
licence and source page of each photo, for the video's description). Choices
already made are kept; delete a file to choose again.
"""

from __future__ import annotations

import html
import io
import json
import re
import sys
import time
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, "/app/backend")
from app.services import vision  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "MealSenseAI-demo/1.0 (portfolio demo video; https://folio.xtangent.ai)"}
FREE = re.compile(r"^(CC0( 1\.0)?|CC BY(-SA)?( [\d.]+)?|Public domain|PD-\S+)$", re.I)
# dish: (Commons searches, labels the model may give it)
DISHES = {
    "chicken_rice": (["Hainanese chicken rice", "chicken rice Singapore"], {"chicken rice"}),
    "nasi_lemak": (["nasi lemak"], {"nasi lemak"}),
    "laksa": (["laksa Singapore", "curry laksa"], {"laksa"}),
    "kaya_toast": (["kaya toast"], {"kaya toast"}),
    "char_kway_teow": (["char kway teow"], {"kway teow", "fried noodles", "hor fun"}),
    "fish_soup": (["sliced fish soup", "fish soup bee hoon"], {"sliced fish soup"}),
    "yong_tau_foo": (["yong tau foo"], {"yong tau foo"}),
    "prata": (["roti prata"], {"indian prata"}),
    "bak_chor_mee": (["bak chor mee"], {"bak chor mee", "mee pok"}),
}
PER_SEARCH = 25


def text(meta: dict, key: str) -> str:
    raw = (meta.get(key) or {}).get("value", "")
    return html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()


def candidates(client: httpx.Client, query: str) -> list[dict]:
    r = client.get(API, params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": PER_SEARCH,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1280})
    r.raise_for_status()
    out = []
    for page in (r.json().get("query", {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licence = text(meta, "LicenseShortName")
        if info.get("mime") not in ("image/jpeg", "image/png") or not FREE.match(licence):
            continue
        if info.get("width", 0) < 800 or not (0.6 <= info["width"] / max(info.get("height", 1), 1) <= 2.0):
            continue
        out.append({"title": page["title"], "url": info.get("thumburl") or info["url"],
                    "page": info.get("descriptionurl"), "licence": licence,
                    "licence_url": text(meta, "LicenseUrl"), "author": text(meta, "Artist") or "Unknown"})
    return out


def judge(path: Path, wanted: set[str]) -> tuple[float, str] | None:
    """How well the model sees `wanted` in the photo: best matching food score, less a little per other region."""
    result = vision.analyze(str(path), "top")
    foods = [i for i in result["items"] if i["kind"] == "food"]
    hits = [i for i in foods if (i.get("model_label") or "") in wanted]
    if not hits:
        return None
    best = max(hits, key=lambda i: i["score"])
    others = len([i for i in result["items"] if i is not best and i["kind"] in ("food", "unknown")])
    return best["score"] - 0.05 * others, f"{best['model_label']} {best['score']:.2f}, {others} other region(s)"


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "photos")
    out.mkdir(parents=True, exist_ok=True)
    work = out / ".candidates"
    work.mkdir(exist_ok=True)
    credits_path = out / "credits.json"
    credits = json.loads(credits_path.read_text()) if credits_path.exists() else {}
    vision.warmup()
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as client:
        for dish, (queries, wanted) in DISHES.items():
            if (out / f"{dish}.jpg").exists() and dish in credits:
                print(f"  {dish:15} kept: {credits[dish]['title']}")
                continue
            seen, best = set(), None
            for q in queries:
                for c in candidates(client, q):
                    if c["title"] in seen:
                        continue
                    seen.add(c["title"])
                    try:
                        raw = client.get(c["url"]).content
                        img = Image.open(io.BytesIO(raw)).convert("RGB")
                    except Exception:  # noqa: BLE001 - a file that will not open is just not a candidate
                        continue
                    path = work / f"{dish}-{len(seen)}.jpg"
                    img.save(path, quality=92)
                    verdict = judge(path, wanted)
                    if verdict and (best is None or verdict[0] > best[0]):
                        best = (verdict[0], verdict[1], path, c)
                    time.sleep(0.2)
            if not best:
                print(f"  {dish:15} no free photo the model recognises ({len(seen)} looked at)")
                continue
            best[2].replace(out / f"{dish}.jpg")
            credits[dish] = {**best[3], "model": best[1]}
            print(f"  {dish:15} {best[1]}  ← {best[3]['title']} ({best[3]['licence']})")
            credits_path.write_text(json.dumps(credits, indent=1, ensure_ascii=False))
    for p in work.iterdir():
        p.unlink()
    work.rmdir()
    lines = ["# Meal photos in the MealSenseAI demo", "",
             "From Wikimedia Commons, under the licences shown. Cropped and resized for the video.", ""]
    for dish, c in sorted(credits.items()):
        lines.append(f"- **{dish.replace('_', ' ')}**: [{c['title'].removeprefix('File:')}]({c['page']}), "
                     f"by {c['author']}, {c['licence']}" + (f" ({c['licence_url']})" if c["licence_url"] else ""))
    (out / "CREDITS.md").write_text("\n".join(lines) + "\n")
    print(f"{len(credits)} of {len(DISHES)} dishes have a photo; credits in {out / 'CREDITS.md'}")


if __name__ == "__main__":
    main()
