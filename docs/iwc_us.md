# IWC US catalogue capture

This dedicated collector uses the current public catalogue at
`https://www.iwc.com/us-en/watches`. It follows the product URLs published there;
it does not generate references or use account, checkout or private API routes.
The current site redirects the old `/us/en/watches.html` address to this route.

The October 2026 capture used one normal Codex in-app browser tab. Plain HTTP
returned 403; the normal browser displayed the catalogue and selected product
pages without a challenge. Navigations were sequential, at least three seconds
apart. Direct HTTP was not retried with spoofed identities, proxies or stealth.

## Catalogue and specifications

All references are present in the public catalogue DOM, including cards initially
hidden behind Show more. The parser reconciles card counts with each displayed
collection count and rejects duplicate or inconsistent references. Discovery
does not need search filters or generated pagination requests.

The product page publishes a complete `noscript` specification table for its
Overview, Features, Case and Movement tabs. The saved DOM preserves this table
even though the interactive UI initially mounts only the Overview panel.
The selected canonical URL, specification reference and Product JSON-LD (when
present) must agree. Some unpriced specialist watches omit Product JSON-LD;
their explicit specification reference and canonical URL establish identity.

The CSV uses the existing 40-column Watch Atlas schema. Case / Strap width maps
to `between_lugs`; Buckle width remains in the raw table and does not supply
lug-to-lug length. Case / Height maps to thickness. Movement supplies calibre,
power reserve, original frequency wording and jewel count. Features preserve
the full disclosed list, including sapphire-glass specifications.

Selected visible US prices are compared with both the catalogue card and its
Product offer when present. Unpriced enquiry-only references remain blank.
The price is suggested US retail and the page states VAT excluded where shown.

JSONL retains all four complete technical sections, selected structured data,
original catalogue attributes and tracking fields, the full strap description,
product introductions, editorial copy, selected gallery links, related product
URLs, source hashes and field provenance. Strap material/colour columns use
explicit words in the strap specification. Unstated release years, dimensions,
finishes and other optional fields remain blank. Publication timestamps in
catalogue attributes are not treated as introduction dates.

## Export and audit saved pages

With the repository's Python dependencies (`lxml`) available:

```sh
python3 -m tools.capture_iwc_us --output scraping_runs/iwc-us-capture
python3 -m tools.validate_iwc_us --output scraping_runs/iwc-us-capture
python3 -m unittest discover -s tests -p test_iwc_us.py
```

The exporter can run during a partial capture and reports incomplete coverage
until all selected product pages exist. It produces `exports/iwc_watches.csv`,
`exports/iwc_watches.jsonl`, `inventory.json`, `listing_pages.json`, `manifest.json`
and `state.sqlite`. The browser stores `browser_cache.json` and content-addressed
HTML under `snapshots/`. The audit produces `validation_report.json`, verifies
every saved hash, checks every CSV field against JSONL and a fresh parse, and
independently checks technical cells, reference identity and selected prices.

## Reusable normal-browser collector

`tools/capture_iwc_browser.mjs` can launch an ordinary Chrome browser or attach
to an explicitly supplied local CDP endpoint. It creates and closes its own tab.
Provide current reviewed robots rules compiled by the shared
`watch_atlas_scraper.robots.Robots` parser; each rule needs `specificity`, `allow`
and `pattern`. The capture's `robots_web.txt` records the official robots text
retrieved through the web research tool; the separately saved direct HTTP
response records its 403. `robots_rules.json` identifies that distinction.
Robots permit the catalogue/product paths used by this capture.

```sh
node tools/capture_iwc_browser.mjs \
  --output scraping_runs/iwc-us-capture \
  --robots scraping_runs/iwc-us-capture/robots_rules.json \
  --chrome '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --delay 3
```

Options include `--playwright /absolute/path/to/playwright`, `--cdp
http://127.0.0.1:PORT`, `--headless true`, `--limit 5` for a pilot and `--refresh
true`. Browser cache expires after 24 hours; offline rebuilding has no network
requests or expiry. A blocked separate browser session is an access limitation;
the successful normal-browser sources can still be processed offline.

Use a new output directory for a separate dated capture. This workflow saves
local research files; it does not import or publish them to the dashboard.
