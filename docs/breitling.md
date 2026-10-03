# Breitling personal research collector

This collector follows the [official US English all-watches catalog](https://www.breitling.com/us-en/watches/all/)
and the watch detail URLs published on its product cards. It uses the same
40-column schema, response cache, source snapshots and field provenance as the
Patek collector. Data stays in the local research directory.

## Run

Use Python 3.11+ with `lxml`, Node.js and Playwright. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
npm install --prefix .scraper-browser playwright
node .scraper-browser/node_modules/playwright/cli.js install chromium
.venv/bin/python -m tools.scrape_breitling \
  --playwright-path "$PWD/.scraper-browser/node_modules/playwright" \
  --output scraping_runs/breitling-personal-research
```

See [Playwright's library instructions](https://playwright.dev/docs/library) for
browser installation. An existing Chrome executable can be supplied with
`--chrome`; `--node` selects another Node executable. The collection in this
workspace used its existing bundled Python, Node and Playwright with installed
Chrome; no global packages or browsers were installed.

Use `--limit 3` for a pilot; omit the limit for the complete catalog. The US
market selection is intentional: prices and availability differ by market.
Curl is the default transport when available; `--transport urllib` selects the
Python standard library instead.

## Why discovery uses a browser

During the live inspection, `all/?page=2` returned page one's watch cards and
search results in the downloaded HTML. The page number in the URL and initial
UI state did not establish which products were actually displayed. After
hydration, the website's own pagination correctly updated the rendered cards.

`tools/discover_breitling.mjs` opens an isolated headless browser, waits for
hydration, follows the site's actual pagination links and saves each rendered
DOM. It checks the declared page count, per-page card count, distinct references
and final catalog count. The Python parser reads only those rendered grid cards,
excluding recommendations and the stale page-one JSON hits. Browser discovery
is cached for 24 hours. The optional `--discovery http` mode rejects incomplete
pagination; it does not silently reuse repeated page-one data.

Detail pages expose the selected watch in public `__NEXT_DATA__`, so they are
downloaded sequentially without a browser. Missing templates and reference
mismatches produce explicit errors. Each record is committed separately so an
interrupted run can resume.

## Exports and source data

- `exports/breitling_watches.csv`: the original 40 columns, in their original order.
- `exports/breitling_watches.jsonl`: mapped columns, every selected product and variant field, structured product data, visible technical table, catalog card data, images, source hashes, provenance and diagnostics.
- `inventory.json` and `listing_pages.json`: all discovered references and their published detail URLs.
- `rendered_pages/`: browser DOM snapshots and a manifest with hashes, page URLs and reference counts.
- `snapshots/` and `state.sqlite`: original HTTP responses, durable records, cache and request events.
- `manifest.json`: coverage, errors, collections, prices and missing fields.
- `validation.json`: the result of checking the exports against all saved source snapshots.

Coverage means the distinct references in the US all-watches listing. Related
reference numbers and strap configurations remain in the raw product data;
they are not counted as additional catalog references without a published
listing card. Historical and other-market catalogs are outside this run.

## Mapping details

The parser uses English attribute display translations. Internal translation
codes cannot replace readable specifications. Case diameter, case thickness and
lug width use the visible technical table: observed CMS attributes labelled
these values in centimeters while the displayed table used millimeters. Both
representations are retained, with `source_discrepancies` identifying conflicts.
Watch-head weight remains separate from total product weight. Placeholder zero
weights stay blank in the legacy column.

Prices come from the selected variant's positive gross amount and currency,
with a matching structured offer as a fallback. Zero and absent prices are not
invented. Explicit launch dates supply introduction years, with the full date
retained separately. Limited-edition booleans retain both true and false values.

A functional bezel description is not used as bezel material. The source label
“Metal bracelet” is preserved as `strap_color_label` while the color column stays
blank. Missing case finish, numerals, lug-to-lug dimensions and other unstated
legacy specifications also stay blank; their absence is measured in the manifest.

## Request behavior, resume and validation

The collector uses a declared WatchAtlasCatalogBot identity, checks applicable
robots rules, uses one browser session for discovery and requests details at
least three seconds apart. The browser honors the same minimum delay and any
applicable longer crawl delay. It records image URLs without downloading images.
Access blocks and rate limits stop collection. Transient connection failures
have bounded retries and remain visible as incomplete records.

Run the same command to resume; saved records are skipped. After improving a
mapping, `--reparse` reuses fresh cached responses. Use one collector process per
run directory. To verify the completed local exports without network requests:

```sh
.venv/bin/python -m tools.validate_breitling \
  --output scraping_runs/breitling-personal-research
.venv/bin/python -m unittest discover -s tests -v
```

The validator checks the full reference set, all source hashes, selected product
identity, raw field preservation, reproducible mappings, provenance and exact
CSV/JSONL agreement. Synthetic fixtures cover stale server pagination, incomplete
browser discovery, unit conflicts, variant prices and unrelated product data.
