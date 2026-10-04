# Universal Watch Search and Advanced Watch Finder

Implemented on `codex/universal-watch-finder`, based on the published Rolex/Breguet refresh. The catalog retains all 3,636 watch IDs, historical records, source markets and original scraped specifications. No new catalog data was scraped or invented.

## Run the complete local application

Requires Node 24 or newer (built-in SQLite; no packages or search-provider key required):

```sh
node tools/build-finder-catalog.mjs
ATLAS_PREVIEW_PORT=8791 node tools/preview-price-backend.mjs
```

Open `http://127.0.0.1:8791/#finder`. A plain static HTTP server can still preview the other existing surfaces, but the Finder needs its database API. The preview serves the existing price API alongside the Finder; paid price lookup remains opt-in and separate.

## Architecture

- `dist/finder-model.js`: shared declarative facet vocabulary, aliases, conservative normalization, typed URL state and deterministic parsing. Identity terms come from catalog metadata. The parser accepts general currency, unit, comparison and range expressions and can be replaced without changing the query API or filter UI.
- `backend/migrations/0001_watch_finder.sql`: normalized derived watch projection, extensible facet relation, source/currency-aware prices, exact-reference indexes, numeric indexes and FTS5. Stable IDs, full original records and separate lightweight cards are retained.
- `tools/build-finder-catalog.mjs`: builds a local SQLite index, a reproducible D1 import at `.finder/catalog.sql`, and `dist/bootstrap.json`. The existing official importer and Rolex/Breguet refresh rebuild this projection automatically. Raw catalogs and exports are unchanged. The local derived database is disposable and can be rebuilt.
- `backend/finder-service.mjs`: GET-only, parameterized search, suggestions, metadata, bounded watch hydration and existing comparison-requirement queries. Queries combine independent groups with AND; values within a group use OR. Complications explicitly offer ALL or ANY, with ALL the default.
- `backend/worker.mjs`: extends the existing Cloudflare price worker. `WATCHES_D1` supplies the same SQL implementation in production. The local preview uses a D1-compatible SQLite adapter.
- `dist/finder.js` / `finder.css`: universal autocomplete, Finder cards, filter sections, exact numeric controls and diameter sliders, mobile draft/apply sheet, interpreted chips, sorting, empty-state relaxations and sharing.
- `dist/comparison.js`: retains the same saved shortlist key, CSV, comparison links, rules and 117 parameters. Shortlisted records are cached (maximum six), selected IDs survive partial bootstrap loading, and comparison candidate queries use the API. Finder browsing retains one result page plus selected records; comparison candidates are capped at 96 and the browser record cache at 110.

Overview, Finder and comparison load an approximately 84 KB bootstrap rather than the 12.7 MB full catalog. Legacy catalog/coverage/insights are retained and load their original bundle only when visited. They are compatibility surfaces; the new search and comparison flow does not require that bundle.

## Queries and URLs

Examples:

```text
#finder?q=126710BLRO&brand=Rolex
#finder?material=Titanium&movement=Automatic&complication=GMT&price.lt=20000&diameter.lt=41&water.min=100
#finder?material=Ceramic&material=Titanium&diameter.min=36&diameter.max=40
```

The route uses the existing hash navigation so GitHub Pages needs no rewrite rules. Query submission converts recognized terms into visible URL-backed filters. Unrecognized words remain a literal full-text query. Numeric minimum/maximum inputs are inclusive; natural “under / below” uses strict `.lt`, and “above” uses `.gt`. Currency remains explicit and is never converted. Filters, paging and sorting are canonical and bookmarkable; back/forward restores them.

Exact references rank before reference prefixes, exact models/collections, and weighted FTS relevance. The FTS candidate set and scores are materialized once per query. No fuzzy fallback introduces unrelated watches. Keyboard autocomplete supports arrows, Enter, Escape and Cmd/Ctrl K; suggestions include brand-specific collections, references and structured searches. Three editorial starting queries are UI examples, not parser logic.

Zero-result responses keep the active requirements and calculate up to three suggestions for removing a single requirement. They never silently widen a search. Page responses contain at most 24 records; watch hydration accepts at most six IDs. Numeric sort places unknown values last. “Latest catalog capture” means capture date, not a fabricated release/added date.

## Data boundaries

- Missing material, movement, price, dimensions, complication evidence and water rating remain unknown. A numeric or positive attribute constraint requires a documented matching value. Unknown is never zero or a negative fact.
- Explicitly negated source attributes, such as Tudor “No date”, do not become positive complication facets.
- Case dimensions accept a single explicit mm value. Multiple dimensions, ranges, diagonal measurements and pocket-watch diameters are excluded from diameter filtering. Case, movement and strap measurements are kept separate.
- Power reserve must be a single hours value; battery duration is not reserve. Hz and stated vibrations per hour normalize to Hz; ambiguous frequencies remain unknown.
- Material and complication facets use structured source fields and model names, not broad marketing text. Full-text search can search model descriptions; it cannot manufacture structured attributes.
- Dial normalization excludes hands, appliques, markers, subdials and bezel descriptions. Composite/reverse dials may remain sparse; original dial wording remains in details.
- Manufacture movement is populated only by explicit evidence. Absence of a manufacture label is unknown, not “No”.
- Styles use explicit source labels. The current catalog contains Classic and Sports labels but does not establish Dress for most references. A dress constraint can legitimately return zero; remove it to explore dimensions and movement independently. “Thin” is subjective and prompts a thickness limit.
- Production and live stock availability are not inferred from capture dates. Official / archive / historical catalog status describes provenance. Known source production values are supported, but the current dataset has none.
- Prices are separated into `official_retail` and `recorded_catalog`. A budget applies only to the chosen source and currency. Future market sources can add price rows and metadata options without changing the filter model.
- AP, JLC, VC and Patek aliases are declarative. Speedy expands to Speedmaster. Pepsi uses Rolex GMT source bezel evidence or the documented BLRO reference suffix (a product-code rule, not a list of selected references). Panda requires an explicit panda mention; contrasting subdials are not guessed.
- Unsupported negation is searched literally and explained. Mixed natural-language OR remains conservative; use the explicit filter selections and complication mode.

## Production activation

The production backend was activated on 5 October 2026. `watch-atlas-catalog` contains 3,636 watches and 3,636 FTS entries, and the existing worker is deployed with `WATCHES_D1` at version `d43be1c4-f828-407f-bab5-f4011139e4b1`. Metadata, exact reference, Pepsi nickname, descriptive constraints, autocomplete, empty-state alternatives and website CORS checks passed against the live API. The existing price endpoint's CORS preflight also passed without a paid lookup. The frontend awaits publication from `main`.

The binding is saved in `backend/wrangler.toml`. For a fresh installation or replacement staging catalog, use the existing Cloudflare account and price worker. Create a dedicated D1 catalog database, then add its actual returned ID to the config:

```toml
[[d1_databases]]
binding = "WATCHES_D1"
database_name = "watch-atlas-catalog"
database_id = "ACTUAL_ID_RETURNED_BY_CLOUDFLARE"
migrations_dir = "migrations"
```

Build and import the projection before publishing the frontend:

```sh
node tools/build-finder-catalog.mjs
wrangler d1 create watch-atlas-catalog --config backend/wrangler.toml
# Add the returned binding to the config before executing the import.
wrangler d1 execute watch-atlas-catalog --remote --file .finder/catalog.sql --config backend/wrangler.toml
wrangler deploy --config backend/wrangler.toml
```

The existing `dist/config.js` sets Finder and price API bases to the existing worker URL. Keep the Serper secret and existing limiters/origins on that worker. Verify `/v1/finder/meta` and representative `/v1/finder/search` requests from the public origin, then publish the static assets through the existing Pages workflow.

The generated SQL is a complete snapshot import, not an incremental ingestion API. For catalog replacements, import into a fresh staging D1 database, verify counts/queries, then switch the binding and deploy the worker; preserve the old database for rollback. Do not rebuild a database currently serving traffic in place. The metadata cache expires after 30 seconds. New ingestion should emit normalized facts with source provenance and reuse this projection, or apply versioned incremental updates; an external search index can later replace FTS behind the same API.

Cloudflare documents [D1 FTS5 support](https://developers.cloudflare.com/d1/sql-api/sql-statements/), [imports](https://developers.cloudflare.com/d1/best-practices/import-export-data/) and [the database binding](https://developers.cloudflare.com/d1/worker-api/d1-database/). Production network latency and D1 costs require validation after activation; local timings are not a production SLA. Pagination uses bounded stable offsets; a cursor can replace it behind the API if deep-page volume grows.

## Validation

```sh
node --test tests/*.test.cjs tests/*.test.mjs
node tools/validate_catalog.cjs
node tools/benchmark-finder.mjs
```

SQL integration tests cover actual catalog queries, exact ranking, blank-reference rejection, OR/AND constraints, strict boundaries, different currencies/sources, unknowns, explicit absence, source ambiguity, every sort, pagination, suggestions, empty-state relaxations, URL round trips and existing comparison operators. Workspace tests exercise persistent shortlists across partial reloads and result pages, six-watch limits and removal of unavailable IDs. Autocomplete tests cover late-response dismissal and keyboard entity selection. Browser checks cover desktop suggestions and cards, 390 px mobile layout, mobile Apply, active-chip removal, back-button restoration, reload persistence, details and the existing comparison table. See `reports/universal-watch-finder.md` and `reports/finder-benchmark.json` for measured results and limitations.
