"""Multilingual support: English, Telugu, Hindi, Odia, Tamil, Malayalam.

Pages are built in English. Every translatable piece of text is wrapped as
    <span data-t="key">English text</span>
and a small script (i18n.js) swaps it for the chosen language. The visitor's choice
is remembered on their phone. All translations live in data/i18n.yaml.
"""
import html
import json

import yaml

from common import ROOT

e = html.escape
DATA = yaml.safe_load((ROOT / "data" / "i18n.yaml").read_text(encoding="utf-8"))
LANGS = DATA["languages"]                       # code -> native name, in display order
STRINGS = {**DATA["ui"], **DATA["terms"]}       # key -> {lang: text}
MISSING = set()                                 # keys used on pages but absent from i18n.yaml


def text(key, lang="en", **args):
    """The text for a key in one language (English fallback), with {placeholders} filled in."""
    entry = STRINGS.get(key)
    if entry is None:
        MISSING.add(key)
        s = key.split(":", 1)[-1]
    else:
        s = entry.get(lang) or entry.get("en") or key
    for k, v in args.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def t(key, tag="span", cls="", **args):
    """Translatable element. Arguments ({n}, {family}…) are stored so the script can refill them."""
    a = f' data-a="{e(json.dumps(args, ensure_ascii=False))}"' if args else ""
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-t="{e(key)}"{a}>{e(text(key, **args))}</{tag}>'


def term(prefix, value, tag="span", cls=""):
    """A database term such as a plant part or IUCN category, e.g. term('part', 'leaf')."""
    return t(f"{prefix}:{value}", tag=tag, cls=cls)


def switcher():
    """The language menu shown at the top of every page."""
    opts = "".join(f'<option value="{c}">{e(n)}</option>' for c, n in LANGS.items())
    return (f'<label class="langsel"><span class="sr" data-t="language">Language</span>'
            '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8">'
            '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/></svg>'
            f'<select id="lang" aria-label="Language">{opts}</select></label>')


def script():
    """Contents of _site/i18n.js: the translation table plus the code that applies it."""
    table = {k: {l: v for l, v in d.items() if v} for k, d in STRINGS.items()}
    return ("window.I18N=" + json.dumps(table, ensure_ascii=False, separators=(",", ":")) + ";\n" + r"""
(function(){
  var KEY='campusflora-lang', sel=document.getElementById('lang');
  function fill(s,a){for(var k in a){s=s.split('{'+k+'}').join(a[k]);}return s;}
  function apply(lang){
    document.documentElement.lang=lang;
    document.querySelectorAll('[data-t]').forEach(function(el){
      var d=I18N[el.getAttribute('data-t')];if(!d)return;
      var s=d[lang]||d.en;if(!s)return;
      var a=el.getAttribute('data-a');el.textContent=a?fill(s,JSON.parse(a)):s;});
    document.querySelectorAll('[data-tp]').forEach(function(el){
      var d=I18N[el.getAttribute('data-tp')];if(d)el.placeholder=d[lang]||d.en;});
    if(sel)sel.value=lang;
  }
  var lang='en';
  try{lang=localStorage.getItem(KEY)||'en';}catch(e){}
  if(!I18N.language[lang])lang='en';
  if(lang!=='en')apply(lang);else if(sel)sel.value='en';
  if(sel)sel.addEventListener('change',function(){
    try{localStorage.setItem(KEY,sel.value);}catch(e){}
    apply(sel.value);});
})();
""")


CSS = """
.langsel{position:relative;display:inline-flex;align-items:center;gap:6px;color:#fff;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);
 border-radius:999px;padding:6px 10px 6px 9px;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);font-weight:600;font-size:13px}
.langsel svg{width:16px;height:16px;flex:none}
.langsel select{appearance:none;-webkit-appearance:none;background:transparent;border:0;color:inherit;font:inherit;padding:0 14px 0 0;cursor:pointer;
 background-image:linear-gradient(45deg,transparent 50%,#fff 50%),linear-gradient(135deg,#fff 50%,transparent 50%);
 background-position:right 4px center,right 0 center;background-size:4px 4px,4px 4px;background-repeat:no-repeat}
.langsel select option{color:#111}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.telugu{font-family:"Noto Sans Telugu","Nirmala UI","Gautami",sans-serif}
/* Indian scripts: no extra letter-spacing or capitals (they break up letters) */
html:not([lang="en"]) .lbl,html:not([lang="en"]) .eyebrow,html:not([lang="en"]) .vpanel h3,html:not([lang="en"]) .taxo small,
html:not([lang="en"]) .pager small,html:not([lang="en"]) .stats small,html:not([lang="en"]) .related h2{letter-spacing:0;text-transform:none}
.chips.telugu li,.lbl+.chips.telugu li{letter-spacing:0}
"""
