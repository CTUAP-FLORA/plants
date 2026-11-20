"""Make tags.pdf: printable A4 sheet, 5 tags per page, with dashed cut lines.

Each tag has labelled lines so visitors without botany training can read it:
  Scientific name: <italic name>
  Common name:     <Telugu name in Telugu script, or the English name if none is known>
  Family:          <family>
then a hand-written "Scan for more details!" with a curved arrow to the QR code,
and the university name in small text.

The page is laid out in HTML and printed with WeasyPrint, which joins Telugu letters
correctly. Fonts are bundled in fonts/. The QR code is drawn as vector squares from the
same qrcode data and settings as scripts/make_qr.py (error correction H).

Each plant is printed as many times as its `copies` in data/plants.yaml.

Usage:  python scripts/make_tags.py
"""
import html
import re

from PIL import ImageFont
from weasyprint import HTML

from common import ROOT, load_config, load_plants, page_url
from make_qr import make

e = html.escape
FONTS = ROOT / "fonts"
PER_PAGE = 5
TAG_W, TAG_H = 190.0, 55.4            # mm
QR_MM = 45.0                          # QR code size including its white quiet zone
TEXT_MM = 124.0                       # width available for the text column
PT_PER_MM = 72 / 25.4


def width_pt(text, font_file, size_pt):
    """Approximate printed width of text, in points."""
    f = ImageFont.truetype(str(FONTS / font_file), 100)
    return f.getlength(text) / 100 * size_pt


def fit(text, font_file, max_pt, min_pt, avail_pt):
    size = max_pt
    while size > min_pt and width_pt(text, font_file, size) > avail_pt:
        size -= 0.5
    return size


def qr_svg(url):
    m = make(url).get_matrix()                        # includes the 4-module quiet zone
    n = len(m)
    d = []
    for y, row in enumerate(m):
        x = 0
        while x < n:
            if row[x]:
                x0 = x
                while x < n and row[x]:
                    x += 1
                d.append(f"M{x0} {y}h{x - x0}v1h-{x - x0}z")
            else:
                x += 1
    return (f'<svg class="qr" viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
            f'<rect width="{n}" height="{n}" fill="#fff"/><path d="{"".join(d)}" fill="#000"/></svg>')


def sci_html(name):
    """Italic scientific name; rank words such as 'var.' stay upright (botanical convention)."""
    parts = re.split(r"(\b(?:var|subsp|f)\.)", name)
    return "".join(f'<span class="up">{e(p)}</span>' if re.fullmatch(r"(?:var|subsp|f)\.", p) else e(p) for p in parts)


GREEN = "#2f7d3a"
ARROW_STYLE = "swoosh"     # one of: swoosh, banner, chevrons, dotted, loop  (see scan_block)


def _svg(inner):
    return f'<svg class="arrow" viewBox="0 0 {TAG_W} {TAG_H}" width="{TAG_W}mm" height="{TAG_H}mm">{inner}</svg>'


def _head(x1, y1, size=1.0):
    return (f'<path d="M{x1 - 5.2 * size},{y1 - 3.0 * size} L{x1 + 0.6},{y1} L{x1 - 5.2 * size},{y1 + 3.0 * size} '
            f'L{x1 - 3.6 * size},{y1} Z" fill="{GREEN}" stroke="{GREEN}" stroke-width="0.4" stroke-linejoin="round"/>')


def scan_block(style):
    """The 'Scan for more details' call-to-action and its arrow to the QR code (positions in mm)."""
    qr_left = TAG_W - 5.0 - QR_MM
    x1, y1 = qr_left + 1.2, TAG_H / 2 + 1.5           # arrow tip: left edge of the QR code
    if style == "banner":
        # a green arrow-shaped banner with white text, its point touching the QR code
        top, bot = 35.0, 44.5
        mid = (top + bot) / 2
        poly = (f"9,{top} {x1 - 7},{top} {x1 - 7},{top - 2.2} {x1},{mid} {x1 - 7},{bot + 2.2} {x1 - 7},{bot} 9,{bot}")
        return (_svg(f'<polygon points="{poly}" fill="{GREEN}" stroke="{GREEN}" stroke-width="0.6" stroke-linejoin="round"/>')
                + '<div class="scan banner">Scan for more details &#8594;</div>')
    if style == "chevrons":
        # hand-written text followed by a row of growing chevrons that lead into the QR code
        tx = 9 + width_pt("Scan for more details!", "Caveat-Bold.woff2", 21) / PT_PER_MM + 3
        n, gap = 6, (x1 - 2 - tx) / 6
        ch = "".join(
            f'<path d="M{tx + k * gap},{40.2 - (1.6 + k * .45)} L{tx + k * gap + 2.2 + k * .35},{40.2} '
            f'L{tx + k * gap},{40.2 + (1.6 + k * .45)}" fill="none" stroke="{GREEN}" stroke-opacity="{0.35 + k * 0.13:.2f}" '
            f'stroke-width="{0.9 + k * 0.12:.2f}" stroke-linecap="round" stroke-linejoin="round"/>' for k in range(n))
        return _svg(ch) + '<div class="scan">Scan for more details!</div>'
    if style == "dotted":
        # a dotted trail from a pointing hand to the QR code
        x0, y0 = 9 + width_pt("Scan for more details!", "Caveat-Bold.woff2", 21) / PT_PER_MM + 3, 40.4
        path = f"M{x0},{y0} C{x0 + 18},{y0 + 6} {x1 - 18},{y1 + 10} {x1 - 1},{y1}"
        return (_svg(f'<path d="{path}" fill="none" stroke="{GREEN}" stroke-width="1.3" stroke-linecap="round" '
                     f'stroke-dasharray="0.01 2.6"/>' + _head(x1, y1, 1.05))
                + '<div class="scan">Scan for more details!</div>')
    if style == "loop":
        x0, y0 = 9 + width_pt("Scan for more details!", "Caveat-Bold.woff2", 21) / PT_PER_MM + 2, 40.6
        lx, ly = x0 + (x1 - x0) * 0.42, y0 + 3.5
        path = (f"M{x0},{y0} C{x0 + 6},{y0 + 4.5} {lx - 6},{ly + 3} {lx},{ly - 1.5} "
                f"C{lx + 5},{ly - 9} {lx - 6},{ly - 10.5} {lx - 4.5},{ly - 3} "
                f"C{lx - 3.5},{ly + 3.5} {x1 - 14},{y1 + 9} {x1},{y1}")
        return (_svg(f'<path d="{path}" fill="none" stroke="{GREEN}" stroke-width="0.8" stroke-linecap="round"/>' + _head(x1, y1, .9))
                + '<div class="scan">Scan for more details!</div>')
    # default "swoosh": a bold, tapered brush-stroke arrow that sweeps up into the QR code
    x0, y0 = 9 + width_pt("Scan for more details!", "Caveat-Bold.woff2", 21) / PT_PER_MM + 2.5, 41.5
    c1, c2 = (x0 + 22, y0 + 8.5), (x1 - 20, y1 + 11)
    top = f"M{x0},{y0} C{c1[0]},{c1[1] - 0.2} {c2[0]},{c2[1] - 1.6} {x1 - 4.2},{y1 - 0.6}"
    bot = f"L{x1 - 4.4},{y1 + 1.4} C{c2[0]},{c2[1] + 1.4} {c1[0]},{c1[1] + 1.2} {x0},{y0 + 0.4} Z"
    return (_svg(f'<path d="{top} {bot}" fill="{GREEN}"/>' + _head(x1, y1, 1.25))
            + '<div class="scan">Scan for more details!</div>')


def tag_html(p, cfg, style=None):
    avail = TEXT_MM * PT_PER_MM
    lab_sci, lab_com, lab_fam = "Scientific name: ", "Common name: ", "Family: "
    sci_pt = fit(p["scientific_name"], "NotoSerif-BoldItalic.ttf", 23, 13,
                 avail - width_pt(lab_sci, "NotoSans-Regular.ttf", 11))
    te = ", ".join(p["telugu_names"])
    te_pt = fit(te, "NotoSansTelugu-Bold.ttf", 19, 11, avail - width_pt(lab_com, "NotoSans-Regular.ttf", 11)) if te else 19
    if te:
        te_html = f'<span class="te" style="font-size:{te_pt}pt">{e(te)}</span>'
    else:   # no Telugu name known: the English common name, in English
        en = ", ".join(p["common_names"])
        en_pt = fit(en, "NotoSans-Bold.ttf", 17, 11, avail - width_pt(lab_com, "NotoSans-Regular.ttf", 11))
        te_html = (f'<span class="en" style="font-size:{en_pt}pt">{e(en)}</span>' if en
                   else '<span class="missing">(to be added)</span>')
    return f"""<div class="tag">
  <div class="bar"></div>
  <div class="txt">
    <p><span class="lab">{lab_sci}</span><span class="sci" style="font-size:{sci_pt}pt">{sci_html(p["scientific_name"])}</span></p>
    <p><span class="lab">{lab_com}</span>{te_html}</p>
    <p><span class="lab">{lab_fam}</span><span class="fam">{e(p["family"])}</span></p>
  </div>
  {scan_block(style or ARROW_STYLE)}
  <div class="uni">{e(cfg["university_name"])}</div>
  <div class="qrbox">{qr_svg(page_url(cfg, p["slug"]))}</div>
</div>"""


CSS = f"""
@font-face {{ font-family: "TagSerif"; src: url("{(FONTS / 'NotoSerif-BoldItalic.ttf').as_uri()}"); }}
@font-face {{ font-family: "TagSans"; src: url("{(FONTS / 'NotoSans-Regular.ttf').as_uri()}"); font-weight: 400; }}
@font-face {{ font-family: "TagSans"; src: url("{(FONTS / 'NotoSans-Bold.ttf').as_uri()}"); font-weight: 700; }}
@font-face {{ font-family: "TagTelugu"; src: url("{(FONTS / 'NotoSansTelugu-Bold.ttf').as_uri()}"); }}
@font-face {{ font-family: "TagHand"; src: url("{(FONTS / 'Caveat-Bold.woff2').as_uri()}"); }}
@page {{ size: A4; margin: 10mm; }}
body {{ margin: 0; font-family: "TagSans", sans-serif; color: #111; }}
.sheet {{ break-after: page; }}
.sheet:last-child {{ break-after: auto; }}
.tag {{ position: relative; width: {TAG_W}mm; height: {TAG_H}mm; box-sizing: border-box; overflow: hidden;
        border: 0.3mm dashed #8a8a8a; margin-top: -0.3mm; }}
.bar {{ position: absolute; left: 2.2mm; top: 5mm; bottom: 5mm; width: 1.6mm; background: #2f6b3a; }}
.txt {{ position: absolute; left: 9mm; top: 4.6mm; width: {TEXT_MM}mm; }}
.txt p {{ margin: 0 0 1.6mm; line-height: 1.25; white-space: nowrap; }}
.lab {{ font-size: 11pt; color: #555; }}
.sci {{ font-family: "TagSerif", serif; color: #000; }}
.sci .up {{ font-style: normal; font-family: "TagSans"; font-weight: 400; font-size: 0.72em; }}
.te {{ font-family: "TagTelugu", sans-serif; color: #111; }}
.fam {{ font-weight: 700; font-size: 14pt; }}
.en {{ font-weight: 700; color: #111; }}
.missing {{ font-size: 11pt; color: #b00; font-style: italic; }}
.scan {{ position: absolute; left: 9mm; top: 35.6mm; font-family: "TagHand", cursive; font-size: 21pt; color: #2f7d3a;
         transform: rotate(-3deg); transform-origin: left center; }}
.arrow {{ position: absolute; left: 0; top: 0; }}
.scan.banner {{ left: 13mm; top: 35.6mm; transform: none; font-family: "TagSans"; font-weight: 700; font-size: 15pt; color: #fff;
                letter-spacing: 0.2pt; }}
.uni {{ position: absolute; left: 9mm; bottom: 3.6mm; font-size: 9pt; color: #2f6b3a; }}
.qrbox {{ position: absolute; right: 5mm; top: {(TAG_H - QR_MM) / 2}mm; width: {QR_MM}mm; height: {QR_MM}mm; }}
.qr {{ width: {QR_MM}mm; height: {QR_MM}mm; display: block; }}
"""


def build_html(plants, cfg):
    sheets = []
    for i in range(0, len(plants), PER_PAGE):
        sheets.append('<section class="sheet">' + "".join(tag_html(p, cfg) for p in plants[i:i + PER_PAGE]) + "</section>")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Plant tags | {e(cfg["university_name"])}</title>'
            f"<style>{CSS}</style></head><body>{''.join(sheets)}</body></html>")


def main(out=ROOT / "tags.pdf", slugs=None):
    cfg = load_config()
    plants = load_plants()
    if slugs:
        plants = [p for p in plants if p["slug"] in slugs]
    plants = [p for p in plants for _ in range(int(p.get("copies") or 1))]   # one tag per printed copy
    HTML(string=build_html(plants, cfg), base_url=str(ROOT)).write_pdf(str(out))
    missing = [p["scientific_name"] for p in plants if not p["telugu_names"] and not p["common_names"]]
    print(f"Wrote {out.name}: {len(plants)} tags on {-(-len(plants) // PER_PAGE)} A4 pages")
    missing = list(dict.fromkeys(missing))
    if missing:
        print("No Telugu name yet (tag shows '(to be added)'):", ", ".join(missing))


if __name__ == "__main__":
    main()
