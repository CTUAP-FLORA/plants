"""Build the static website into _site/ from data/plants.yaml.

Usage:  python scripts/build.py
"""
import html
import json
import shutil

from common import OPTIONAL_TEXT_FIELDS, ROOT, load_config, load_plants

OUT = ROOT / "_site"
e = html.escape

CSS = """
:root{--bg:#f6f8f4;--card:#fff;--ink:#1d2a1f;--muted:#5b6b5d;--accent:#2f6b3a;--line:#dfe6dc}
@media (prefers-color-scheme:dark){:root{--bg:#121814;--card:#1b231d;--ink:#e6eee6;--muted:#a3b2a5;--accent:#7cc48a;--line:#2c3a2f}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header.top{background:var(--accent);color:#fff;padding:12px 16px}
@media (prefers-color-scheme:dark){header.top{color:#0d140f}}
header.top a{color:inherit;text-decoration:none;font-weight:600}
header.top small{display:block;opacity:.85;font-size:13px}
main{max-width:720px;margin:0 auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 18px 8px;margin-bottom:16px}
h1{font-size:28px;line-height:1.2;margin:0 0 4px}
h1 i,.sci{font-style:italic}
.syn{color:var(--muted);margin:0 0 10px}
.common{font-size:20px;margin:8px 0}
.family{color:var(--muted);margin:0 0 12px}
h2{font-size:18px;color:var(--accent);margin:18px 0 6px}
figure{margin:0 0 14px}
figure img{width:100%;height:auto;border-radius:10px;display:block}
figcaption{font-size:14px;color:var(--muted);margin-top:4px}
.soon{color:var(--muted);font-style:italic}
input[type=search]{width:100%;font-size:18px;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);margin-bottom:12px}
ul.list{list-style:none;margin:0;padding:0}
ul.list li{border-bottom:1px solid var(--line)}
ul.list a{display:block;padding:12px 4px;color:var(--ink);text-decoration:none}
ul.list a:hover .sci{text-decoration:underline}
ul.list .meta{display:block;color:var(--muted);font-size:15px}
footer{color:var(--muted);font-size:13px;text-align:center;padding:24px 16px}
footer a{color:var(--accent)}
"""


def page(title, body, cfg, up):
    """up = relative (or absolute) path from this page to the site root."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<header class="top"><a href="{up}">{e(cfg['site_title'])}</a><small>{e(cfg['university_name'])}</small></header>
<main>
{body}
</main>
<footer><a href="{up}">All plants on campus</a></footer>
</body>
</html>
"""


def paragraphs(text):
    """Text or list -> HTML. A list becomes bullet points; blank lines split paragraphs."""
    if isinstance(text, list):
        return "<ul>" + "".join(f"<li>{e(str(x))}</li>" for x in text) + "</ul>"
    parts = [p.strip() for p in str(text).split("\n\n") if p.strip()]
    return "".join(f"<p>{e(p).replace(chr(10), '<br>')}</p>" for p in parts)


def plant_page(p, cfg):
    b = [f'<article class="card">', f'<h1><i>{e(p["scientific_name"])}</i></h1>']
    if p.get("synonym"):
        b.append(f'<p class="syn">Synonym: <i>{e(p["synonym"])}</i></p>')
    if p["common_names"]:
        b.append(f'<p class="common">{e(", ".join(p["common_names"]))}</p>')
    b.append(f'<p class="family">Family: <b>{e(p["family"])}</b></p>')
    for ph in p["photos"]:
        cap = " · ".join(x for x in (ph.get("caption"), ph.get("credit")) if x)
        b.append(f'<figure><img src="../../photos/{e(ph["file"])}" alt="{e(ph.get("caption") or p["scientific_name"])}" loading="lazy">'
                 + (f"<figcaption>{e(cap)}</figcaption>" if cap else "") + "</figure>")
    has_detail = False
    for key, heading in OPTIONAL_TEXT_FIELDS:
        val = p.get(key)
        if val:
            has_detail = True
            b.append(f"<h2>{heading}</h2>{paragraphs(val)}")
    if not has_detail and not p["photos"]:
        b.append('<p class="soon">More details about this plant will be added soon.</p>')
    b.append("</article>")
    return page(f'{p["scientific_name"]} | {cfg["site_title"]}', "\n".join(b), cfg, "../../")


def index_page(plants, cfg):
    items = []
    for p in sorted(plants, key=lambda x: x["scientific_name"]):
        search = " ".join([p["scientific_name"], p.get("synonym") or "", p["family"], *p["common_names"]]).lower()
        items.append(
            f'<li data-s="{e(search)}"><a href="p/{p["slug"]}/"><span class="sci">{e(p["scientific_name"])}</span>'
            f'<span class="meta">{e(", ".join(p["common_names"]))} · {e(p["family"])}</span></a></li>')
    body = f"""<h1>Plants on campus</h1>
<p class="family">{len(plants)} species. Search by scientific name, common name or family.</p>
<input type="search" id="q" placeholder="Search plants…" aria-label="Search plants" autocomplete="off">
<ul class="list" id="list">
{chr(10).join(items)}
</ul>
<p id="none" class="soon" hidden>No plants match your search.</p>
<script>
var q=document.getElementById('q'),li=[].slice.call(document.querySelectorAll('#list li')),none=document.getElementById('none');
q.addEventListener('input',function(){{var t=q.value.trim().toLowerCase(),n=0;
li.forEach(function(x){{var ok=x.getAttribute('data-s').indexOf(t)>-1;x.hidden=!ok;if(ok)n++;}});none.hidden=n>0;}});
</script>"""
    return page(f'{cfg["site_title"]} | {cfg["university_name"]}', body, cfg, "")


def main():
    cfg = load_config()
    plants = load_plants()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    (OUT / "index.html").write_text(index_page(plants, cfg), encoding="utf-8")
    for p in plants:
        d = OUT / "p" / p["slug"]
        d.mkdir(parents=True)
        (d / "index.html").write_text(plant_page(p, cfg), encoding="utf-8")
    root = cfg["base_url"] + "/"   # 404 can be served at any path, so use absolute links
    nf = page("Page not found", f'<h1>Page not found</h1><p>See the list of <a href="{root}">all plants</a>.</p>', cfg, root)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    photos = ROOT / "photos"
    if photos.exists():
        shutil.copytree(photos, OUT / "photos", ignore=shutil.ignore_patterns(".gitkeep"))
    # machine-readable list, used by scripts/verify.py
    (OUT / "plants.json").write_text(json.dumps(
        [{"slug": p["slug"], "scientific_name": p["scientific_name"]} for p in plants], indent=1), encoding="utf-8")
    print(f"Built {len(plants)} plant pages into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
