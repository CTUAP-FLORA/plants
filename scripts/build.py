"""Build the static website into _site/ from data/plants.yaml.

Usage:  python scripts/build.py

Design notes
* Every plant FAMILY has its own colour theme, so pages are colourful and
  plants of one family look related.
* Everything shown is taken from data/plants.yaml (the classification strip
  uses only the family and the genus = first word of the scientific name).
* Light: one small web font, no frameworks, no images unless photos are added.
  Animations are switched off for people who prefer reduced motion.
* Page URLs (/p/<slug>/) never change here; the QR codes depend on them.
"""
import hashlib
import html
import json
import shutil

import verified_html
from common import OPTIONAL_TEXT_FIELDS, ROOT, load_config, load_plants

OUT = ROOT / "_site"
e = html.escape

FONT = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        # media="print" + onload: the font never delays the first paint on slow mobile data
        '<link rel="stylesheet" media="print" onload="this.media=\'all\'" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,700;1,9..144,600;1,9..144,700&display=swap">')

# Each family on campus has its own colour (hue in degrees on the colour wheel,
# spaced evenly so no two look alike). A family that is not listed here gets a
# colour computed from its name, so new plants work automatically.
FAMILY_HUES = {
    "Apocynaceae": 0, "Anacardiaceae": 19, "Rutaceae": 38, "Costaceae": 57,
    "Asparagaceae": 76, "Meliaceae": 95, "Combretaceae": 114, "Fabaceae": 133,
    "Araucariaceae": 152, "Cupressaceae": 171, "Bignoniaceae": 190, "Malvaceae": 209,
    "Euphorbiaceae": 228, "Muntingiaceae": 247, "Myrtaceae": 266, "Nyctaginaceae": 285,
    "Rosaceae": 304, "Arecaceae": 323, "Strelitziaceae": 342,
}


def hue(family):
    return FAMILY_HUES.get(family, int(hashlib.md5(family.encode()).hexdigest(), 16) % 360)


def theme(family):
    """Colour theme for a plant family -> CSS custom properties."""
    h = hue(family)
    h2 = (h + 40) % 360
    return (f"--c1:hsl({h} 65% 24%);--c2:hsl({h2} 60% 34%);--c3:hsl({h} 70% 62%);"
            f"--soft:hsl({h} 60% 95%);--soft-d:hsl({h} 30% 17%);--ink-c:hsl({h} 65% 26%);--ink-c-d:hsl({h} 65% 76%)")


ICONS = {  # simple inline SVG icons (stroke = currentColor)
    "description": '<path d="M5 4h10l4 4v12H5z"/><path d="M15 4v4h4M8 12h8M8 16h6"/>',
    "uses": '<path d="M12 21s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 5.6-7 10-7 10z"/>',
    "native_to": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>',
    "flowering_season": '<circle cx="12" cy="12" r="2.5"/><path d="M12 9.5a3 3 0 1 1 0-6 3 3 0 1 1 0 6zM12 14.5a3 3 0 1 0 0 6 3 3 0 1 0 0-6zM9.5 12a3 3 0 1 1-6 0 3 3 0 1 1 6 0zM14.5 12a3 3 0 1 0 6 0 3 3 0 1 0-6 0z"/>',
    "notes": '<path d="M12 21s-6-5.3-6-11a6 6 0 0 1 12 0c0 5.7-6 11-6 11z"/><circle cx="12" cy="10" r="2"/>',
    "leaf": '<path d="M5 19c0-9 6-14 15-14 0 9-5 15-14 15"/><path d="M5 19c4-4 7-6 10-8"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    "back": '<path d="M15 5l-7 7 7 7"/>',
    "next": '<path d="M9 5l7 7-7 7"/>',
    "grid": '<rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/>',
    "share": '<circle cx="18" cy="5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="m8.2 10.8 7.6-4.4M8.2 13.2l7.6 4.4"/>',
}


def icon(name, cls="ic"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


LEAF_PATH = "M50 2C80 22 92 60 50 98 8 60 20 22 50 2z"
LEAF_VEIN = "M50 6v90M50 40l-16-12M50 40l16-12M50 60l-20-14M50 60l20-14M50 80l-18-12M50 80l18-12"


def leaf_svg(cls):
    return (f'<svg class="{cls}" viewBox="0 0 100 100" aria-hidden="true"><path d="{LEAF_PATH}" fill="#fff"/>'
            f'<path d="{LEAF_VEIN}" stroke="#000" stroke-opacity=".12" stroke-width="2" fill="none"/></svg>')


# Floating leaves + soft glow in the header (pure CSS/SVG, about 2 KB).
DECOR = ('<div class="decor" aria-hidden="true"><span class="glow"></span>'
         + "".join(leaf_svg(f"lf lf{i}") for i in range(1, 7)) + "</div>")
WAVE = ('<svg class="wave" viewBox="0 0 1440 80" preserveAspectRatio="none" aria-hidden="true">'
        '<path d="M0 40c240 40 480 40 720 10S1200-10 1440 30v50H0z"/></svg>')

SPROUT = """<svg viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M20 78h56"/><path d="M30 78c2-8 9-12 18-12s16 4 18 12"/><path class="stem" d="M48 66V40"/>
<path class="l1" d="M48 48c-12 0-20-8-20-20 12 0 20 8 20 20z" fill="currentColor" fill-opacity=".15"/>
<path class="l2" d="M48 40c0-12 8-20 20-20 0 12-8 20-20 20z" fill="currentColor" fill-opacity=".15"/></svg>"""

CSS = """
:root{--bg:#f2f5ef;--card:#fff;--ink:#17201a;--muted:#5b695e;--line:#e1e7dd;--shadow:0 10px 30px -12px rgba(20,45,28,.25);
 --serif:"Fraunces",Georgia,"Times New Roman",serif}
@media (prefers-color-scheme:dark){:root{--bg:#0d1310;--card:#161e19;--ink:#e7efe8;--muted:#9fb1a4;--line:#253129;--shadow:0 10px 30px -12px rgba(0,0,0,.6)}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;overflow-x:hidden}
a{color:inherit}
.wrap{max-width:760px;margin:0 auto;padding:0 16px}

/* ---------- hero ---------- */
.hero{position:relative;overflow:hidden;color:#fff;background:radial-gradient(120% 90% at 85% 0%,var(--c2) 0%,transparent 60%),linear-gradient(160deg,var(--c1),var(--c2));
 padding:14px 0 70px;min-height:min(60vh,470px);display:flex;flex-direction:column}
.hero>.wrap{position:relative;z-index:2;width:100%;flex:1;display:flex;flex-direction:column}
.hero.photo{background:#0b0f0c}
.hero .bgimg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;animation:kb 18s ease-out both}
.hero.photo::after{content:"";position:absolute;inset:0;z-index:1;background:linear-gradient(180deg,rgba(0,0,0,.25) 0%,rgba(0,0,0,.05) 35%,rgba(0,0,0,.7) 100%)}
@keyframes kb{from{transform:scale(1.12)}to{transform:scale(1)}}
.decor{position:absolute;inset:0;z-index:1;pointer-events:none}
.glow{position:absolute;width:420px;height:420px;right:-120px;top:-140px;border-radius:50%;background:radial-gradient(circle,var(--c3) 0%,transparent 65%);opacity:.45;animation:pulse 9s ease-in-out infinite}
@keyframes pulse{50%{transform:scale(1.15);opacity:.3}}
.lf{position:absolute;opacity:.13;animation:float 14s ease-in-out infinite}
.lf1{width:170px;right:-30px;top:30px;--r:-25deg}
.lf2{width:90px;right:120px;top:-10px;--r:30deg;animation-delay:-3s;opacity:.1}
.lf3{width:120px;right:40px;top:230px;--r:65deg;animation-delay:-6s;opacity:.09}
.lf4{width:60px;left:55%;top:120px;--r:-60deg;animation-delay:-2s;opacity:.12}
.lf5{width:70px;left:-20px;top:300px;--r:20deg;animation-delay:-8s;opacity:.08}
.lf6{width:44px;right:200px;top:340px;--r:110deg;animation-delay:-5s;opacity:.12}
@keyframes float{0%,100%{transform:translateY(0) rotate(var(--r))}50%{transform:translateY(-16px) rotate(calc(var(--r) + 10deg))}}
.wave{position:absolute;left:0;bottom:-1px;width:100%;height:56px;z-index:3}
.wave path{fill:var(--bg)}
.topbar{display:flex;align-items:center;gap:10px;font-size:13px}
.pill{display:inline-flex;align-items:center;gap:6px;text-decoration:none;color:#fff;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);
 padding:7px 13px 7px 9px;border-radius:999px;font-weight:600;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
.pill .ic{width:16px;height:16px}
.topbar .uni{margin-left:auto;text-align:right;opacity:.9;max-width:58%;line-height:1.35}
.hero-body{margin-top:auto;padding-top:40px}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;opacity:.92}
.eyebrow .ic{width:16px;height:16px}
.hero h1{font-family:var(--serif);font-style:italic;font-weight:700;font-size:min(68px,11vw,calc((100vw - 34px) / (var(--chars,10) * .62)));line-height:1;overflow-wrap:break-word;letter-spacing:-.01em;margin:4px 0 8px;
 text-shadow:0 4px 30px rgba(0,0,0,.25)}
.hero h1 .sp{display:block}
.hero .syn{margin:0;opacity:.88;font-size:15px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 0;padding:0;list-style:none}
.lbl{display:block;margin:20px 0 0;font-size:13px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;opacity:.85}
.lbl.first{margin-top:16px}
.grid .cn b{font-weight:600;color:var(--ink)}
.chips li{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.3);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
 padding:7px 15px;border-radius:999px;font-weight:600;font-size:16px}
/* entrance animation */
.rise{animation:rise .8s cubic-bezier(.2,.7,.2,1) both}
.d1{animation-delay:.08s}.d2{animation-delay:.16s}.d3{animation-delay:.24s}.d4{animation-delay:.32s}
@keyframes rise{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:none}}

/* ---------- content ---------- */
main.wrap{position:relative;z-index:4;margin-top:-34px;padding-bottom:8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:18px;margin-bottom:14px;box-shadow:var(--shadow)}
.reveal{opacity:0;transform:translateY(26px);transition:opacity .7s ease,transform .7s cubic-bezier(.2,.7,.2,1)}
.reveal.in{opacity:1;transform:none}
.taxo{display:grid;grid-template-columns:.8fr 1.1fr 1.1fr;gap:0;padding:0;overflow:hidden}
.taxo div{padding:14px 6px;min-width:0;container-type:inline-size;position:relative;text-align:center}
.taxo div+div{border-left:1px solid var(--line)}
.taxo small{display:block;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.taxo b{display:block;font-size:var(--fs,16px);font-size:min(var(--fs,16px),calc(100cqi / (var(--n,8) * .66)));line-height:1.3;margin-top:2px;color:var(--ink-c);white-space:nowrap}
.taxo b.g{font-family:var(--serif);font-style:italic;font-size:var(--fs,18px);font-size:min(var(--fs,18px),calc(100cqi / (var(--n,8) * .62)))}
.taxo div:nth-child(2){background:var(--soft)}
.info h2{display:flex;align-items:center;gap:12px;font-size:14px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-c);margin:0 0 10px}
.info h2 .ic{width:40px;height:40px;padding:9px;border-radius:13px;color:#fff;background:linear-gradient(135deg,var(--c1),var(--c2));flex:none;box-shadow:0 6px 14px -6px var(--c1)}
.info p{margin:0 0 8px}.info ul{margin:0 0 6px;padding-left:20px}.info li{margin:4px 0}
.info li::marker{color:var(--c2)}
.gallery{display:grid;gap:12px;margin-bottom:14px}
.gallery figure{margin:0;border-radius:22px;overflow:hidden;background:var(--card);box-shadow:var(--shadow);border:1px solid var(--line)}
.gallery img{width:100%;height:auto;display:block}
.gallery figcaption{font-size:14px;color:var(--muted);padding:8px 14px 10px}
.soon{text-align:center;padding:26px 18px 22px}
.soon svg{width:92px;height:92px;color:var(--ink-c)}
.soon .stem,.soon .l1,.soon .l2{transform-origin:48px 66px;animation:grow 2.4s ease-in-out infinite alternate}
.soon .l1{animation-delay:.2s}.soon .l2{animation-delay:.4s}
@keyframes grow{from{transform:scale(.92)}to{transform:scale(1.04)}}
.soon h2{margin:6px 0 4px;font-size:20px;font-family:var(--serif)}
.soon p{margin:0;color:var(--muted)}
.related h2{font-size:14px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-c);margin:0 0 10px}
.related ul{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.related a{display:block;text-decoration:none;background:var(--soft);color:var(--ink-c);padding:8px 15px;border-radius:999px;font-family:var(--serif);font-style:italic;font-weight:600}
.pager{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:4px 0 14px}
.pager a{display:block;text-decoration:none;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:12px 14px;box-shadow:var(--shadow);min-width:0}
.pager a.nx{text-align:right}
.pager small{display:flex;align-items:center;gap:4px;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.pager a.nx small{justify-content:flex-end}
.pager small .ic{width:14px;height:14px}
.pager span{display:block;font-family:var(--serif);font-style:italic;font-weight:600;font-size:17px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--ink-c)}
.cta{display:flex;align-items:center;justify-content:center;gap:10px;margin:6px 0;padding:16px;border-radius:18px;text-decoration:none;font-weight:700;color:#fff;
 background:linear-gradient(135deg,var(--c1),var(--c2));box-shadow:0 12px 26px -12px var(--c1)}
.cta .ic{width:20px;height:20px}
.count{text-align:center;color:var(--muted);font-size:13px;margin:10px 0 0}
footer{color:var(--muted);font-size:13px;text-align:center;padding:18px 16px 34px}
@media (prefers-color-scheme:dark){
 .info h2,.related h2,.related a,.soon svg,.taxo b,.pager span{color:var(--ink-c-d)}
 .related a,.taxo div:nth-child(2){background:var(--soft-d)}
}

/* ---------- index page ---------- */
.home .hero{--c1:#123d27;--c2:#1f6b52;--c3:#7fdc9f;min-height:0;padding-bottom:96px}
.home .hero h1{font-style:normal;font-size:clamp(38px,10vw,60px);margin-top:14px}
.home .hero h1 i{font-style:italic;color:#b9f3cc}
.home .lead{margin:6px 0 0;opacity:.92;font-size:17px;max-width:520px}
.stats{display:flex;gap:10px;margin-top:20px}
.stats div{flex:1;max-width:150px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:16px;padding:10px 12px;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
.stats b{display:block;font-family:var(--serif);font-size:30px;line-height:1.1}
.stats small{font-size:12px;letter-spacing:.06em;text-transform:uppercase;opacity:.85}
.searchbox{position:relative;margin-top:-58px;z-index:5}
.searchbox .ic{position:absolute;left:18px;top:50%;transform:translateY(-50%);width:22px;height:22px;color:var(--muted)}
input[type=search]{width:100%;font-size:18px;padding:17px 16px 17px 52px;border:1px solid var(--line);border-radius:18px;background:var(--card);color:var(--ink);box-shadow:var(--shadow);outline:none}
input[type=search]:focus{border-color:#1f6b52;box-shadow:0 0 0 4px rgba(31,107,82,.15),var(--shadow)}
.fams{display:flex;gap:8px;overflow-x:auto;padding:14px 2px 6px;margin:0 -16px;padding-left:16px;padding-right:16px;scrollbar-width:none}
.fams::-webkit-scrollbar{display:none}
.fams button{flex:none;font:inherit;font-size:14px;font-weight:600;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:7px 14px;border-radius:999px;cursor:pointer;display:inline-flex;align-items:center;gap:7px}
.fams button i{width:10px;height:10px;border-radius:50%;background:linear-gradient(135deg,var(--c1),var(--c3))}
.fams button[aria-pressed=true]{color:#fff;border-color:transparent;background:linear-gradient(135deg,var(--c1),var(--c2))}
.fams button[aria-pressed=true] i{background:#fff}
.grid{list-style:none;margin:10px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.grid a{display:flex;gap:14px;align-items:flex-start;height:100%;text-decoration:none;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:14px;box-shadow:var(--shadow);transition:transform .2s}
.grid a:active{transform:scale(.98)}
.grid .badge{flex:none;width:52px;height:52px;border-radius:16px;display:grid;place-items:center;color:#fff;font-family:var(--serif);font-style:italic;font-weight:700;font-size:24px;
 background:linear-gradient(135deg,var(--c1),var(--c2));box-shadow:0 8px 16px -8px var(--c1)}
.grid .tx{min-width:0}
.grid .sci{display:block;font-family:var(--serif);font-style:italic;font-weight:700;font-size:19px;line-height:1.2}
.grid .cn{display:block;color:var(--muted);font-size:14.5px;margin-top:3px;line-height:1.4}
.grid .fam{display:inline-block;margin-top:8px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-c);background:var(--soft);padding:3px 9px;border-radius:999px}
@media (prefers-color-scheme:dark){.grid .fam{color:var(--ink-c-d);background:var(--soft-d)}}
.none{text-align:center;color:var(--muted);padding:20px}

@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}.reveal{opacity:1;transform:none}}
"""

REVEAL_JS = """<script>
(function(){var els=[].slice.call(document.querySelectorAll('.reveal'));
if(!('IntersectionObserver' in window)){els.forEach(function(x){x.classList.add('in')});return;}
var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting){en.target.classList.add('in');io.unobserve(en.target);}})},{rootMargin:'0px 0px -6% 0px'});
els.forEach(function(x){io.observe(x)});})();
</script>"""


def page(title, body, cfg, up, style="", cls="", color="#1f5f3a"):
    """up = relative (or absolute) path from this page to the site root."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="{color}">
<title>{e(title)}</title>
{FONT}
<link rel="stylesheet" href="{up}style.css">
</head>
<body class="{cls}" style="{style}">
{body}
<footer>{e(cfg['site_title'])} · {e(cfg['university_name'])}</footer>
{REVEAL_JS}
{verified_html.JS if 'class="vbtns"' in body else ""}
</body>
</html>
"""


def paragraphs(text):
    """Text or list -> HTML. A list becomes bullet points; blank lines split paragraphs."""
    if isinstance(text, list):
        return "<ul>" + "".join(f"<li>{e(str(x))}</li>" for x in text) + "</ul>"
    parts = [p.strip() for p in str(text).split("\n\n") if p.strip()]
    return "".join(f"<p>{e(p).replace(chr(10), '<br>')}</p>" for p in parts)


def sci_name_html(name):
    """'Hibiscus rosa-sinensis' -> genus on one line, epithet on the next."""
    parts = name.split(" ", 1)
    if len(parts) == 2:
        return f'{e(parts[0])}<span class="sp">{e(parts[1])}</span>'
    return e(name)


def plant_page(p, cfg, plants):
    up = "../../"
    photos = p["photos"]
    ordered = sorted(plants, key=lambda q: q["scientific_name"])
    i = next(k for k, q in enumerate(ordered) if q["slug"] == p["slug"])
    prev_p, next_p = ordered[i - 1], ordered[(i + 1) % len(ordered)]

    bg = f'<img class="bgimg" src="{up}photos/{e(photos[0]["file"])}" alt="">' if photos else DECOR
    h = [f'<header class="hero{" photo" if photos else ""}">{bg}<div class="wrap">',
         f'<div class="topbar"><a class="pill" href="{up}">{icon("back")}All plants</a>'
         f'<span class="uni">{e(cfg["university_name"])}</span></div>',
         '<div class="hero-body">',
         f'<div class="eyebrow rise">{icon("leaf")}{e(cfg["site_title"])} · {e(p["family"])}</div>',
         '<span class="lbl first rise d1">Scientific name</span>',
         f'<h1 class="rise d1" style="--chars:{max(len(w) for w in p["scientific_name"].split())}">{sci_name_html(p["scientific_name"])}</h1>']
    if p.get("synonym"):
        h.append(f'<p class="syn rise d2">Synonym: <i>{e(p["synonym"])}</i></p>')
    if p["common_names"]:
        h.append(f'<span class="lbl rise d3">{"Common names" if len(p["common_names"]) > 1 else "Common name"}</span>')
        h.append('<ul class="chips rise d3">' + "".join(f"<li>{e(n)}</li>" for n in p["common_names"]) + "</ul>")
    h.append(f"</div></div>{WAVE}</header>")

    genus = p["scientific_name"].split(" ")[0]
    m = ['<main class="wrap">',
         f'<section class="card taxo rise d4" aria-label="Classification">'
         f'<div><small>Kingdom</small><b>Plantae</b></div>'
         f'<div><small>Family</small><b style="--fs:16px;--n:{len(p["family"])}">{e(p["family"])}</b></div>'
         f'<div><small>Genus</small><b class="g" style="--fs:18px;--n:{len(genus)}">{e(genus)}</b></div></section>']
    m.append(verified_html.render(p["slug"]))
    if photos:
        m.append('<div class="gallery">')
        for ph in photos:
            cap = " · ".join(x for x in (ph.get("caption"), ph.get("credit")) if x)
            m.append(f'<figure class="reveal"><img src="{up}photos/{e(ph["file"])}" alt="{e(ph.get("caption") or p["scientific_name"])}" loading="lazy">'
                     + (f"<figcaption>{e(cap)}</figcaption>" if cap else "") + "</figure>")
        m.append("</div>")
    has_detail = False
    for key, heading in OPTIONAL_TEXT_FIELDS:
        val = p.get(key)
        if val:
            has_detail = True
            m.append(f'<section class="card info reveal"><h2>{icon(key)}{heading}</h2>{paragraphs(val)}</section>')
    if not has_detail and not photos:
        m.append(f'<section class="card soon reveal">{SPROUT}<h2>More details coming soon</h2>'
                 '<p>Description, uses, flowering season and photos will be added here.</p></section>')
    same = sorted((q for q in plants if q["family"] == p["family"] and q["slug"] != p["slug"]),
                  key=lambda q: q["scientific_name"])
    if same:
        m.append(f'<section class="card related reveal"><h2>Also in {e(p["family"])} on campus</h2><ul>'
                 + "".join(f'<li><a href="{up}p/{q["slug"]}/">{e(q["scientific_name"])}</a></li>' for q in same)
                 + "</ul></section>")
    m.append(f'<nav class="pager reveal" aria-label="More plants">'
             f'<a href="{up}p/{prev_p["slug"]}/" style="{theme(prev_p["family"])}"><small>{icon("back")}Previous</small><span>{e(prev_p["scientific_name"])}</span></a>'
             f'<a class="nx" href="{up}p/{next_p["slug"]}/" style="{theme(next_p["family"])}"><small>Next{icon("next")}</small><span>{e(next_p["scientific_name"])}</span></a></nav>')
    m.append(f'<a class="cta reveal" href="{up}">{icon("grid")}Explore all {len(plants)} plants on campus</a>'
             f'<p class="count">Plant {i + 1} of {len(plants)}</p></main>')
    color = f"hsl({hue(p['family'])} 65% 24%)"
    return page(f'{p["scientific_name"]} | {cfg["site_title"]}', "\n".join(h + m), cfg, up, theme(p["family"]), color=color)


def index_page(plants, cfg):
    items = []
    for p in sorted(plants, key=lambda x: x["scientific_name"]):
        search = " ".join([p["scientific_name"], p.get("synonym") or "", p["family"], *p["common_names"]]).lower()
        items.append(
            f'<li data-s="{e(search)}" data-f="{e(p["family"])}" style="{theme(p["family"])}"><a href="p/{p["slug"]}/">'
            f'<span class="badge">{e(p["scientific_name"][0])}</span><span class="tx">'
            f'<span class="sci">{e(p["scientific_name"])}</span>'
            f'<span class="cn"><b>Common {"names" if len(p["common_names"]) > 1 else "name"}:</b> {e(", ".join(p["common_names"]))}</span>'
            f'<span class="fam">{e(p["family"])}</span></span></a></li>')
    fams = sorted({p["family"] for p in plants})
    fam_buttons = ['<button type="button" aria-pressed="true" data-f="" style="--c1:#123d27;--c2:#1f6b52;--c3:#7fdc9f"><i></i>All</button>']
    fam_buttons += [f'<button type="button" aria-pressed="false" data-f="{e(f)}" style="{theme(f)}"><i></i>{e(f)}</button>' for f in fams]
    body = f"""<header class="hero">{DECOR}<div class="wrap">
<div class="topbar"><span class="uni" style="margin-left:0;text-align:left;max-width:100%">{e(cfg['university_name'])}</span></div>
<div class="hero-body">
<div class="eyebrow rise">{icon("leaf")}{e(cfg['site_title'])}</div>
<h1 class="rise d1">Plants of <i>our campus</i></h1>
<p class="lead rise d2">Scan the QR code on any plant tag, or explore them all below.</p>
<div class="stats rise d3"><div><b>{len(plants)}</b><small>Species</small></div><div><b>{len(fams)}</b><small>Families</small></div></div>
</div></div>{WAVE}</header>
<main class="wrap">
<div class="searchbox rise d4">{icon("search")}<input type="search" id="q" placeholder="Search by name or family…" aria-label="Search plants" autocomplete="off"></div>
<div class="fams" id="fams" role="group" aria-label="Filter by family">{"".join(fam_buttons)}</div>
<ul class="grid" id="list">
{chr(10).join(items)}
</ul>
<p id="none" class="none" hidden>No plants match your search.</p>
</main>
<script>
(function(){{var q=document.getElementById('q'),li=[].slice.call(document.querySelectorAll('#list li')),none=document.getElementById('none'),
bs=[].slice.call(document.querySelectorAll('#fams button')),fam='';
function run(){{var t=q.value.trim().toLowerCase(),n=0;li.forEach(function(x){{var ok=x.getAttribute('data-s').indexOf(t)>-1&&(!fam||x.getAttribute('data-f')===fam);x.hidden=!ok;if(ok)n++;}});none.hidden=n>0;}}
q.addEventListener('input',run);
bs.forEach(function(b){{b.addEventListener('click',function(){{fam=b.getAttribute('data-f');bs.forEach(function(x){{x.setAttribute('aria-pressed',x===b)}});run();}})}});}})();
</script>"""
    return page(f'{cfg["site_title"]} | {cfg["university_name"]}', body, cfg, "", cls="home", color="#123d27")


def main():
    cfg = load_config()
    plants = load_plants()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "style.css").write_text(CSS.strip() + "\n" + verified_html.CSS.strip() + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    (OUT / "index.html").write_text(index_page(plants, cfg), encoding="utf-8")
    for p in plants:
        d = OUT / "p" / p["slug"]
        d.mkdir(parents=True)
        (d / "index.html").write_text(plant_page(p, cfg, plants), encoding="utf-8")
    root = cfg["base_url"] + "/"   # 404 can be served at any path, so use absolute links
    nf = (f'<header class="hero" style="--c1:#123d27;--c2:#1f6b52;--c3:#7fdc9f;min-height:50vh">{DECOR}<div class="wrap"><div class="hero-body">'
          f'<div class="eyebrow">{icon("leaf")}{e(cfg["site_title"])}</div><h1 style="font-style:normal">Page not found</h1></div></div>{WAVE}</header>'
          f'<main class="wrap"><a class="cta" style="--c1:#123d27;--c2:#1f6b52" href="{root}">{icon("grid")}See all plants on campus</a></main>')
    (OUT / "404.html").write_text(page("Page not found", nf, cfg, root), encoding="utf-8")
    photos = ROOT / "photos"
    if photos.exists():
        shutil.copytree(photos, OUT / "photos", ignore=shutil.ignore_patterns(".gitkeep"))
    # machine-readable list, used by scripts/verify.py
    (OUT / "plants.json").write_text(json.dumps(
        [{"slug": p["slug"], "scientific_name": p["scientific_name"]} for p in plants], indent=1), encoding="utf-8")
    print(f"Built {len(plants)} plant pages into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
