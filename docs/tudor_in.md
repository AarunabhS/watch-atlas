# Tudor India catalogue capture

This collector follows the English Tudor catalogue at `https://www.tudorwatch.com/en/watches`, its published pagination links, and the watch references embedded in those pages. It is specific to Tudor. It uses one ordinary browser page, spaces navigation starts by at least three seconds, resumes from saved snapshots, and stops at access blocks or inconsistent data.

The successful October 2026 capture used Codex's normal in-app browser. Plain HTTP and a separate headless Chrome session returned HTTP 403; the normal in-app browser displayed the catalogue and INR prices without a challenge. No proxy, stealth options, CAPTCHA handling or reference guessing were used.

## Sources and mapping

Tudor embeds public JSON in a DOM script beginning `window[Symbol.for("InstantSearchInitialResults")] =`. Parse its JSON text; do not execute the script or inspect private runtime state. The five pages contain 48, 48, 48, 48 and 24 entries. The source includes full technical specifications and the India price even when a promotional tile replaces a conventional clickable card.

Every selected product page is saved as a content-addressed rendered DOM snapshot. Product reference, INR price, and all technical fields must agree with the catalogue. The original catalogue hit, selected Product JSON-LD, technical wording, editorial paragraphs, related reference IDs and source hashes are retained in JSONL.

The export uses the existing 40-column Watch Atlas schema. The full displayed `M…-0001` reference is preserved. Two Pelagos models have a different display code and URL code; neither identifier is discarded. Special editions can redirect to `/en/watch-family/daring-watches/…`; the final official product URL is retained, alongside the original catalogue URL.

Tudor's internal `lugToLugSpec` is visibly labelled **lug width**. Map it to `between_lugs`. Populate `lug_to_lug` only from an explicit length in the Case text, such as the Pelagos FXD's 52 mm measurement. The separate displayed case-thickness value takes precedence over a more precise value appearing inside a Case paragraph; both source values remain in the raw specifications.

Undisclosed fields remain blank. Catalogue creation timestamps are not release dates. Strap material excludes a different metal used only in the buckle. Editorial copy can describe the watch family and is retained as published; it does not supply a guessed variant-specific dial or bracelet colour. Prices are Tudor suggested retail prices, not availability guarantees.

## Rebuild and audit without network

From the repository root, with its Python dependencies installed:

```sh
PYTHONPATH=. python3 tools/capture_tudor_in.py --output scraping_runs/tudor-in-capture
PYTHONPATH=. python3 tools/validate_tudor_in.py --output scraping_runs/tudor-in-capture
python3 -m unittest tests.test_tudor_in
```

Outputs are `exports/tudor_watches.csv`, `exports/tudor_watches.jsonl`, `manifest.json`, `inventory.json`, `listing_pages.json`, `validation_report.json`, `state.sqlite`, `browser_cache.json` and SHA-256 source files under `snapshots/`.

## Capture in a normal browser

`tools/capture_tudor_browser.mjs` uses Playwright with ordinary browser settings. It can launch Chrome headed or connect to a user-supplied local browser debugging endpoint. The collector creates and closes its own tab. A 403 in a separate browser session is a concrete access limitation; the successful capture's normal-browser snapshots can still be processed offline.

First fetch Tudor's current `robots.txt` and compile it with the shared `watch_atlas_scraper.robots.Robots` parser. The rules file must contain a `rules` array with `specificity`, `allow` and `pattern` for each selected rule. The capture directory contains the robots file and rules used for this run.

```sh
node tools/capture_tudor_browser.mjs \
  --output scraping_runs/tudor-in-capture \
  --robots scraping_runs/tudor-in-capture/robots_rules.json \
  --chrome '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --delay 3
```

Options include `--playwright /absolute/path/to/playwright`, `--cdp http://127.0.0.1:PORT`, `--headless true`, and `--refresh true`. Cache entries expire after 24 hours unless rebuilding with the offline Python script. Use a new output directory for a separate dated capture. The parser refuses another country's prices; choose India through the normal website before capturing in a connected browser.
