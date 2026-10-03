# IWC US capture — completed

Captured and validated **225 / 225 distinct wristwatch references** from the
[official IWC US catalogue](https://www.iwc.com/us-en/watches), on **4 October
2026**, approximately 02:42–03:09 India time. The exported reference set
and every collection count agree with the published catalogue snapshot.
There are zero extraction errors, duplicate references or record-validation errors.

| Published collection | References |
|---|---:|
| Pilot’s Watches | 84 |
| Portugieser | 59 |
| Portofino | 56 |
| Ingenieur | 19 |
| Aquatimer | 7 |
| **Total** | **225** |

**210 references have published USD prices; 15 are unpriced in this snapshot.**
These are suggested US retail prices, with VAT excluded where stated. This dated
capture describes the current US catalogue, not all historical IWC watches or
stock availability.

## Deliverables

- [40-column CSV](../scraping_runs/iwc-us-capture/exports/iwc_watches.csv).
- [Full JSONL](../scraping_runs/iwc-us-capture/exports/iwc_watches.jsonl): mapped fields,
  all four raw technical sections, selected structured data, catalogue attributes
  and tracking fields, strap descriptions, editorial copy, gallery links, related
  watch URLs, source hashes and provenance.
- [Completion manifest](../scraping_runs/iwc-us-capture/manifest.json) and
  [validation report](../scraping_runs/iwc-us-capture/validation_report.json).
- Reusable [normal-browser collector](../tools/capture_iwc_browser.mjs),
  [offline exporter](../tools/capture_iwc_us.py), [parser](../watch_atlas_scraper/iwc_us_data.py),
  [validator](../tools/validate_iwc_us.py), and [instructions](../docs/iwc_us.md).
- Source inventory, browser cache, SQLite state and full content-addressed rendered
  HTML under `scraping_runs/iwc-us-capture/`.

Capture data are local and ignored by Git. This run did not import or publish
IWC records to the Watch Atlas dashboard.

## Collection method

The old `/us/en/watches.html` address redirects to `/us-en/watches`. The normal
in-app browser displays the new public catalogue and product pages. Plain HTTP
returned 403 and was not retried. No proxy, stealth options, CAPTCHA handling,
account access or private endpoints were used.

One tab followed only actual published watch links, with navigation starts at
least three seconds apart. Progress was saved after each product. The complete
catalogue DOM includes all 225 cards, even though the visible grid initially shows
only the first eight per larger collection. No generated reference numbers,
search filters or pagination requests were needed.

The site publishes complete Overview, Features, Case and Movement tables in a
`noscript` fallback. All four sections are preserved in each full DOM snapshot.
The interactive interface initially mounts only Overview; the exporter reads the
complete public fallback. Canonical URL, selected table reference and Product
JSON-LD (when present) establish watch identity. Unpriced specialist pages that
omit Product JSON-LD retain their selected table, introduction and gallery links.
Related watches never supply a missing price or selected specification.

The official robots text was read through the web research tool and recorded
with its provenance. The separately saved direct HTTP response is a 403, rather
than being represented as a successful robots retrieval. Reviewed rules allow
the catalogue/product paths used here.

## Mapping and disclosed gaps

Case / Height maps to thickness. Case / Strap width maps to `between_lugs`;
Buckle width remains in raw specifications and never supplies lug-to-lug length.
Movement supplies calibre, power reserve, frequency with original units and
jewel count. Features retain glass specifications and every other disclosed item.
Explicit strap material/colour words are mapped, and complete wording remains
in JSONL. No introduction year is inferred from catalogue publication timestamps.

| Normalized field | Populated |
|---|---:|
| reference_number | 225 / 225 |
| parent_model | 225 / 225 |
| case_material | 223 / 225 |
| diameter | 224 / 225 |
| case_thickness | 224 / 225 |
| water_resistance | 224 / 225 |
| dial_color | 221 / 225 |
| movement | 225 / 225 |
| caliber | 225 / 225 |
| power_reserve | 224 / 225 |
| frequency | 225 / 225 |
| jewels | 225 / 225 |
| price | 210 / 225 |
| image_URL | 225 / 225 |

The technical tables omit case material for **IW328107 and IW389411**, and dial
colour for **IW345901, IW388304, IW388305 and IW388306**. **IW659803** omits diameter,
thickness, water resistance and power reserve. Those cells remain blank rather
than being inferred from the model name, a related watch or descriptive prose.
Its published frequency is only `(4 Hz)`; that original wording is retained.
All seven watches' product descriptions and full source pages remain available.
Other optional fields absent from technical tables remain blank.

## Verification

- **100 repository tests passed**, including eight IWC source and failure cases.
- **226 referenced source snapshots** passed SHA-256 and complete-HTML checks:
  one full catalogue and all 225 selected product pages.
- **900 technical sections** verified against the saved sources.
- Exact 40-column CSV/JSONL agreement and full fresh-parser agreement for every record.
- Every reference and family count reconciled with the published catalogue.
- All **210 visible selected prices** independently matched their catalogue prices,
  and Product offers were checked wherever provided.
- Zero detail failures, duplicate references or record-validation errors.

```sh
python3 -m tools.capture_iwc_us --output scraping_runs/iwc-us-capture
python3 -m tools.validate_iwc_us --output scraping_runs/iwc-us-capture
python3 -m unittest discover -s tests -p test_iwc_us.py
```
