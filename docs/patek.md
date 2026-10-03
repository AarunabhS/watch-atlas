# Patek Philippe personal research collector

The collector follows the English [official watch finder](https://www.patek.com/en/collection/watch-finder)
and the watch pages linked in its published catalog. A browser inspection showed
that the watch finder and technical detail panels are present in the page's
`__NEXT_DATA__` JSON. Browser automation is therefore unnecessary for downloading
these pages.

The 2 October 2026 inventory contains **283 current timepieces**: **232 wristwatches,
20 pocket watches and 31 clocks**. The watch exports target all 252 watch references.
Clocks remain in the separate inventory file. Another 21 entries fall outside the
selected availability/run-out dates; they are preserved separately, without
assuming that they are discontinued.

## Run

From the repository root, with Python 3.11+ and `lxml`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m tools.scrape_patek --output scraping_runs/patek-personal-research
```

The bundled Python runtime in this Codex workspace already has `lxml`. No global
packages were installed. Curl, when installed, is the default HTTP transport;
`--transport urllib` uses the Python standard library instead. Both use the same
declared WatchAtlasCatalogBot identity and request checks. Curl avoided a slow
connection fallback observed with this machine's standard library transport.

The default date cutoff is the current date/time in India, recorded in the
manifest. An explicit historical cutoff can be supplied with `--as-of`, but it
filters the retrieved inventory rather than reconstructing a historical catalog.
Use `--limit 3` for a small pilot; omit it for the full catalog.

## Files

The run directory contains:

- `exports/patek_watches.csv`: all wristwatches and pocket watches, using the original 40 columns in their original order.
- `exports/patek_wristwatches.csv`: the wristwatch subset.
- `exports/patek_pocket_watches.csv`: the pocket watch subset.
- `exports/patek_watches.jsonl`: each record's mapped fields, all raw product and listing fields, assets, source hash, provenance and missing-field diagnostics.
- `current_inventory.json` and `not_current_inventory.json`: the complete retrieved catalog, including the clocks and date-filtered entries.
- `manifest.json`: expected/captured counts, missing fields, extraction errors and validation errors.
- `state.sqlite` and `snapshots/`: saved progress, response cache and original HTML, keyed by SHA-256.

These local research files are ignored by Git. The script does not publish the
records or merge them into the existing dashboard.

## Extraction

`watch_atlas_scraper/patek_data.py` reads only the main `WatchFinder` and
`ProductDetail` components. Header navigation and suggested models cannot supply
the current watch's specifications. Each detail reference must match its catalog
reference before the record is accepted.

Case dimensions come from the case fields, while movement dimensions remain
separate metadata. Linked CMS attributes are unwrapped, technical markup is
converted to plain text, and actual rendered product image URLs are selected
instead of Photoshop source files. All original datasource fields and linked
assets remain available in JSONL, even when they have no legacy CSV column.
`case_dimensions_display` preserves measurement labels such as diagonal or
10–4 o'clock diameter. The legacy `diameter` column may contain rectangular
dimensions and must not be treated as a round-case diameter for every watch.

Some pages contain different movement parts counts in a base CMS field and the
display field used by the visible technical panel. The exported parts count uses
the display field, and `source_discrepancies` preserves both values. Explicit
strap color clauses and case finish captions are mapped without using the dial
color or metal color as a substitute.

Absent prices, launch years, nicknames and other unstated values stay blank.
Availability dates are preserved separately and are not used as introduction
years. Some CMS attribute labels are in French even on English pages; their
original wording is preserved. Missing fields are measured without filling them
from related models or brand assumptions.

The manifest's `reference_coverage_complete` means every selected watch reference
was captured. It does not mean the manufacturer publishes every possible
specification or every legacy field.

## Request behavior and resume

The script sends sequential requests at least three seconds apart, honors the
applicable robots rules, restricts collection to Patek's official English catalog
paths and stops on access blocks or rate limits. It does not use login sessions,
rotating proxies or challenge solving. Image URLs are recorded without downloading
the image files.

Run the same command to resume. Already saved records are skipped. To improve a
mapping and reprocess saved pages, use:

```sh
.venv/bin/python -m tools.scrape_patek --output scraping_runs/patek-personal-research --reparse
```

Fresh cached pages are reused for 24 hours, with the same scope and robots checks.
The directory must be used by one collector process at a time.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The tests use invented fixtures shaped like the observed components. Live run
counts and errors are reported separately in the manifest. Missing embedded data
or a mismatched reference produces an explicit error so a site change cannot
silently produce the wrong watch.
