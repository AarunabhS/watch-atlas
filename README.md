# Watch Atlas

A responsive watch research portfolio and catalog for Arunabho Kanti Som.

**[Explore the live dashboard](https://www.arunabhosom.com/watch-atlas/)** · [GitHub Pages URL](https://aarunabhs.github.io/watch-atlas/)

The site contains a watch showcase, searchable catalog, collection insights, project process, data coverage, and a searchable inventory of 73 project files. Data is an archival snapshot from 2023–2024, not a live scrape. The catalog contains 1,629 wristwatch references across five watchmakers.

Collection insights compare six inferred watch segments, average round-case diameter, decorative gemstone mentions, movement families, and distinct calibers. Watchmaker selection updates all comparisons; chart selections open matching catalog references. Filters combine watchmaker, segment, movement family, gemstone detail and text search.

The landing page uses original watchmaker image links in an animated showcase with pause and manual selection controls. The layout adapts to mobile screens and respects reduced-motion preferences. Technical archive information is confined to Project archive.

## Preview locally

Run `python3 -m http.server 4173 --directory dist` and open `http://localhost:4173`.

## Source

- `dist/index.html`: page structure and metadata.
- `dist/styles.css` and `dist/refinement.css`: visual design, responsive layouts and animation.
- `dist/app.js`: navigation, search, filters, detail panels, archive, and optional browser catalog tool.
- `dist/insights.js`: interactive comparisons and methodology notes.
- `dist/data.json`: normalized catalog and archive inventory derived from the preserved project files.

The catalog uses seven prepared source tables. Repeated rows are coalesced by brand and reference, falling back to the source URL when a reference is absent. Later H. Moser source tables enrich earlier ones. Empty fields remain empty. Coverage measures the presence of ten core fields; it does not certify accuracy. Original price currencies and source provenance are retained.

The preserved archive and original project files were not modified. The dashboard includes file metadata and selected watch data. Raw notebooks and private project documents remain outside the published repository.

## Interpreting insights

The primary segment is inferred from captured model names, collection labels and stated functions. Complications take priority, followed by chronographs, diving, travel and jewellery; remaining models fall under time & date. This is an analytical grouping rather than an official watchmaker taxonomy.

Diameter comparisons use 1,590 single diameter measurements. Rectangular dimensions and missing values are excluded. One 430 mm wall clock remains in the project data but is excluded from the wristwatch catalog and comparisons. Miniature wristwatches with valid measurements remain included.

Gemstone mentions describe decorative stones in the captured specifications and descriptions. Sapphire crystals and movement-bearing jewel counts are excluded. A missing mention does not establish that a watch has no gemstones. Movement families use explicit recorded wording; unspecified types stay unspecified. Calibers are normalized and counted separately for each watchmaker.

Some source descriptions differ from their model labels. The comparisons describe the stored snapshot without independently verifying every specification or claiming complete current catalog coverage.

The application runs in the browser, with its prepared catalog bundled in `dist/data.json`. Watchmaker images and web fonts require an internet connection. Local preview is available through the server command above.

## GitHub Pages

GitHub Pages publishes the `dist` directory through `.github/workflows/pages.yml`. Every push to `main` deploys the current dashboard; the workflow can also be run manually from GitHub Actions. No build step, package installation, API keys or backend are required.

The public site includes the prepared catalog and archive inventory. The original notebooks, spreadsheets and private project documents are not bundled in this repository.
