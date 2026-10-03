# Jaeger-LeCoultre collection

This collector follows the published US watch cards and visits one watch page at a time in a normal headless Chrome browser. It exports the project's exact 40-column CSV schema and JSONL with all selected product metadata, technical specifications, movement tables, both Reverso faces, listing details, source hashes and field provenance. Raw browser snapshots stay local in the ignored run directory.

```sh
python3 -m tools.scrape_jlc --output scraping_runs/jlc-personal-research \
  --node /path/to/node --playwright-path /path/to/playwright \
  --chrome /path/to/chrome
python3 -m tools.validate_jlc --output scraping_runs/jlc-personal-research
```

Python 3.11+, `lxml`, Node, Playwright and Chrome are required. Executable paths are optional when available in the normal environment. Use `--limit 3` for a pilot. Rerunning resumes cached pages; `--offline` rebuilds both exports from saved snapshots without network requests. An incomplete pilot reports incomplete coverage.

The collector checks browser-fetched robots rules and evaluates them before each main navigation, including redirects. Requests use one page with at least three seconds between navigation starts. Images, media and fonts are skipped during extraction. Account, checkout, search and appointment flows are outside the queue. Access denials and human-verification pages stop collection. There is no proxy rotation, stealth mode or challenge bypass.

The initial HTTP requests were denied, while ordinary headless-browser visits returned the public pages successfully. The collector therefore uses the browser's actual page DOM.

## Discovery and mapping

The all-watches listing declares 186 cards. One links to an editorial URL; its selected-watch tracking metadata and explicit watch-image captions identify Q6202420. Three Calibre 101 and six additional Hybris watches occur in the specialist catalogs but not the all-watches listing. Two further Hybris editorial product pages identify Q5252470 and Q52624A3. The complete capture contains **197 watch references**. Discovery merges all-watches, Calibre 101, high-complication and Hybris cards, validating each published count. The Atmos clock in Hybris is recorded as an exclusion. Product URLs come from published links; references are never generated.

Standard watch pages expose technical accordions, selected Product JSON-LD and selected-watch tracking metadata. Request-only models sometimes omit Product JSON-LD; their explicit reference, title and canonical URL still establish identity. Some high-complication pages use a narrative template: its selected metadata, listing dimensions, calibre block and watch-specific narrative are retained. Unpublished values stay blank.

Case thickness and movement thickness are separate. Reverso L × W dimensions are preserved rather than treated as a round diameter. Decimal commas are normalized in measurements. Both Recto and Verso dials and functions are retained. Separate calibre blocks occasionally disagree with the technical accordion; both values and the discrepancies remain in JSONL, with the technical accordion used for shared fields.

The offline validator reparses every listing and watch snapshot, verifies SHA-256 hashes, reconciles the complete reference set and checks every CSV field against JSONL and source data. It does not request private APIs or infer missing specifications from another reference.
