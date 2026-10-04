# Comparison and reported-price implementation

Implemented locally on 4 October 2026; backend connected on 5 October 2026
(Asia/Kolkata). The owner deployed the Cloudflare Worker and privately uploaded
the Serper key. Setup: `docs/price-search-and-comparison.md`.

The catalog still contains 3,477 watches across eleven makers and 73 archive
files. `dist/data.json`, captured prices, original currencies, source datasets
and the collectors were not modified.

## Delivered

- Six-watch shortlists from the catalog, detail dialog and matching-watch list.
- Twelve combined requirements over 88 selectable parameters: 41 shared fields
  and 47 additional published details. Unknown values and currency-specific
  budget conditions are explicit. Ranges are supported; ambiguous measurements
  retain their original wording without becoming numeric evidence.
- Saved browser preferences, difference-only rows, optional empty-row hiding,
  shared comparison links and escaped CSV exports.
- Missing-price controls with an immediate direct Google link in the unconnected
  static site, and inline Google-result lookup when a Worker URL is configured.
- A deployable Worker with a generated 1,529-watch identity allowlist, one
  Serper search per cache miss, a 8-second provider deadline, cache reuse,
  manual stale refresh, duplicate-request coalescing, CORS and rate-limit
  bindings. The browser times out after ten seconds. Found reports include
  provenance, currency, source dates when available and the lookup time.
- Local integrated preview at `http://127.0.0.1:8787/#compare`; it injects a local
  backend URL without editing the production configuration. No invented live
  prices are supplied when the search key is absent.

## Verification

All **44 JavaScript tests passed** (11 existing catalog tests and 33 comparison,
backend and price UI tests). Catalog validation and whitespace checks passed.
Syntax checks passed for the modified and new frontend and backend scripts.

The actual browser was used to verify:

- Diameter requirements and an INR 300,000 budget narrowed the Tudor matches.
- Two selected Tudor references met both requirements; difference-only display
  left their differing recorded prices visible.
- Catalog and detail selections fed the same cross-brand comparison.
- A seventh watch was rejected with a clear six-watch limit message.
- Reload retained the shortlist; a copied share link restored watch IDs and
  parameter selections.
- A local API lookup for unpriced IWC IW345901 returned a clear unconfigured
  status and a working Google fallback link.
- The layout at a 390 px mobile viewport had a 390 px document width; the
  three-watch table scrolled within its own 770 px container.

CSV content, currency retention and formula escaping passed automated checks.
The in-app browser did not expose a download completion event for the CSV,
so a completed browser download was not independently confirmed.

The Google provider was not called with a real key, and production Worker
deployment, real provider latency and live-site activation remain unverified.
The 8-second limit is a timeout budget, not a measured production response time.
Newest means the most recent dated matching source returned by the search;
an undated result is never assigned a fabricated source date.

Screenshots: `watch-comparison-preview.png` and `watch-comparison-mobile.png`
in this reports directory. The existing untracked collector/audit files were
left intact. Publication is tracked in the GitHub Pages deployment workflow.
