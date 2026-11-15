"""Shared helpers: load config and plant data, validate them."""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "plants.yaml"
CONFIG_FILE = ROOT / "config.yaml"
QR_DIR = ROOT / "qr"
LOCK_FILE = QR_DIR / "slugs.lock"   # slugs that already have QR codes (never remove)
SLUG_RE = re.compile(r"^[a-z]+(-[a-z]+)+$")

OPTIONAL_TEXT_FIELDS = [
    # (yaml key, heading shown on the page)
    ("description", "Description"),
    ("uses", "Uses"),
    ("native_to", "Native to"),
    ("flowering_season", "Flowering season"),
    ("notes", "Notes"),
]


def fail(msg):
    sys.exit(f"ERROR: {msg}")


def load_config():
    cfg = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    cfg["base_url"] = str(cfg["base_url"]).rstrip("/")
    return cfg


def page_url(cfg, slug):
    """The permanent URL encoded in the QR code."""
    return f"{cfg['base_url']}/p/{slug}/"


def locked_slugs():
    if not LOCK_FILE.exists():
        return []
    return [s.strip() for s in LOCK_FILE.read_text().splitlines()
            if s.strip() and not s.startswith("#")]


def load_plants():
    data = yaml.safe_load(DATA_FILE.read_text(encoding="utf-8"))
    plants = data.get("plants") or []
    seen = set()
    for i, p in enumerate(plants, 1):
        where = f"data/plants.yaml entry #{i}"
        for key in ("slug", "scientific_name", "family"):
            if not p.get(key):
                fail(f"{where} is missing '{key}'")
        slug = p["slug"]
        if not SLUG_RE.match(slug):
            fail(f"{where}: slug '{slug}' must be lowercase words joined by hyphens")
        if slug in seen:
            fail(f"{where}: slug '{slug}' is used twice")
        seen.add(slug)
        names = p.get("common_names") or []
        if isinstance(names, str):
            names = [n.strip() for n in names.split(",") if n.strip()]
        p["common_names"] = names
        photos = p.get("photos") or []
        p["photos"] = [ph if isinstance(ph, dict) else {"file": ph} for ph in photos]
        for ph in p["photos"]:
            if not (ROOT / "photos" / ph["file"]).exists():
                fail(f"{where} ({slug}): photo file photos/{ph['file']} not found")
    missing = [s for s in locked_slugs() if s not in seen]
    if missing:
        fail("These slugs already have printed QR codes and must not be removed or "
             "renamed: " + ", ".join(missing))
    return plants
