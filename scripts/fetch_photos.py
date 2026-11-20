"""Download one freely licensed photo per plant from Wikimedia Commons.

The photo is the one Wikidata links to the species (property P18, "image"); if none is usable,
a Commons file named after the species is taken. Only files under
licences that allow reuse with credit (CC0, public domain, CC BY, CC BY-SA) are taken.
Each photo is resized for phones and saved as photos/<slug>-wiki.jpg, and data/photo_credits.json
records the photographer, licence and source page, which the plant page shows under the photo.

Plants that already have a photo of your own in data/plants.yaml are left alone: your own
photos always come first.

Usage:  python scripts/fetch_photos.py                     # all plants without a photo
        python scripts/fetch_photos.py azadirachta-indica  # one plant (replaces its Commons photo)
"""
import html
import io
import json
import re
import sys
import time

import requests
from PIL import Image, ImageOps

import fetch_verified as fv
from common import ROOT, load_plants

PHOTOS = ROOT / "photos"
CREDITS = ROOT / "data" / "photo_credits.json"
OK_LICENCE = re.compile(r"^(cc0|public domain|pd|copyrighted free use|cc[ -]by(-sa)?( \d\.\d)?)", re.I)
THUMB_WIDTHS = (1280, 960, 500)     # Wikimedia's standard thumbnail sizes, largest first
WIDTH = 1200
# Wikimedia asks automated tools to say who they are, with a contact address, and to go slowly.
WM_UA = {"User-Agent": "CampusFloraBuild/1.0 (https://ctuap-flora.github.io/plants/; botanical garden plant labels) python-requests"}


def wm_get(url, params=None, tries=6):
    """GET from Wikimedia, waiting as long as it asks (Retry-After) when it is busy."""
    for i in range(tries):
        r = requests.get(url, params=params, headers=WM_UA, timeout=60)
        if r.status_code in (429, 503):
            wait = min(int(r.headers.get("Retry-After", "0") or 0) or 10 * (i + 1), 120)
            print(f"    Wikimedia busy ({r.status_code}) for {url.split('/')[2]}: waiting {wait}s", flush=True)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()


def commons_info(filename, width=1280):
    r = wm_get("https://commons.wikimedia.org/w/api.php",
               {"action": "query", "titles": "File:" + filename, "prop": "imageinfo", "format": "json",
                "iiprop": "url|extmetadata|mime|size",
                "iiurlwidth": width}).json()        # a standard thumbnail size, as Wikimedia asks
    page = next(iter(r["query"]["pages"].values()))
    if "imageinfo" not in page:
        return None
    ii = page["imageinfo"][0]
    meta = ii.get("extmetadata", {})

    def m(k):
        return re.sub(r"<[^>]+>", "", html.unescape(meta.get(k, {}).get("value", ""))).strip()
    return {"file": filename, "thumb": ii.get("thumburl") or ii["url"], "page": ii.get("descriptionurl"),
            "mime": ii.get("mime"), "artist": m("Artist") or "Unknown", "licence": m("LicenseShortName"),
            "licence_url": m("LicenseUrl")}


def images_for(p):
    g = fv.safe(fv.gbif_match, p["scientific_name"])
    taxa = fv.safe(fv.wikidata_taxa, p, g)
    if not taxa:
        return []
    files = []
    for item in taxa.split():          # one item at a time: the multi-item form misbehaves on Wikidata's server
        rows = fv.safe(fv.sparql, f"SELECT ?img WHERE {{ {item} wdt:P18 ?img }} LIMIT 5") or []
        for r in rows:
            v = r["img"]["value"]
            if "Special:FilePath/" in v:
                files.append(requests.utils.unquote(v.rsplit("/", 1)[1]).replace("_", " "))
        time.sleep(1)
    return list(dict.fromkeys(files))


def commons_search(p, limit=8):
    """Fallback: photos on Commons whose file name contains the scientific name."""
    r = wm_get("https://commons.wikimedia.org/w/api.php",
               {"action": "query", "list": "search", "srnamespace": 6, "srlimit": limit, "format": "json",
                "srsearch": f'intitle:"{p["scientific_name"]}" filetype:bitmap'}).json()
    return [h["title"].split(":", 1)[1] for h in r.get("query", {}).get("search", [])]


def main():
    only = set(sys.argv[1:])
    credits = json.loads(CREDITS.read_text()) if CREDITS.exists() else {}
    for p in load_plants():
        slug = p["slug"]
        if only and slug not in only:
            continue
        if p["photos"] and not only:
            continue
        if slug in credits and not only:
            continue
        got = None
        for fname in images_for(p) + commons_search(p):
            time.sleep(2)
            info = fv.safe(commons_info, fname)
            # a file smaller than the size asked for comes back as the original, which Wikimedia
            # blocks for tools: ask for the next standard size down until it is a real thumbnail
            for w in THUMB_WIDTHS[1:]:
                if not info or "/thumb/" in info["thumb"]:
                    break
                time.sleep(2)
                info = fv.safe(commons_info, fname, w)
            if info and "/thumb/" not in info["thumb"]:
                print(f"  - skip {fname}: no thumbnail available")
                continue
            if not info or not (info["mime"] or "").startswith("image/") or not OK_LICENCE.match(info["licence"] or ""):
                print(f"  - skip {fname}: {info and info['licence']}")
                continue
            got = info
            break
        if not got:
            print(f"{slug}: no usable photo")
            continue
        try:
            raw = wm_get(got["thumb"]).content
        except requests.RequestException as ex:
            print(f"{slug}: download failed ({ex}); run again later for this plant")
            continue
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        if max(im.size) > WIDTH:                    # longest side at most 1200 px
            k = WIDTH / max(im.size)
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        out = PHOTOS / f"{slug}-wiki.jpg"
        im.save(out, "JPEG", quality=74, optimize=True, progressive=True)
        credits[slug] = {k: got[k] for k in ("file", "page", "artist", "licence", "licence_url")}
        credits[slug]["photo"] = out.name
        print(f"{slug}: {got['file']} | {got['artist'][:40]} | {got['licence']} | {out.stat().st_size // 1024} KB")
        CREDITS.write_text(json.dumps(credits, indent=1, ensure_ascii=False), encoding="utf-8")   # save as we go
        time.sleep(4)
    CREDITS.write_text(json.dumps(credits, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
