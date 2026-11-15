"""Collect cited scientific data for each plant from verified public databases.

Writes data/verified/<slug>.json. Each plant page shows it behind 3 buttons:
Taxonomy, Phytochemicals and Conservation. Every section stores its exact source
links and the date retrieved. Nothing is written by hand or guessed: if a database
has no record, the page says "Not recorded in these databases".

Sources:
  Taxonomy ........ GBIF Backbone Taxonomy + NCBI Taxonomy
  Phytochemicals .. Wikidata compound-species links (LOTUS natural products database),
                    each compound linked to PubChem; IMPPAT linked for Indian plants
  Conservation .... IUCN Red List category (via GBIF), native/introduced status in India
                    from published checklists (WCVP, GRIIS via GBIF), endemism (Wikidata)

Usage:  python scripts/fetch_verified.py                      # all plants
        python scripts/fetch_verified.py azadirachta-indica   # one plant
"""
import datetime as dt
import json
import re
import sys
import time
import xml.etree.ElementTree as ET

import requests

from common import ROOT, load_plants

OUT_DIR = ROOT / "data" / "verified"
UA = {"User-Agent": "CampusFloraBuild/1.0 (educational botanical garden website; python-requests)"}
TIMEOUT = 40
AP_GADM = "IND.2_1"          # GADM code for Andhra Pradesh

IUCN_NAMES = {
    "EX": "Extinct", "EW": "Extinct in the Wild", "CR": "Critically Endangered",
    "EN": "Endangered", "VU": "Vulnerable", "NT": "Near Threatened",
    "LC": "Least Concern", "DD": "Data Deficient", "NE": "Not Evaluated",
}


def get(url, params=None, as_json=True, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code}")
            r.raise_for_status()
            return r.json() if as_json else r
        except (requests.RequestException, ValueError):
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1) ** 2)


def safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except (requests.RequestException, ValueError, KeyError, ET.ParseError) as ex:
        print(f"    ! {fn.__name__}: {ex}")
        return None


def sparql(query):
    return get("https://query.wikidata.org/sparql", {"query": query, "format": "json"})["results"]["bindings"]


# ---------- database lookups ----------

def gbif_match(name):
    d = get("https://api.gbif.org/v1/species/match", {"name": name, "kingdom": "Plantae", "strict": "true"})
    return d if d.get("usageKey") and d.get("matchType") != "NONE" else None


def ncbi_taxon(name):
    time.sleep(0.4)
    ids = get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
              {"db": "taxonomy", "term": f'"{name}"[Scientific Name]', "retmode": "json", "tool": "campusflora"}
              )["esearchresult"]["idlist"]
    if not ids:
        return None
    t = None
    for attempt in range(4):        # NCBI sometimes answers with an empty/error page when busy
        time.sleep(0.5 + 3 * attempt)
        r = get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                {"db": "taxonomy", "id": ids[0], "retmode": "xml", "tool": "campusflora"}, as_json=False)
        t = ET.fromstring(r.content).find("Taxon")
        if t is not None:
            break
    if t is None:
        raise ValueError("NCBI returned no taxon record")
    lineage = [(x.findtext("Rank"), x.findtext("ScientificName")) for x in (t.find("LineageEx") if t.find("LineageEx") is not None else [])]
    lineage.append((t.findtext("Rank"), t.findtext("ScientificName")))
    return {"id": ids[0], "lineage": lineage}


def section_taxonomy(p, g, nc):
    ranks = {r: n for r, n in (nc["lineage"] if nc else [])}
    rows = [["Kingdom", (g or {}).get("kingdom")], ["Division (Phylum)", (g or {}).get("phylum")],
            ["Class", (g or {}).get("class")], ["Subclass", ranks.get("subclass")],
            ["Order", (g or {}).get("order")], ["Family", (g or {}).get("family")],
            ["Subfamily", ranks.get("subfamily")], ["Tribe", ranks.get("tribe")],
            ["Genus", (g or {}).get("genus")], ["Species", (g or {}).get("species") or p["scientific_name"]]]
    src = []
    if g:
        src.append([f"GBIF Backbone Taxonomy (key {g['usageKey']})", f"https://www.gbif.org/species/{g['usageKey']}"])
    if nc:
        src.append([f"NCBI Taxonomy (ID {nc['id']})", f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={nc['id']}"])
    note = None
    if g and g.get("status") and g["status"] != "ACCEPTED":
        note = f"GBIF lists this name as {g['status'].lower()}; accepted name: {g.get('species')}."
    return {"rows": rows, "authority": (g or {}).get("scientificName"), "note": note, "sources": src}


def wikidata_taxa(p, g):
    """Wikidata items for this plant: by exact name, by the hybrid spelling ("Genus × epithet")
    and by GBIF taxon ID. Returns a SPARQL VALUES list such as 'wd:Q1 wd:Q2', or None."""
    genus, _, epithet = p["scientific_name"].partition(" ")
    names = {p["scientific_name"], f"{genus} × {epithet}"}
    keys = {str(g["usageKey"]), str(g.get("acceptedUsageKey") or g["usageKey"])} if g else set()
    parts = [f'{{ ?t wdt:P225 "{n}" }}' for n in sorted(names)] + [f'{{ ?t wdt:P846 "{k}" }}' for k in sorted(keys)]
    rows = sparql("SELECT DISTINCT ?t WHERE { " + " UNION ".join(parts) + " }")
    items = sorted({r["t"]["value"].rsplit("/", 1)[1] for r in rows})
    return " ".join(f"wd:{q}" for q in items) or None


# Regions of Kew's World Checklist (WCVP) that lie inside India.
INDIA_WCVP = {"India", "Assam", "Andaman Is.", "Nicobar Is.", "Laccadive Is."}


def section_conservation(p, g, taxa):
    out = {"iucn": None, "india": [], "endemic": [], "sources": []}
    name = p["scientific_name"]
    if g:
        key = g.get("acceptedUsageKey") or g["usageKey"]
        iucn = safe(get, f"https://api.gbif.org/v1/species/{key}/iucnRedListCategory")
        code = (iucn or {}).get("code")
        if code:
            out["iucn"] = [code, IUCN_NAMES.get(code, code)]
            out["sources"].append(["IUCN Red List category (published via GBIF)", f"https://www.gbif.org/species/{key}"])
        dist = (safe(get, f"https://api.gbif.org/v1/species/{key}/distributions", {"limit": 300}) or {}).get("results", [])
        seen = set()
        for d in dist:
            place = d.get("locality") or d.get("country") or ""
            means = (d.get("establishmentMeans") or "").lower()
            if "World Checklist of Vascular Plants" in (d.get("source") or "") and place in INDIA_WCVP:
                means = means or "native"   # WCVP flags introduced regions; unflagged regions are native
            if (d.get("country") == "IN" or place in INDIA_WCVP or "india" in place.lower()) and means:
                k = ("India" if place == "IN" else (place or "India"), means)
                if k not in seen:
                    seen.add(k)
                    out["india"].append([k[0], k[1], (d.get("source") or "")[:140]])
            if d.get("endemic") and place:
                out["endemic"].append(place)
        if out["india"]:
            out["sources"].append(["Published checklists (GBIF species distributions)", f"https://www.gbif.org/species/{key}"])
    rows = (safe(sparql, f'SELECT ?t ?pLabel WHERE {{ VALUES ?t {{ {taxa} }} ?t wdt:P183 ?p . '
                         f'SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}') or []) if taxa else []
    for r in rows:
        out["endemic"].append(r["pLabel"]["value"])
    if rows:
        out["sources"].append(["Wikidata: 'endemic to' statement", rows[0]["t"]["value"]])
    out["endemic"] = sorted(set(out["endemic"]))
    out["sources"].append(["IUCN Red List search", f"https://www.iucnredlist.org/search?query={name.replace(' ', '%20')}"])
    return out


def section_phytochemicals(p, taxa):
    if not taxa:
        return {"compounds": [], "sources": []}
    rows = safe(sparql,
                f'SELECT DISTINCT ?t ?c ?cLabel ?cid ?ref WHERE {{ VALUES ?t {{ {taxa} }} ?c p:P703 ?st . ?st ps:P703 ?t . '
                f'OPTIONAL {{ ?c wdt:P662 ?cid }} '
                f'OPTIONAL {{ ?st prov:wasDerivedFrom/pr:P248 ?refw . ?refw wdt:P356 ?ref }} '
                f'SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }} LIMIT 600') or []
    comps = {}
    for r in rows:
        label = r["cLabel"]["value"]
        if re.fullmatch(r"Q\d+", label):          # no English name in Wikidata: skip
            continue
        c = comps.setdefault(r["c"]["value"], {"name": label, "url": None, "dois": set()})
        if "cid" in r:
            c["url"] = f"https://pubchem.ncbi.nlm.nih.gov/compound/{r['cid']['value']}"
        if "ref" in r:
            c["dois"].add(r["ref"]["value"])
    def sort_key(x):   # alphabetical by the name itself, ignoring prefixes like "(+)-", "11beta-", "2-"
        core = re.sub(r"^(?:[\W\d_−±αβγδ]|(?<![a-z])(?:alpha|beta|gamma|delta|cis|trans|[RSEZDLopm])(?![a-z]))+", "",
                      x["name"], flags=re.I)
        return (len(x["name"]) > 32, core.lower())
    items = sorted(({"name": c["name"], "url": c["url"] or q, "refs": sorted(c["dois"])[:3]} for q, c in comps.items()),
                   key=sort_key)
    src = []
    if rows:
        src += [["Wikidata compound–species links (from the LOTUS natural products database)", rows[0]["t"]["value"]],
                ["LOTUS natural products initiative", "https://lotus.naturalproducts.net/"]]
    src += [["IMPPAT: Indian Medicinal Plants, Phytochemistry And Therapeutics", "https://cb.imsc.res.in/imppat/"]]
    return {"compounds": items, "sources": src}


def fetch(p):
    name = p["scientific_name"]
    g = safe(gbif_match, name)
    nc = safe(ncbi_taxon, name)
    taxa = safe(wikidata_taxa, p, g)
    return {
        "slug": p["slug"], "scientific_name": name,
        "retrieved": dt.date.today().isoformat(),
        "sections": {
            "taxonomy": section_taxonomy(p, g, nc),
            "phytochemicals": section_phytochemicals(p, taxa),
            "conservation": section_conservation(p, g, taxa),
        },
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plants = load_plants()
    only = set(sys.argv[1:])
    for p in plants:
        if only and p["slug"] not in only:
            continue
        f = OUT_DIR / f"{p['slug']}.json"
        if not only and f.exists() and json.loads(f.read_text())["retrieved"] == dt.date.today().isoformat():
            continue                    # already fetched today (lets an interrupted run resume)
        print(f"- {p['scientific_name']}")
        data = fetch(p)
        f.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        time.sleep(1)


if __name__ == "__main__":
    main()
