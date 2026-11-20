"""Check that everything is correct BEFORE printing.

  1. Every qr/<slug>.png decodes to exactly <base_url>/p/<slug>/ with two
     independent readers (zxing-cpp and OpenCV), at error correction level H
  2. Every QR code inside tags.pdf decodes to the right URL (if tags.pdf exists
     and pdftoppm is installed)
  3. (--online) Every page URL loads (HTTP 200) and shows the right plant

Usage:  python scripts/verify.py            # offline checks
        python scripts/verify.py --online   # also fetch every live page
Needs:  pip install zxing-cpp opencv-python-headless pillow requests
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import zxingcpp
from PIL import Image

from common import QR_DIR, ROOT, load_config, load_plants, page_url


def decode_all(path):
    """All QR codes in an image (zxing-cpp): list of (text, ec_level)."""
    return [(r.text, r.ec_level) for r in zxingcpp.read_barcodes(Image.open(path))]


def decode_opencv(path):
    return cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(path)))[0]


def main():
    online = "--online" in sys.argv
    cfg = load_config()
    plants = load_plants()
    errors = 0

    for p in plants:
        want = page_url(cfg, p["slug"])
        png = QR_DIR / f"{p['slug']}.png"
        got, cv = decode_all(png), decode_opencv(png)
        if got != [(want, "H")] or cv != want:
            errors += 1
            print(f"QR FAIL  {p['slug']}: zxing {got}, opencv {cv!r}, expected {want} at level H")
        if not (QR_DIR / f"{p['slug']}.svg").exists():
            errors += 1
            print(f"MISSING  qr/{p['slug']}.svg")
    print(f"QR PNGs: checked {len(plants)}")

    pdf = ROOT / "tags.pdf"
    if pdf.exists():
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["pdftoppm", "-r", "200", "-png", str(pdf), f"{tmp}/pg"], check=True)
            found = []
            for img in sorted(Path(tmp).glob("pg*.png")):
                found += [t for t, _ in decode_all(img)]
        want = sorted(page_url(cfg, p["slug"]) for p in plants for _ in range(int(p.get("copies") or 1)))
        if sorted(found) != want:
            errors += 1
            print(f"PDF FAIL: decoded {len(found)} codes; missing {sorted(set(want) - set(found))}, "
                  f"unexpected {sorted(set(found) - set(want))}")
        print(f"tags.pdf: decoded {len(found)} QR codes")

    if online:
        import requests
        for p in plants:
            url = page_url(cfg, p["slug"])
            try:
                r = requests.get(url, timeout=20)
                ok = r.status_code == 200 and p["scientific_name"] in r.text
            except requests.RequestException as ex:
                ok, r = False, ex
            if not ok:
                errors += 1
                print(f"PAGE FAIL {url}: {getattr(r, 'status_code', r)}")
        print(f"Live pages: checked {len(plants)}")

    print("ALL CHECKS PASSED" if not errors else f"{errors} PROBLEM(S) FOUND")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
