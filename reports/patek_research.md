# Patek Philippe research collection — 2 October 2026

**252 of 252 current watch references collected: 232 wristwatches and 20 pocket
watches.** Every record passed the final source and export integrity checks.

The source is the English [official watch finder](https://www.patek.com/en/collection/watch-finder)
and its linked watch pages. The retrieved finder contains 283 current timepieces;
31 clocks are retained in the inventory and excluded from the watch exports.
Another 21 entries fall outside the selected availability/run-out dates and are
saved separately. This is current-reference coverage for the retrieved inventory,
not a historical archive of every watch Patek has made.

| Finder collection | Watch references |
| --- | ---: |
| Aquanaut | 20 |
| Calatrava | 12 |
| Complications | 32 |
| Cubitus | 6 |
| Golden Ellipse | 6 |
| Gondolo | 8 |
| Grand Complications | 50 |
| Nautilus | 44 |
| Pocket Watches | 5 |
| Rare Handcrafts | 59 |
| Twenty~4 | 10 |
| **Total** | **252** |

## Data

The local run is `scraping_runs/patek-personal-research/`:

- `exports/patek_watches.csv`: all 252 watches in the original 40-column schema.
- `exports/patek_wristwatches.csv`: 232 wristwatches.
- `exports/patek_pocket_watches.csv`: 20 pocket watches.
- `exports/patek_watches.jsonl`: all mapped fields, all **120 original product datasource fields per watch**, original listing fields, asset links, provenance and diagnostics.
- `manifest.json`: coverage, missing-field counts and errors.
- `validation_report.json`: final checks and counts.
- `state.sqlite` and `snapshots/`: saved responses and resumable progress.

Prices, launch years and other unstated values remain blank. Case dimensions,
movement dimensions and measurement labels are preserved separately. Pocket
watch water statements use the pocket-specific field. Images are recorded as
display URLs without downloading image files.

On 134 pages, the base CMS movement parts count differs from the display field.
The exported count follows the display field used by the visible technical panel;
both values are retained in `source_discrepancies` and the original fields. These
are source disagreements, separate from extraction or validation errors.

## Validation

The final checks confirmed exact agreement with the selected catalog references,
252 unique identities, successful official responses, matching SHA-256 source
hashes, preservation of every original product field, image display URLs, pocket
water statements, measurement labels and agreement between the CSV and JSONL.
There were **zero extraction errors and zero record validation errors**. All
**45 offline tests passed**.

The collection recorded 254 HTTP 200 responses: robots, finder and 252 detail
pages. Requests were sequential with a three-second minimum interval. Reprocessing
used the saved pages; it made no additional HTTP requests. The script uses a
declared crawler identity, normal curl connection handling, robots checks,
bounded retries and persistent stop conditions for access blocks or rate limits.

## Reproduce

From the repository root, with Python 3.11+ and `lxml` installed:

```sh
python3 -m tools.scrape_patek --output scraping_runs/patek-personal-research
```

See [`docs/patek.md`](../docs/patek.md) for setup and reprocessing. This run follows
the user's clarified local personal, non-commercial research scope. The research
files stay local and are ignored by Git. No new records have been published or
merged into the archival dashboard.
