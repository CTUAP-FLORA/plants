"""Generate one PNG and one SVG QR code per plant in qr/.

Each QR code encodes ONLY the permanent page URL:  <base_url>/p/<slug>/
Error correction level H (30% of the code can be damaged and still scan).

Usage:  python scripts/make_qr.py
"""
import qrcode
import qrcode.image.svg

from common import LOCK_FILE, QR_DIR, load_config, load_plants, page_url


def make(url):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=20, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    return qr


def main():
    cfg = load_config()
    plants = load_plants()
    QR_DIR.mkdir(exist_ok=True)
    for p in plants:
        url = page_url(cfg, p["slug"])
        make(url).make_image(fill_color="black", back_color="white").save(QR_DIR / f"{p['slug']}.png")
        make(url).make_image(image_factory=qrcode.image.svg.SvgPathImage).save(str(QR_DIR / f"{p['slug']}.svg"))
    # Record every slug that now has a QR code, so the build refuses to drop one later.
    LOCK_FILE.write_text(
        "# Slugs that have QR codes. Do not edit. The build fails if any of these disappear\n"
        "# from data/plants.yaml, because printed tags point to them.\n"
        + "\n".join(sorted(p["slug"] for p in plants)) + "\n")
    print(f"Wrote {len(plants)} PNG + {len(plants)} SVG QR codes to qr/ for {cfg['base_url']}")


if __name__ == "__main__":
    main()
