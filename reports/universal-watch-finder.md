# Universal Watch Search / Advanced Watch Finder validation

Validated locally on 5 October 2026 in `codex/universal-watch-finder`, based on the published Rolex/Breguet refresh (`83abbd1`). The complete preview is running at `http://127.0.0.1:8791/#finder`.

## Delivery

Universal keyboard/touch autocomplete, entity ranking and aliases, natural-language constraint parsing, URL-backed advanced filters, 24-watch server-paginated results, sorting, measured empty-state relaxations, mobile draft/Apply/Clear controls, and the existing persistent six-watch comparison workspace are implemented together. The price worker and catalog import/refresh tools are extended rather than replaced.

Search uses a normalized SQLite/D1 projection with numeric indexes, relational facets, separate price source/currency facts and FTS5. Raw source records and all stable IDs remain unchanged. Overview, Finder and comparison begin with an 83,427-byte bootstrap; legacy catalog/coverage/insights retain their original 12.7 MB bundle, loaded when visited. Finder does not download the entire catalog. Detail and comparison record caches are bounded; comparison retains its CSV, shared links, requirements and 117 parameters.

## Representative catalog queries

These counts describe this catalog snapshot and the default official retail / USD source when a budget is present.

| Query | Results |
| --- | ---: |
| Rolex Pepsi | 4 |
| Rolex 126710BLRO | 2 |
| 5711 | 4 |
| JLC Reverso green | 8 |
| Omega Speedmaster Snoopy | 1 |
| Patek perpetual calendar | 33 |
| Speedy | 98 |
| AP 15500 blue | 0 — reference absent from this catalog |
| VC Overseas | 0 — watchmaker absent from this catalog |
| automatic GMT under $15,000 | 52 |
| titanium watches under 40mm | 2 |
| chronograph with 70 hour power reserve | 266 |
| sports watch 100m water resistance under 41mm | 104 |
| manual winding tourbillon rose gold | 20 |
| thin manual-winding dress watches under $20k | 0 — no documented Dress facet; removing style yields 74 |
| automatic titanium GMT under 41mm, at least 100m, below $20,000 | 0 — all six constraints preserved |

The last query exposes movement, material, GMT, strict diameter/price limits and minimum water rating as visible chips. Removing only material yields 40 matches; removing GMT yields 2; removing price yields 1. These alternatives are counted by the database and require a user action. Nothing is widened silently. “Thin” prompts an explicit thickness limit.

## Data coverage and missing values

| Documented normalized attribute | Watches |
| --- | ---: |
| Case diameter eligible for wristwatch comparison | 3,366 |
| Case thickness | 2,219 |
| Lug to lug | 645 |
| Case material | 3,524 |
| Dial color / finish facet | 2,692 |
| Movement type | 3,551 |
| Calibre | 3,481 |
| Explicit manufacture movement evidence | 295 |
| Power reserve in hours | 3,233 |
| Frequency | 1,566 |
| Jewels | 1,328 |
| Positive complication evidence | 2,656 |
| Water resistance | 3,544 |
| Strap / bracelet material | 3,146 |
| Explicit style label | 216 |
| Production status | 0 |

There are 1,285 USD and 216 INR official retail snapshots, plus 244 USD and 74 CHF archive prices. Budgets never convert or mix them. Additional price sources can use the same URL/API model, and search returns the selected price fact separately from the unchanged original catalog price.

Ambiguous multi-dimension/diagonal/pocket measurements, ranges, battery durations and missing values remain unknown. Manufacture, dress style, production and live stock are not guessed. Explicit “No date” Tudor records do not become positive Date facets. Dial colors are not taken from hands, markers, counters or case metal. Unsupported query negation is explained and searched literally.

## Automated and browser checks

- 84 JavaScript tests pass, including 24 Finder SQL/parser/normalization integration cases, 3 persistent comparison cases, 2 autocomplete interaction cases, and existing catalog, comparison, price and refresh coverage. Four tests belong to the concurrent image viewer work; those changes were preserved.
- All 107 existing Python scraper tests pass with the bundled Python runtime. The system Python lacks `lxml`; no packages were installed or scraper code changed to work around that environment difference.
- Catalog validation confirms 3,636 watches, 11 watchmakers and 73 archived files.
- Syntax checks and `git diff --check` pass.
- Filter tests cover same-group OR, cross-group AND, ALL/ANY complications, strict/inclusive bounds, unknown values, currencies/sources, all sorts, stable pages, exact ranking, shareable URL round trips, empty-state alternatives, hydration limits and existing comparison operators.
- Autocomplete tests cover a late response after dismissal and ArrowDown/Enter entity selection. Browser checks confirm grouped suggestions and touch/keyboard submission.
- Desktop was checked at 1,440 × 900: sidebar, active chips, result cards, numeric/price sorting and the shared tray. No horizontal page overflow.
- Mobile was checked at 390 × 844: sidebar is replaced by a modal filter sheet, count feedback follows the draft, Apply updates the URL/results, Clear/Cancel preserves the applied state, and back navigation restores removed filters. Adding an inclusive 41 mm maximum to the 52-match automatic GMT budget search yields 43 references. Page width and scroll width both remain 390 px.
- Two shortlisted references survive a reload, a different result query, sorting and navigation to the existing comparison table. Removal works in the mobile tray, including unavailable stored IDs. Full original details hydrate on demand. Final browser error log is empty.
- Temporary viewport overrides were reset; the preview tab remains available.

Visual evidence: [desktop overview](finder-screenshots/desktop-overview.jpg), [desktop cards and filters](finder-screenshots/desktop-results.jpg), [mobile filter sheet](finder-screenshots/mobile-filters.jpg), [mobile results](finder-screenshots/mobile-results.jpg).

## Scale check

`node tools/benchmark-finder.mjs` builds 100,000 synthetic records from small real catalog projections with facets, prices and FTS. Each timing includes a count and 24-result query; eight iterations are measured. The text candidate set / BM25 scores are materialized once per query.

| Scenario | Matches | Median | Maximum |
| --- | ---: | ---: | ---: |
| Catalog page | 100,000 | 91.0 ms | 100.0 ms |
| Broad reference prefix | 33,340 | 224.7 ms | 229.9 ms |
| Combined material, movement, complication and diameter filters | 25,005 | 183.7 ms | 196.1 ms |
| Numeric sorting | 100,000 | 83.6 ms | 102.1 ms |

Full measurements are in [finder-benchmark.json](finder-benchmark.json). These are synthetic in-memory local SQLite measurements, not production D1/network latency or a service-level guarantee. Production latency and database costs need measurement after activation. Deep pagination uses stable bounded offsets; the API can later adopt cursors or another search index.

## Activation and remaining limits

**Production backend activated on 5 October 2026; frontend publication pending.** The catalog was imported into `watch-atlas-catalog` (`df288d98-0322-4b66-985a-d4e564e17fba`) and the existing worker deployed with `WATCHES_D1`, version `d43be1c4-f828-407f-bab5-f4011139e4b1`. Remote counts confirm 3,636 watch records and 3,636 FTS entries. `.finder/catalog.sql` and `.finder/catalog.sqlite` are generated locally and ignored by Git. The largest current import statement is approximately 22 KB.

Live API checks from the website origin passed: metadata 3,636; `Rolex 126710BLRO` 2; `Rolex Pepsi` 4; `automatic GMT under $15,000` 52; the six-constraint titanium query 0 with the same 40/2/1 relaxations; and relevant JLC Reverso autocomplete collections/references. All responses returned HTTP 200 and the expected website CORS header. Observed request times ranged from 380 to 1,228 ms including network latency; this small functional check is not a load test. The existing price API preflight returned HTTP 204 without initiating a paid lookup.

Follow [the architecture and activation guide](../docs/universal-watch-finder.md). Import a new staging database, verify representative queries, bind/deploy the existing worker, then publish the frontend. Preserve the old database for rollback. Existing price credentials, origin restrictions and rate limits remain in place.

This first version uses an extensible deterministic parser, not an AI service. It deliberately leaves unsupported negation/mixed natural-language OR and subjective descriptions visible or explained. There is no invented availability or production data, no fuzzy fallback noise and no fabricated watch recommendations. Styles and nicknames depend on source evidence. These boundaries are foundations for future concierge, semantic, market-price and similarity providers behind the same API.
