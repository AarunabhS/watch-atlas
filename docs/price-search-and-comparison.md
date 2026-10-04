# Reported price search and personal comparison

Implemented on 4 October 2026. The existing GitHub Pages application and its
catalog are preserved. The comparison feature needs no account or backend.
Inline price lookups require the separate worker and a server-side Serper key.
The owner chose Serper + Cloudflare and will connect those accounts.

## User experience

- **Compare watches** is available in the navigation, home page, catalog cards
  and watch details. Shortlist up to six watches. Selections, parameters and
  requirements survive reloads in this browser's local storage.
- Choose from **88 parameters in the current catalog**, including 41 shared
  fields and 47 additional published details. New extra specifications become
  selectable automatically when catalog data changes.
- Combine up to twelve requirements. Numeric conditions support minimum,
  maximum, equality and ranges; textual conditions support contains, equals,
  excludes and recorded-only. All conditions apply together. Use search to
  narrow the matches. Selected watches remain visible when requirements change,
  with a clear indication of whether they still meet those requirements.
- Missing specifications do not meet a condition by default. The optional
  include-unknown setting labels the number of unrecorded requirements. Missing
  gemstone details never imply that a watch has no gemstones.
- Budgets use recorded catalog prices in one explicit currency. INR, USD and
  other currencies are never ranked as interchangeable numbers. Web reports
  remain separate from the original catalog and are not silently used as retail
  prices or budget evidence.
- Select rows, show only differences, hide wholly unrecorded rows, export CSV,
  and copy a link carrying the shortlist, chosen fields and requirements. CSV
  values are escaped and spreadsheet formula prefixes neutralized. Shared links
  contain public watch IDs and the user's chosen criteria; no account is needed.
- At unavailable prices, **Find latest reported price** searches inline when the
  worker URL is configured. Until then, a clearly labeled Google link performs
  the exact-reference search directly. Watches without a usable reference also
  use the direct search. Search country is selectable independently of source
  market; currencies remain those reported by each source.

## Backend and latency

The Cloudflare Worker exposes `GET /v1/price?id=<catalog-id>&country=us`.
`backend/catalog.mjs` is an allowlist of 1,529 eligible identities generated from
the 1,530 watches without numeric prices; one lacks a usable reference. Clients
cannot supply an arbitrary query, brand, reference or upstream URL. The worker
constructs an exact-reference Google query through Serper's search endpoint.

Each uncached request makes **one** search request for ten organic results.
There is no language-model inference or sequential product-page crawl. The
provider request, including JSON consumption, has a **8-second deadline**;
the browser has a **10-second deadline**. These are timeout budgets, not a promise
that every search will succeed within a fixed latency. One live IWC search completed in 5.9 seconds; its cached repeat took 0.5 seconds.
Individual searches can vary and may still time out.

Successful results are fresh for six hours; no-result responses for fifteen
minutes. The Worker Cache API retains found responses for seven days. Stale
results return immediately with their original check time and a visible stale
label while `waitUntil()` refreshes them. This explicitly implements stale
refresh because Cloudflare's Cache API does not honor `stale-while-revalidate`.
The cache key includes watch ID, search country and parser version. Duplicate
in-flight requests share a promise within a worker instance. Cache entries are
local to each Cloudflare location; this is not a globally serialized cache.

The deployed configuration limits uncached lookups to six per IP per minute
and paid provider queries to thirty per minute per Cloudflare location. These
bindings are approximate regional limits, not a global spend cap. Keep the
Serper account's credit/spend controls enabled. CORS allows only the existing
site origins and local preview origins. CORS is a browser access policy, not
authentication; the allowlist and rate limits also restrict paid query abuse.
The API never returns the key, raw provider errors or private watch data.

## What a reported price means

The parser requires the full reference in the result snippet, or in both a
product title and its URL, plus watchmaker evidence, an HTTPS source and one
unambiguous explicit amount. It rejects
unrelated references, obvious accessories/replicas, monthly payments, discounts,
starting prices, ranges and conflicting amounts. Ambiguous dollar signs retain
the original text and **currency unspecified**, rather than being guessed as USD.

Up to three matching sources are shown with amount, currency, source link,
snippet evidence, condition/basis, source date if supplied and lookup timestamp.
Among the results returned by this search, dated sources sort newest first;
undated results retain Google's ordering after dated results. A page's source
date is not necessarily the date its price was set. The app does not claim to
identify the latest price on the entire internet, verify an offer's availability,
or turn a resale report into an official manufacturer price. If Google provides
no safe amount, the user can open the source results directly.

## Connect and deploy the backend

1. Create/connect the [Serper](https://serper.dev/) and Cloudflare accounts.
   Install the official Wrangler CLI using the normal npm package workflow,
   then run `npx wrangler login` in this repository.
2. Rebuild identities after any catalog import:

   ```sh
   node tools/build-price-catalog.cjs
   node --test tests/*.test.cjs tests/*.test.mjs
   ```

3. From `backend/`, deploy the Worker, then upload the key as a worker secret:

   ```sh
   npx wrangler deploy
   npx wrangler secret put SERPER_API_KEY
   ```

   Wrangler prompts for the secret. Never add it to `dist/config.js`, a URL, Git,
   or `wrangler.toml`. The two configured rate-limit namespace IDs must be unique
   to this worker in your Cloudflare account. Remove localhost entries from
   `ALLOWED_ORIGINS` in production if local access is no longer needed.

4. In `dist/config.js`, set `priceApiBase` to the returned HTTPS Worker origin
   (for example, `https://watch-atlas-prices.YOUR-SUBDOMAIN.workers.dev`). Do not
   append `/v1/price`; the app adds the route. Publish the static files through
   the established GitHub Pages workflow.
5. Test one unavailable reference in its detail dialog and in comparison.
   Confirm the result's reference, source, currency and timestamp, then repeat
   to confirm a cached response. Also test another search country, no-result
   handling and temporarily exhausted credits. Rate-limit failures preserve
   the direct Google fallback.

The owner deployed the Worker and uploaded the Serper secret privately.
The frontend is configured for `https://watch-atlas-prices.aksom1711.workers.dev`.
The frontend remains usable without a price API.

## Local preview and verification

Existing frontend preview:

```sh
python3 -m http.server 4173 --directory dist
```

Integrated backend preview without changing public configuration:

```sh
node tools/preview-price-backend.mjs
# Open http://127.0.0.1:8787/#compare
```

This preview injects a localhost-only API origin into the served configuration.
Without `SERPER_API_KEY` in the server environment it returns a clear 503 and a
Google fallback; it never supplies fabricated prices. To exercise real results,
set the secret in your terminal environment and rerun the preview. Local rate
limits and response caches are in memory; production uses Cloudflare bindings.

Automated tests cover unit interpretation, AND requirements, missing data,
currency separation, row differences, additional parameters, CSV safety,
reference matching, amount ambiguity, date ordering/timezones, cache hits,
negative caching, background refresh, concurrent requests, CORS, input validation,
rate limits, provider failures and the provider timeout.

Primary integration references: [Serper](https://serper.dev/),
[Worker Cache API](https://developers.cloudflare.com/workers/runtime-apis/cache/),
[rate-limit bindings](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/),
[Worker secrets](https://developers.cloudflare.com/workers/configuration/secrets/).
