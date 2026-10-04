# Watch Atlas

A responsive watch research portfolio and catalog for Arunabho Kanti Som.

**[Explore the live dashboard](https://www.arunabhosom.com/watch-atlas/)** · [GitHub Pages URL](https://aarunabhs.github.io/watch-atlas/)

The site contains a watch showcase, searchable catalog, collection insights, project process, data coverage, and a searchable inventory of 73 project files. The catalog contains **3,636 watches across eleven watchmakers**: 3,612 wristwatches and 24 pocket watches. It combines the 2023–2024 archive with 252 Patek Philippe and 402 Breitling references captured on 2 October 2026, plus 197 Jaeger-LeCoultre, 556 Omega, 216 Tudor and 225 IWC references captured on 3–4 October 2026. Capture dates and source markets appear in watch details; Tudor uses the India/INR snapshot and IWC the US/USD snapshot.

Collection insights compare six inferred watch segments, average wristwatch diameter, decorative gemstone mentions, movement families, and distinct calibers. Watchmaker selection updates all comparisons; chart selections open matching catalog references. Filters combine watchmaker, segment, movement family, gemstone detail, watch type and text search.

**Compare watches** lets users combine up to twelve personal requirements and shortlist up to six references. The current catalog offers 117 selectable comparison parameters, including price, dimensions, materials, movements, functions, dials, straps and additional published details. Comparisons support difference-only rows, saved shortlists, shareable links and CSV export. Budget filters keep currencies separate and missing values remain unknown.

Unavailable prices offer an exact-reference Google search. The optional Serper + Cloudflare backend enables inline reported-price results with source links, source dates, currency labels, caching and short request deadlines. The existing price worker is connected; its key stays on the server. See [setup and comparison documentation](docs/price-search-and-comparison.md).

The landing page uses original watchmaker image links in an animated showcase with pause and manual selection controls. The layout adapts to mobile screens and respects reduced-motion preferences. Technical archive information is confined to Project archive.

## Preview locally

Run `python3 -m http.server 4173 --directory dist` and open `http://localhost:4173`.

## Source

- `dist/index.html`: page structure and metadata.
- `dist/styles.css` and `dist/refinement.css`: visual design, responsive layouts and animation.
- `dist/app.js`: navigation, search, filters, detail panels, archive, and optional browser catalog tool.
- `dist/insights.js`: interactive comparisons and methodology notes.
- `dist/comparison-model.js`, `dist/comparison.js`, `dist/comparison.css`: personal requirements, shortlists and side-by-side comparison.
- `dist/price-lookup.js`, `dist/config.js`: reported-price controls and public backend configuration.
- `backend/`: optional Cloudflare price-search worker, catalog identity allowlist and deployment configuration.
- `dist/data.json`: normalized catalog and archive inventory derived from the preserved project files.

The catalog uses seven archived source tables, six completed official catalog imports, and exact-reference Rolex/Breguet refreshes. Repeated rows are coalesced by brand and reference, falling back to the source URL when a reference is absent. Later H. Moser source tables enrich earlier ones. Empty fields remain empty. Coverage measures the presence of ten core fields; it does not certify accuracy. Source provenance is retained. Fresh Rolex/Breguet records do not inherit unverified archive prices or currencies.

The preserved archive and original project files were not modified. The dashboard includes file metadata and selected watch data. Raw notebooks and private project documents remain outside the published repository.

## Interpreting insights

The primary segment is inferred from captured model names, collection labels and stated functions. Complications take priority, followed by chronographs, diving, travel and jewellery; remaining models fall under time & date. This is an analytical grouping rather than an official watchmaker taxonomy.

Diameter comparisons use 3,367 single wristwatch diameter measurements. Pocket watches, diagonal measurements, multiple dimensions and missing values are excluded. One 430 mm wall clock remains in the project data but is excluded from the watch catalog and comparisons. Miniature wristwatches with valid measurements remain included.

Gemstone mentions describe decorative stones in the captured specifications and descriptions. Sapphire crystals and movement-bearing jewel counts are excluded. A missing mention does not establish that a watch has no gemstones. Movement families use explicit recorded wording; unspecified types stay unspecified. Calibers are normalized and counted separately for each watchmaker.

Some source descriptions differ from their model labels. The comparisons describe the stored snapshot without independently verifying every specification or claiming complete current catalog coverage.

The application runs in the browser, with its prepared catalog bundled in `dist/data.json`. Watchmaker images and web fonts require an internet connection. Local preview is available through the server command above.

## GitHub Pages

GitHub Pages publishes the `dist` directory through `.github/workflows/pages.yml`. Every push to `main` deploys the current dashboard; the workflow can also be run manually from GitHub Actions. The catalog and comparison workspace require no build step, package installation, API key or backend. Inline reported-price searches use the separately deployed worker and server-side key described above.

The public site includes the prepared catalog and archive inventory. The original notebooks, spreadsheets and private project documents are not bundled in this repository.

## Catalog collector

The Patek-specific collector reads the official watch finder and each published
watch detail page for local personal, non-commercial research. Its current
run collected all **252 current watch references: 232 wristwatches and 20 pocket
watches**, with zero extraction errors. It preserves the
reviewed 40-column CSV schema and retains every product datasource field in JSONL,
along with source hashes and field provenance.

```sh
python3 -m tools.scrape_patek --output scraping_runs/patek-personal-research
```

See [the successful run report](reports/patek_research.md) and
[Patek collection instructions](docs/patek.md) for setup, exports, resume and
mapping details. The collector uses sequential requests, robots checks, a local
cache and saved progress. It does not publish data or modify the archival site
automatically.

The Breitling-specific collector uses headless Playwright for the US catalog's
rendered pagination, followed by sequential downloads of each selected watch's
detail page. It exports the same 40 columns and preserves the complete product
fields in JSONL. See [Breitling collection instructions](docs/breitling.md) for
setup, source mappings, resume and snapshot validation.
Its completed run captured all **402 US catalog references**, with USD prices
and all 67 source product fields per watch. See [the run report](reports/breitling_research.md).

```sh
python3 -m tools.scrape_breitling --output scraping_runs/breitling-personal-research
```

The earlier six-brand framework and [initial audit](reports/first_run.md) were
prepared for platform reuse before the research scope was clarified. Its other
brand profiles remain provisional outside the dedicated collectors. [Framework documentation](docs/scraping.md)
describes those separate controls and extension points.

## Import completed catalogs

Run `node tools/import_catalog.cjs patek breitling jlc omega tudor iwc` to import the validated JSONL exports from `scraping_runs/`. This is a separate, repeatable step: reimporting replaces the same source datasets without duplicating references. Archived records and the 73-file inventory remain unchanged. The site retains the shared specifications, additional published technical details, source identities and capture dates. Full source fields and raw cached pages remain in the local research exports.

Validate before publishing with `node tools/validate_catalog.cjs` and `node --test tests/catalog.test.cjs`.

Jaeger-LeCoultre uses the browser collector in [its instructions](docs/jaeger_lecoultre.md). Its completed capture contains **197 references**, including specialist collections and three watch-identified editorial product pages. See [the run report](reports/jaeger_lecoultre_research.md).

Omega uses the isolated [US collector](tools/capture_omega_us.py) and [instructions](docs/omega_us.md). Its **556 references** reconcile exactly with the US watch finder, including three pocket watches. See [the validated run report](reports/omega_us_capture.md).

Tudor and IWC use the validated [India Tudor capture](reports/tudor_in_capture.md) and [US IWC capture](reports/iwc_us_capture.md). Their 441 references are imported into the same searchable catalog and insights. Grouped USD prices are parsed numerically; the 15 unpriced IWC references and undisclosed specifications remain unspecified.

## Rolex and Breguet refresh

The refresh updates 840 exact Rolex references and rebuilds 199 current Breguet references, adding 159 watches while retaining all 1,196 existing IDs. All 1,038 nonempty image URLs in these refreshed records are verified. The 249 unavailable Rolex and 67 unresolved Breguet references remain marked as historical and unverified. Conflicting Breguet archive identities have unreliable details withheld. One current Breguet reference has no image published by its source. Current watches lead each brand’s curated view; searches accept both archived and current reference separators. See the [refresh report](reports/rolex_breguet_refresh.md) and [reproduction instructions](docs/rolex_breguet_refresh.md).
