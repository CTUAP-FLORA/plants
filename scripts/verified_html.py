"""Render data/verified/<slug>.json (made by fetch_verified.py) as 3 buttons with panels:
Taxonomy, Phytochemicals and Conservation.

Source links are kept in the JSON files (data/verified/) but not shown on the page.
Empty results are shown honestly ("Not recorded in these databases").
"""
import html
import json

from common import ROOT

e = html.escape
VERIFIED_DIR = ROOT / "data" / "verified"

# (key in the JSON, button label, icon path)
BUTTONS = [
    ("taxonomy", "Taxonomy", '<rect x="9" y="3" width="6" height="5" rx="1.5"/><rect x="3" y="16" width="6" height="5" rx="1.5"/><rect x="15" y="16" width="6" height="5" rx="1.5"/><path d="M12 8v4M6 16v-2h12v2"/>'),
    ("phytochemicals", "Phytochemicals", '<path d="M9 3h6M10 3v6L5 18a2 2 0 0 0 1.8 3h10.4A2 2 0 0 0 19 18l-5-9V3"/><path d="M7.5 14h9"/>'),
    ("conservation", "Conservation", '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>'),
]

IUCN_COLOURS = {"EX": "#000", "EW": "#542344", "CR": "#d81e05", "EN": "#fc7f3f", "VU": "#f9e814",
                "NT": "#cce226", "LC": "#60c659", "DD": "#d1d1c6", "NE": "#fff"}
NR = '<span class="nr">Not recorded in these databases</span>'

CSS = """
.vf{margin:0 0 14px}
.vf-head{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin:2px 4px 10px}
.vf-head h2{font-family:var(--serif);font-size:22px;margin:0}
.vf-head small{color:var(--muted);font-size:12px;text-align:right}
.vbtns{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.vbtns button{font:inherit;font-size:13.5px;font-weight:700;line-height:1.2;color:var(--ink-c);background:var(--card);border:1px solid var(--line);border-radius:18px;
 padding:14px 6px 12px;display:flex;flex-direction:column;align-items:center;gap:8px;cursor:pointer;box-shadow:var(--shadow);transition:transform .15s,background .2s,color .2s}
.vbtns button:active{transform:scale(.96)}
.vbtns svg{width:44px;height:44px;padding:10px;border-radius:14px;background:var(--soft);color:var(--ink-c);transition:background .2s,color .2s}
.vbtns button[aria-expanded=true]{color:#fff;background:linear-gradient(135deg,var(--c1),var(--c2));border-color:transparent}
.vbtns button[aria-expanded=true] svg{background:rgba(255,255,255,.2);color:#fff}
.vpanel{margin-top:12px;scroll-margin-top:12px;animation:rise .45s cubic-bezier(.2,.7,.2,1) both}
.vpanel h3{display:flex;align-items:center;gap:10px;margin:0 0 12px;font-size:14px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-c)}
.vpanel h3 svg{width:36px;height:36px;padding:8px;border-radius:12px;color:#fff;background:linear-gradient(135deg,var(--c1),var(--c2))}
.vpanel p{margin:0 0 10px}
.facts{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;margin:0 0 12px}
.facts dt{color:var(--muted);font-size:14px}.facts dd{margin:0;font-weight:600}
.quote{border-left:4px solid var(--c2);background:var(--soft);padding:10px 14px;border-radius:0 12px 12px 0;margin:0 0 10px}
.quote small{display:block;color:var(--muted);margin-top:4px;font-size:12.5px}
.ranks{width:100%;border-collapse:collapse;margin-bottom:6px}
.ranks td{padding:8px 4px;border-bottom:1px solid var(--line);vertical-align:top}
.ranks td:first-child{color:var(--muted);font-size:14px;width:44%}
.ranks td:last-child{font-weight:600}
.nr{color:var(--muted);font-weight:400;font-style:italic;font-size:14px}
.tree{list-style:none;margin:0 0 6px;padding:0}
.tree li{position:relative;padding:4px 0 4px 26px}
.tree li::before{content:"";position:absolute;left:8px;top:0;bottom:0;border-left:2px solid var(--line)}
.tree li::after{content:"";position:absolute;left:3px;top:12px;width:12px;height:12px;border-radius:50%;background:var(--card);border:2px solid var(--c2)}
.tree li:last-child::after{background:var(--c2)}
.tree small{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-right:6px}
.stats2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.stats2 div{background:var(--soft);border-radius:14px;padding:10px 12px}
.stats2 b{display:block;font-family:var(--serif);font-size:28px;line-height:1.1;color:var(--ink-c)}
.stats2 small{color:var(--muted);font-size:12.5px}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 12px;padding:0;list-style:none}
.tags li{background:var(--soft);color:var(--ink-c);border-radius:999px;padding:4px 11px;font-size:14px;font-weight:600}
.tags.muted li{background:transparent;border:1px solid var(--line);color:var(--muted);font-weight:500}
.vpanel h4{margin:12px 0 4px;font-size:15px}
.iucn{display:flex;align-items:center;gap:12px;margin:4px 0 12px}
.iucn b{display:grid;place-items:center;width:52px;height:52px;border-radius:50%;font-size:17px;border:2px solid rgba(0,0,0,.15)}
input.chem-filter{width:100%;box-shadow:none;font:inherit;font-size:16px;padding:10px 14px;border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--ink);margin:0 0 10px}
.chems{list-style:none;margin:0 0 6px;padding:0 4px 0 0;max-height:360px;overflow-y:auto;overflow-x:hidden;display:grid;grid-template-columns:1fr 1fr;gap:0 14px;align-content:start;font-size:14.5px}
.chems li{padding:3px 0;min-width:0;overflow-wrap:anywhere}
.chems a{color:var(--ink-c);text-decoration:none;border-bottom:1px dotted var(--c2)}
.papers{list-style:none;margin:0 0 6px;padding:0;counter-reset:p}
.papers li{padding:10px 0;border-bottom:1px solid var(--line)}
.papers a{font-weight:600;text-decoration:none;color:var(--ink)}
.papers a:hover{text-decoration:underline}
.papers small{display:block;color:var(--muted);font-size:13px;margin-top:3px}
.note{background:var(--soft);border-radius:12px;padding:8px 12px;font-size:14px;margin:0 0 10px;color:var(--ink-c)}
.src{margin-top:12px;background:#eef4ff;border:1px solid #d6e4ff;border-radius:14px;padding:10px 14px;font-size:13.5px}
.src b{display:block;color:#1d4ed8;font-size:12px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px}
.src ol{margin:0;padding-left:20px}.src li{margin:3px 0}
.src a{color:#1d4ed8;overflow-wrap:anywhere}
.src small{display:block;color:#64748b;margin-top:6px}
@media (prefers-color-scheme:dark){
 .vbtns button,.vbtns svg,.vpanel h3,.stats2 b,.tags li,.chems a,.note{color:var(--ink-c-d)}
 .vbtns svg,.stats2 div,.tags li,.quote,.note{background:var(--soft-d)}
 .vbtns button[aria-expanded=true],.vbtns button[aria-expanded=true] svg{color:#fff}
 .src{background:#141c2e;border-color:#24304a}.src b,.src a{color:#93b4ff}
}
@media (max-width:360px){.chems{grid-template-columns:1fr}}
"""

JS = """<script>
(function(){var bs=[].slice.call(document.querySelectorAll('.vbtns button'));
bs.forEach(function(b){b.addEventListener('click',function(){var open=b.getAttribute('aria-expanded')==='true';
bs.forEach(function(x){x.setAttribute('aria-expanded','false');document.getElementById(x.getAttribute('aria-controls')).hidden=true;});
if(!open){b.setAttribute('aria-expanded','true');var p=document.getElementById(b.getAttribute('aria-controls'));p.hidden=false;
p.style.animation='none';p.offsetHeight;p.style.animation='';
setTimeout(function(){p.scrollIntoView({behavior:'smooth',block:'start'});},60);}});});
var f=document.querySelector('.chem-filter');if(f){var li=[].slice.call(document.querySelectorAll('.chems li'));
f.addEventListener('input',function(){var t=f.value.trim().toLowerCase();li.forEach(function(x){x.hidden=x.textContent.toLowerCase().indexOf(t)<0;});});}
})();
</script>"""


def load(slug):
    f = VERIFIED_DIR / f"{slug}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def svg(path):
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{path}</svg>')


def tags(items, cls="tags"):
    return f'<ul class="{cls}">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"


def body_taxonomy(s):
    rows = "".join(f"<tr><td>{e(r)}</td><td>{e(v)}</td></tr>" for r, v in s["rows"] if v)   # empty ranks are hidden
    out = f'<table class="ranks">{rows}</table>'
    if s.get("authority"):
        out += f'<p class="note">Name with authority: <i>{e(s["authority"])}</i></p>'
    if s.get("note"):
        out += f'<p class="note">{e(s["note"])}</p>'
    return out


def body_conservation(s):
    out = ["<h4>IUCN Red List</h4>"]
    if s.get("iucn"):
        code, name = s["iucn"]
        bg = IUCN_COLOURS.get(code, "#ccc")
        fg = "#fff" if code in ("EX", "EW", "CR") else "#111"
        out.append(f'<div class="iucn"><b style="background:{bg};color:{fg}">{e(code)}</b><span><strong>{e(name)}</strong></span></div>')
    else:
        out.append(f"<p>{NR}</p>")
    out.append("<h4>Status in India (published checklists)</h4>")
    if s["india"]:
        rows = [((pl if pl != "IN" else "India"), m, src) for pl, m, src in s["india"]]
        # Kew's World Checklist (WCVP) is the authority on native ranges: where it covers a
        # region, other checklists for that region are not shown (avoids "native" + "introduced").
        wcvp = {pl for pl, _, src in rows if "World Checklist of Vascular Plants" in src}
        rows = [r for r in rows if r[0] not in wcvp or "World Checklist of Vascular Plants" in r[2]]
        seen = list(dict.fromkeys((pl, m) for pl, m, _ in rows))
        seen.sort(key=lambda x: x[0] != "India")      # mainland India (includes Andhra Pradesh) first
        out.append('<ul class="papers">' + "".join(f"<li><b>{e(pl)}</b>: {e(m)}</li>" for pl, m in seen) + "</ul>")
    else:
        out.append(f"<p>{NR}</p>")
    out.append("<h4>Endemic to</h4>" + (tags(s["endemic"]) if s["endemic"] else f"<p>{NR}</p>"))
    return "".join(out)


def body_phytochemicals(s):
    c = s["compounds"]
    if not c:
        return f"<p>{NR}</p>"
    lis = "".join(f'<li><a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["name"])}</a></li>' for x in c)
    return (f'<div class="stats2"><div><b>{len(c)}</b><small>compounds reported</small></div>'
            f'<div><b>PubChem</b><small>tap a compound to open it</small></div></div>'
            f'<input class="chem-filter" type="search" placeholder="Find a compound…" aria-label="Find a compound">'
            f'<ul class="chems">{lis}</ul>')


RENDER = {"taxonomy": body_taxonomy, "phytochemicals": body_phytochemicals, "conservation": body_conservation}


def render(slug):
    """HTML for the 3-button block, or '' when no verified data was fetched for this plant."""
    d = load(slug)
    if not d:
        return ""
    secs = d["sections"]
    btns, panels = [], []
    for key, label, path in BUTTONS:
        pid = f"v-{key}"
        btns.append(f'<button type="button" aria-expanded="false" aria-controls="{pid}">{svg(path)}{e(label)}</button>')
        panels.append(f'<section class="card vpanel" id="{pid}" hidden><h3>{svg(path)}{e(label)}</h3>'
                      f'{RENDER[key](secs[key])}</section>')
    return (f'<section class="vf reveal"><div class="vf-head"><h2>Explore this plant</h2>'
            f'<small>Verified scientific databases</small></div>'
            f'<div class="vbtns">{"".join(btns)}</div>{"".join(panels)}</section>')
