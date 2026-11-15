# Campus Flora: Central Tribal University of Andhra Pradesh

Every plant species on campus has a tag with its scientific name, common names,
family and a **QR code**. Scanning the code opens that plant's page on this website:

    https://ctuap-flora.github.io/plants/            ← list of all plants (with search)
    https://ctuap-flora.github.io/plants/p/<slug>/   ← one page per plant

The QR codes contain **only** the page address. The information on the page comes from
`data/plants.yaml`. So you can add or correct details at any time, and the **same printed
tags** will show the new information. You never need to reprint tags to update them.

---

## ⚠️ Never change these (or every printed tag stops working)

1. **A plant's `slug`** (e.g. `azadirachta-indica`). It is inside the QR code. Even if a
   plant's scientific name changes, keep the old slug. Just edit `scientific_name` and
   add the old name as `synonym`.
2. **The repository name** `plants`.
3. **The organization name** `CTUAP-FLORA`.
4. **`base_url` in `config.yaml`**, once tags are printed.

Never delete a plant entry that has a printed tag. The build checks this and stops with an
error if a slug listed in `qr/slugs.lock` disappears.

---

## How to add details for a plant (no installation needed)

1. On GitHub, open **`data/plants.yaml`** and click the **pencil icon** (Edit).
2. Find the plant (press Ctrl+F and type its name).
3. Fill in any of the empty fields. Leave a field empty if you don't have checked information.

   ```yaml
     - slug: azadirachta-indica                 # ← never change
       scientific_name: Azadirachta indica
       synonym: ""
       common_names: ["Neem", "Vepa", "Margosa"]
       family: Meliaceae
       description: |
         A fast-growing evergreen tree, 15–20 m tall.

         A second paragraph is separated by an empty line.
       uses:
         - Twigs used as a toothbrush
         - Seed oil used in soaps
       native_to: Indian subcontinent
       flowering_season: March – May
       photos:
         - file: azadirachta-indica-1.jpg
           caption: Flowering branch
           credit: Photo by the Botany Department
       notes: Planted near the main library.
   ```

   * One-line text: write it after the colon.
   * Several lines or paragraphs: write `|` after the colon, then indent the text by
     **2 more spaces** than the field name.
   * A list of points: start each line with `- `.
4. Click **Commit changes**. After about a minute the website is updated automatically.
   You can watch progress in the **Actions** tab. A green tick means it worked. A red cross
   means there is a mistake in the file (usually indentation). Click it to see the message.

### Adding photos
1. Go to the **`photos/`** folder, click **Add file → Upload files**, and upload the image.
   Use a lowercase name such as `azadirachta-indica-1.jpg`. Resize large photos to about
   1600 px wide first so pages load fast on phones.
2. Add it under `photos:` for that plant, as shown above (replace `photos: []`).

## How to add a new plant

1. Add a new block at the end of `data/plants.yaml` (copy an existing one).
2. Set `slug` to genus-species in lowercase with hyphens, e.g. `ficus-religiosa`.
   It must be unique. **Choose it carefully. It is permanent once printed.**
3. Commit. The page appears at `https://ctuap-flora.github.io/plants/p/ficus-religiosa/`.
4. Run `python scripts/fetch_verified.py <slug>` to collect its Taxonomy, Phytochemicals
   and Conservation data, and commit the new file in `data/verified/`.
5. Make the QR code and tag on a computer (below), check them with `verify.py`, and print
   only the new tag. Existing QR codes do not change, because they depend only on their own slug.

## The 3 buttons: Taxonomy, Phytochemicals, Conservation

Each plant page has 3 buttons. Their content is collected automatically from verified
scientific databases. It is **not typed by hand**, so do not edit these files manually.

| Button | Comes from |
|---|---|
| Taxonomy | GBIF Backbone Taxonomy, NCBI Taxonomy (ranks with no record are hidden) |
| Phytochemicals | LOTUS natural products database (via Wikidata); each compound links to PubChem |
| Conservation | IUCN Red List category (via GBIF); native/introduced status in India from published checklists (WCVP, GRIIS); endemism (Wikidata) |

The data is saved in `data/verified/<slug>.json`, one file per plant. Each file also keeps
the exact source links and the date the data was retrieved (the links are not shown on
the page). When a database has no record, the page says "Not recorded in these databases".

**To refresh the data** (for example once a year, or after adding a new plant):

```bash
python scripts/fetch_verified.py                    # all plants (takes a few minutes)
python scripts/fetch_verified.py ficus-religiosa    # just one plant
```

Then commit the changed files in `data/verified/`.

## Running the scripts on a computer

Needs Python 3.10+ (and `pdftoppm` from poppler-utils if you want `verify.py` to check `tags.pdf`).

```bash
pip install -r requirements.txt
python scripts/fetch_verified.py # Taxonomy / Phytochemicals / Conservation → data/verified/
python scripts/build.py          # website → _site/ (GitHub does this automatically)
python scripts/make_qr.py        # qr/<slug>.png and qr/<slug>.svg for every plant
python scripts/make_tags.py      # tags.pdf: A4, 5 tags per page, dashed cut lines
python scripts/verify.py --online  # decode every QR code + load every live page
```

Commit the new files in `qr/` and `tags.pdf` afterwards.

## What's in this repository

| Path | What it is |
|---|---|
| `data/plants.yaml` | **All plant information.** The only file you normally edit. |
| `data/verified/` | Taxonomy, phytochemicals and conservation data (automatic, with sources) |
| `config.yaml` | Website address (`base_url`) and university name |
| `photos/` | Plant photos used on the pages |
| `qr/` | QR codes (PNG for printing, SVG for designers) + `slugs.lock` |
| `tags.pdf` | Printable tag sheet |
| `scripts/` | Small Python scripts that build everything |
| `.github/workflows/pages.yml` | Rebuilds and publishes the website on every change |

## Printing tips
* Print `tags.pdf` at **100% / "Actual size"**, not "Fit to page".
* Each QR code is about 48 mm wide and uses the strongest error correction (level H), so
  it still scans when slightly scratched or dirty.
* For outdoor use, laminate the tags or print on weatherproof (PVC/synthetic) sheets.
* Test-scan a few printed tags with a phone before printing everything.
