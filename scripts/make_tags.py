"""Make tags.pdf: printable A4 sheet, 5 tags per page, with dashed cut lines.

Each tag: scientific name (italic), synonym if any, common names, family,
QR code on the right, university name in small text.
The QR code is drawn as vector squares (sharp at any print size) from the
same qrcode data and settings as scripts/make_qr.py.

Usage:  python scripts/make_tags.py
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from common import ROOT, load_config, load_plants, page_url
from make_qr import make

PAGE_W, PAGE_H = A4
MARGIN = 10 * mm
ROWS = 5
TAG_W = PAGE_W - 2 * MARGIN                 # 190 mm
TAG_H = (PAGE_H - 2 * MARGIN) / ROWS        # 55.4 mm
PAD = 5 * mm
QR_SIZE = TAG_H - 2 * 3.5 * mm               # ~49 mm including the white quiet zone
GREEN = (0.16, 0.38, 0.20)


def fit(text, font, size, min_size, width, c):
    while size > min_size and c.stringWidth(text, font, size) > width:
        size -= 0.5
    return size


def draw_qr(c, url, x, y, size):
    matrix = make(url).get_matrix()          # includes the 4-module quiet zone
    n = len(matrix)
    m = size / n
    c.setFillColorRGB(1, 1, 1)
    c.rect(x, y, size, size, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)
    for r, row in enumerate(matrix):
        run = None
        for col in range(n + 1):             # merge horizontal runs to keep the PDF small
            dark = col < n and row[col]
            if dark and run is None:
                run = col
            elif not dark and run is not None:
                c.rect(x + run * m, y + size - (r + 1) * m, (col - run) * m + 0.01, m + 0.01, stroke=0, fill=1)
                run = None


def draw_tag(c, p, cfg, x, y):
    qr_x = x + TAG_W - PAD - QR_SIZE + 2 * mm
    qr_y = y + (TAG_H - QR_SIZE) / 2 + 1.2 * mm
    draw_qr(c, page_url(cfg, p["slug"]), qr_x, qr_y, QR_SIZE)

    text_w = qr_x - x - PAD - 2 * mm
    tx = x + PAD
    ty = y + TAG_H - PAD

    # Green accent bar
    c.setFillColorRGB(*GREEN)
    c.rect(x + 1.6 * mm, y + PAD, 1.6 * mm, TAG_H - 2 * PAD, stroke=0, fill=1)

    # Scientific name, italic
    size = fit(p["scientific_name"], "Times-BoldItalic", 32, 18, text_w, c)
    ty -= size * 0.8
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Times-BoldItalic", size)
    c.drawString(tx, ty, p["scientific_name"])

    if p.get("synonym"):
        ty -= 17
        c.setFont("Times-Italic", 13)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(tx, ty, f"Syn. {p['synonym']}")

    # Common names, wrapped, shrink if needed
    common = ", ".join(p["common_names"])
    cs = 19
    while True:
        lines = simpleSplit(common, "Helvetica-Bold", cs, text_w)
        if len(lines) <= 2 or cs <= 13:
            break
        cs -= 0.5
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", cs)
    ty -= 10
    for line in lines:
        ty -= cs * 1.15
        c.drawString(tx, ty, line)

    # Family
    ty -= 24
    c.setFont("Helvetica", 16)
    c.drawString(tx, ty, "Family: ")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(tx + c.stringWidth("Family: ", "Helvetica", 16), ty, p["family"])

    # University (small) at the bottom
    c.setFont("Helvetica", 9.5)
    c.setFillColorRGB(*GREEN)
    c.drawString(tx, y + PAD - 1, cfg["university_name"])
    # "Scan me" hint under the QR
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.35, 0.35, 0.35)
    c.drawCentredString(qr_x + QR_SIZE / 2, qr_y + 0.2 * mm, "Scan for more details")


def cut_lines(c):
    c.setStrokeColorRGB(0.55, 0.55, 0.55)
    c.setLineWidth(0.5)
    c.setDash(4, 3)
    for i in range(ROWS + 1):
        yy = MARGIN + i * TAG_H
        c.line(MARGIN - 5 * mm, yy, PAGE_W - MARGIN + 5 * mm, yy)
    for xx in (MARGIN, PAGE_W - MARGIN):
        c.line(xx, MARGIN - 5 * mm, xx, PAGE_H - MARGIN + 5 * mm)
    c.setDash()


def main(out=ROOT / "tags.pdf"):
    cfg = load_config()
    plants = load_plants()
    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle(f"Plant tags | {cfg['university_name']}")
    for start in range(0, len(plants), ROWS):
        cut_lines(c)
        for i, p in enumerate(plants[start:start + ROWS]):
            draw_tag(c, p, cfg, MARGIN, PAGE_H - MARGIN - (i + 1) * TAG_H)
        c.showPage()
    c.save()
    print(f"Wrote {out.name}: {len(plants)} tags on {-(-len(plants) // ROWS)} A4 pages")


if __name__ == "__main__":
    main()
