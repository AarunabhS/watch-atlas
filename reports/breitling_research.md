# Breitling catalog collection — 2 October 2026

**Captured 402 of 402 distinct watch references in the official US English
all-watches listing, across all nine catalog pages.** Every watch has a published
USD price. There are zero remaining extraction or record-validation errors.

The JSONL preserves all **67 selected product fields per watch: 26,934 source
fields in total**, including fields without a legacy CSV column. Selected
variant fields, structured product data, availability, visible technical tables,
catalog card data, image links and source provenance are also preserved.

## Exports

The local run is in `scraping_runs/breitling-personal-research/`:

- `exports/breitling_watches.csv`: 402 watches using the original 40 columns, in their original order.
- `exports/breitling_watches.jsonl`: complete selected product data, mapped fields and diagnostics.
- `inventory.json`, `listing_pages.json` and `rendered_pages/manifest.json`: the full discovered reference set and pagination evidence.
- `manifest.json`: coverage, collections, prices, errors and per-column missing counts.
- `validation.json`: the successful offline comparison with every source snapshot.
- `state.sqlite`, `snapshots/` and `rendered_pages/`: durable records, original HTTP responses and rendered catalog snapshots, with SHA-256 hashes.

The data remains local for the requested personal, non-commercial research.
These run files are ignored by Git. Collection does not publish them or modify
the existing archival dashboard.

## Collections

| Collection | References |
| --- | ---: |
| Avenger | 20 |
| Chronomat | 167 |
| Classic AVI | 17 |
| Navitimer | 54 |
| Premier | 28 |
| Professional | 56 |
| Superocean | 23 |
| Superocean Heritage | 19 |
| Top Time | 18 |
| **Total** | **402** |

These are distinct listed references, including team editions and listed strap
variants. Coverage refers to this US catalog snapshot. Historical watches,
other markets and related reference numbers without a published catalog card
are not counted as additional watches.

## Site-specific extraction

The downloaded HTML for later catalog page numbers repeated page-one results.
An isolated headless Playwright browser followed the site's actual pagination
and saved the rendered product cards instead. Detail pages were then downloaded
sequentially and parsed from their public `__NEXT_DATA__` selected variant,
without borrowing values from related watches.

All 402 products have a source-unit conflict in at least one dimension: the CMS
uses a centimeter label while the technical panel displays millimeters. The
CSV uses the panel's measurements; JSONL preserves both representations and
records the discrepancy. Product weight and watch-head weight remain separate.

Positive prices use the selected variant's gross amount and currency. The
published US label excludes sales tax. Introduction years use each reference's
explicit launch date. Limited-edition flags retain **112 true and 290 false**
values. Functional bezel wording is preserved as a description, and the source
label “Metal bracelet” is retained without treating it as a color.

All watches have reference, source URL, model, case material, diameter, movement,
water resistance, dial color, image link and weight values. **86 watches have no
published power-reserve value**; those entries remain blank. Other blanks reflect
missing source values or no direct mapping to a legacy column. The full raw data
and per-row missing-field lists allow those decisions to be reviewed.

## Validation and request behavior

**54 automated tests passed.** Synthetic fixtures cover source identity, selected
variant prices, readable translations, dimension units, weights, booleans,
stale server pagination and incomplete browser discovery. Twelve offline browser
robots checks agreed with the shared Python parser, including rejection of a
disallowed query route.

The completed-run validator checked all nine rendered listing snapshots and all
402 detail snapshots. It confirmed the exact reference set, SHA-256 integrity,
all product and variant fields, structured data, field provenance, reproducible
mappings and exact CSV/JSONL agreement. It used zero network requests and reported
zero errors.

The collector declares its identity, checks applicable robots rules and paces
requests at least three seconds apart, with a local response cache and durable
resume. The main pass had one timed-out detail page; a subsequent resume captured
it successfully. All 405 HTTP responses recorded by the collector returned 200;
three timeout attempts remain in the request history. No access blocks or rate
limits were encountered. Image URLs were saved without downloading images.

## Reproduce

See [setup and collection instructions](../docs/breitling.md). From the repository
root, after installing its documented dependencies:

```sh
python3 -m tools.scrape_breitling --output scraping_runs/breitling-personal-research
python3 -m tools.validate_breitling --output scraping_runs/breitling-personal-research
```

Use `--reparse` to improve mappings from fresh cached pages. The dedicated parser
is `watch_atlas_scraper/breitling_data.py`; browser discovery and the runner are
separate modules sharing the existing transport, cache, schema and export code.

Source: [official Breitling US all-watches catalog](https://www.breitling.com/us-en/watches/all/).
