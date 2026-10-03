# Watch catalog collection

**For the completed Patek-specific personal research workflow, use
[`docs/patek.md`](patek.md).** This page documents the earlier generic framework
for collection and platform reuse; its default grant controls do not govern the
separate Patek personal research script.

The first six targets are Breitling, Patek Philippe, Jaeger-LeCoultre, Omega,
Tudor and IWC. The permission audit on **2 October 2026 (India time)** found no
permission for the intended bulk collection and reuse on Watch Atlas. All six
are disabled by default. The first run collected **zero product records**.

The user explicitly selected “collect only where permitted and record blocked
brands.” Robots allowing a path is not a content license. See
[`reports/first_run.md`](../reports/first_run.md) for the findings and official
sources.

## Run

Python 3.11+ and `lxml` are required. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m watch_atlas_scraper audit
.venv/bin/python -m watch_atlas_scraper crawl --run-dir scraping_runs/current
.venv/bin/python -m unittest discover -s tests -v
```

With the current permission state, `crawl` writes a manifest and an empty,
correctly headed CSV without making product or robots requests. `audit` reads
the checked terms and optional saved robots evidence, with no network requests.

In this Codex workspace the existing bundled Python runtime was used for the
tests and first run; no global Python packages were installed.

## Actual permissions

After receiving permission, record its actual scope in the ignored local file
`permissions.local.json`. The following is an **illustration of the format,
not a permission grant**. Replace every placeholder with the permission evidence
and limits. An unknown, missing, or expired grant never enables collection.

```json
{
  "tudor": {
    "collection": true,
    "reuse": true,
    "evidence": "Location and identifier of the actual written agreement",
    "valid_until": "YYYY-MM-DD",
    "url_prefixes": ["https://www.tudorwatch.com/"]
  }
}
```

`valid_until` is the agreement expiry or the next agreed review date. Collection
and reuse are separate scopes. A research-only collection grant cannot export
data for platform reuse. Permissions are supplied by the operator; the software
cannot authenticate the agreement. Secrets and agreement documents stay local.

```sh
.venv/bin/python -m watch_atlas_scraper crawl \
  --brands tudor --grants permissions.local.json \
  --run-dir scraping_runs/tudor --max-pages 50 --delay 3
```

Every request still passes the robots and host checks. A permission grant does
not override a robots denial or an HTTP access block. For denied hosts, arrange
an approved feed, endpoint or access method with the watchmaker.

## Data and schema

`watches.csv` preserves the 40 columns and their order from the reviewed AP and
Bulgari exports. `watches.jsonl` adds provenance and diagnostics. Its `image_url`
alias matches the existing browser catalog. The software does not rewrite the
archival 1,629-reference site catalog or its analysis fields.

| Group | Existing columns |
| --- | --- |
| Identity | reference_number, watch_URL, type, brand, year_introduced, parent_model, specific_model, nickname, marketing_name, style |
| Commercial | currency, price, image_URL, made_in |
| Case | case_shape, case_material, case_finish, caseback, diameter, between_lugs, lug_to_lug, case_thickness, bezel_material, bezel_color, crystal, water_resistance, weight |
| Dial and strap | dial_color, numerals, bracelet_material, bracelet_color, clasp_type |
| Movement | movement, caliber, power_reserve, frequency, jewels, features |
| Text | short_description, description |

The JSON output additionally contains capture time, source URL/hash, market,
language, field provenance, every captured labeled specification, offers,
image URLs, linked product URLs, missing fields and extraction warnings.
Missing information stays blank. Currency, origin, launch year and movement
type are not inferred from brand or market. Ambiguous multiple offers are kept
without choosing a single price. References remain strings.

Full authorized HTML responses are stored by SHA-256 in local snapshots. That
preserves material which a current mapping does not understand, allowing offline
improvements without requesting the site again. Capturing a response does not
establish complete catalog or specification coverage. Images are linked rather
than downloaded; use of image URLs still requires the relevant permission.

## Architecture and extension

`watch_atlas_scraper/adapters/` has a registry and separate modules for the six
brands. A shared adapter handles Product JSON-LD, explicit HTML specification
labels, and inert embedded JSON. Brand hooks can add selectors, label aliases,
reference rules and documented payload mappings. The generic Patek adapter remains
provisional; the separate `patek_data.py` parser follows the live-observed
WatchFinder/ProductDetail structure and has been exercised on real pages.

**All six product adapters are provisional.** Their path rules and extraction
hooks pass invented fixtures, but none has been validated against a current
product page. Do not mistake the fixture tests for six successful live scrapes.
Once access is granted, validate one watch and one variant from each distinct
product template before enabling a catalog run. Update a brand module when the
official paths, locale or layout change.

Product JSON-LD is accepted only when its URL or explicit SKU matches the current
watch. Related cards and site navigation cannot supply its price or specifications.
Page links and explicit JSON URLs support collection/variant discovery. Only
configured official HTTPS hosts and approved product/listing paths enter the
queue. Sitemap parsing ignores image/video URLs and disables external XML entities.

References are deduplicated by brand, reference, market and language. A missing
reference falls back to source URL, but that record is quarantined until its
identity is resolved. Distinct references and markets remain separate. Explicit
configuration IDs need a brand-specific identity extension if a future site uses
one reference for multiple configurable watches. `linked_product_urls` includes
recommendations as discovery candidates and does not claim they are variants.

To add another maker, subclass `Adapter`, define its official host and path
rules, implement extraction hooks, register it and add a reviewed permission
entry. An unreviewed brand is never implicitly enabled.

## Crawl behavior

- One sequential request stream; at least 3 seconds between request starts on
  a host, increased by applicable `Crawl-delay`.
- Identified WatchAtlasCatalogBot user agent. No browser impersonation, rotating
  proxies, challenge solving, authentication probing or undocumented API discovery.
- Applicable robots groups merge. Wildcards, query rules, longest matching rule
  and Allow ties are supported. Other agents' permissions are never borrowed.
- Permission and robots checks occur before cached or new product responses.
  Robots cache age is at most 24 hours. Unknown/failed rules stop collection.
- Local cache and ETag/Last-Modified revalidation reduce repeated downloads.
- Transient network/5xx failures get at most three attempts. HTTP 401, 403, 451
  and detected challenges stop the host and persist a circuit. HTTP 429 stops
  the current run and records Retry-After; no immediate retry.
- Redirect targets must remain on the configured official hosts and pass scope
  and robots checks. Redirect loops and oversized responses stop fetching.
- SQLite queue and snapshots persist across runs. Only pending URLs resume.
  Failed/disallowed URLs remain visible for investigation rather than repeated
  requests. Run directories should be used by one process at a time.
- The default budget is 50 pages per brand. Queue size and response/decompression
  sizes are bounded. A budget stop reports pending work.

Global sitemap indexes may contain other locales. Product URL classification
filters to the configured locale. A future adapter can specialize map selection
when a site publishes separate locale maps. The budget makes this discovery
bounded; it does not guarantee every nested map will be reached in one run.

## Outputs and offline repair

The run directory contains `state.sqlite`, `snapshots/`, `manifest.json` and:

- `exports/watches.csv`: compatible columns, reuse-authorized valid identities.
- `exports/watches.jsonl`: extended records and provenance.
- `exports/quarantine.json`: identity/validation/reuse failures.
- `exports/quality.json`: row counts and missing-field counts.

Raw runs, snapshots, grants and private documents are ignored by Git. The checked
permission report contains status and hashes, not cookies, secrets or catalog
content. No data is published automatically.

Authorized saved snapshots can be reparsed with no network access:

```sh
.venv/bin/python -m watch_atlas_scraper parse-snapshot \
  --brand tudor --url 'https://www.tudorwatch.com/en/watches/COLLECTION/REFERENCE' \
  --file /absolute/path/to/authorized-page.html \
  --grants permissions.local.json --run-dir scraping_runs/offline
```

The URL must match the adapter's actual product template. An approved data feed
can be integrated through a new adapter/transport after its schema and access
scope are known. No specific feed or API has been obtained in this run.

## Verification

45 offline tests cover default permission gates, separate reuse permission,
scope boundaries, expiry, robots precedence/wildcards, conditional caching,
redirect controls, access-denial circuits, 429 handling, variant isolation,
explicit dimensions, unknown specs, external XML entities, durable resume,
quarantine, all six provisional URL profiles, and a complete synthetic
sitemap-to-export run. All pass. Ten additional Patek tests check the observed
component structure, identity, date filtering, images, preserved raw fields and
case versus movement dimensions. The generic six-brand pipeline remains separate
from the live Patek collection documented in `docs/patek.md`.
