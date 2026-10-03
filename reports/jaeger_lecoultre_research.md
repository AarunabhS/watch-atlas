# Jaeger-LeCoultre US capture — completed

Collected **197 distinct watch references** from the public US catalogs. Pages were captured on **3–4 October 2026, India time**. All watch identities, saved HTML hashes, shared fields and both exports passed offline validation.

The main listing has 186 cards. The specialist Calibre 101 and Hybris lists add nine watches. Three editorial URLs are watch product pages with explicit selected-watch metadata and references in their titles or watch-image captions. Their published URLs are retained. An Atmos clock is excluded. This reconciles to 197 distinct watches across 15 published collection labels. Historical Collectibles and other regional catalogs are outside this capture.

The collector uses one normal headless browser page, robots checks, a three-second minimum interval and resumable content-addressed snapshots. Plain HTTP access was denied; ordinary browser pages returned HTTP 200. The capture did not encounter browser access blocks or bypass human-verification challenges.

## Outputs

- `scraping_runs/jlc-personal-research/exports/jlc_watches.csv`: the exact 40-column project schema.
- `scraping_runs/jlc-personal-research/exports/jlc_watches.jsonl`: shared fields, additional technical details, all selected JSON-LD and watch tracking fields, both Reverso faces, calibre blocks, full technical accordions, watch-specific narratives and listing provenance.
- `manifest.json`, `validation.json`, `inventory.json`, `listing_pages.json` and `browser_cache.json`: completion, coverage, source identity and snapshot metadata.
- `snapshots/`: the full saved browser DOM and SHA-256 source hashes.

Capture outputs stay local and are ignored by Git. The dedicated Atlas importer publishes the normalized watch data separately.

## Verification

- **197 / 197 references**, with zero extraction or record validation errors.
- **201 listing and watch snapshots** verified.
- Every one of the 40 CSV fields agrees with JSONL and reparsed source data.
- **118 published USD prices**; request-only prices remain blank.
- **14 narrative-template pages** parsed alongside the standard technical template.
- **63 records** retain disagreements between the technical accordion and separate calibre block, rather than silently discarding either value.
- Rectangular dimensions and movement thickness remain separate from case diameter and thickness.
- One source omits its calibre label (Q3848423), and one narrative page omits an explicit case diameter (Q13125S2); those fields remain blank. Undisclosed specifications are never inferred from another watch.

See [collector instructions](../docs/jaeger_lecoultre.md), [parser](../watch_atlas_scraper/jlc_data.py), [collector](../tools/scrape_jlc.py) and [validator](../tools/validate_jlc.py).

Official discovery sources: [all watches](https://www.jaeger-lecoultre.com/us-en/watches/all-watches), [Calibre 101](https://www.jaeger-lecoultre.com/us-en/watches/calibre-101), [high complication](https://www.jaeger-lecoultre.com/us-en/watches/high-complication), [Hybris](https://www.jaeger-lecoultre.com/us-en/watches/hybris).
