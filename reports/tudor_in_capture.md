# Tudor catalogue capture — 4 October 2026

Complete: **216 / 216 distinct wristwatch references** from the [official English Tudor catalogue](https://www.tudorwatch.com/en/watches), rendered for the India price market. All 216 references have published INR suggested retail prices. This is the current catalogue snapshot, not a historical archive or an availability guarantee.

## Deliverables

- CSV: `scraping_runs/tudor-in-capture/exports/tudor_watches.csv` — the shared 40-column Watch Atlas format.
- JSONL: `scraping_runs/tudor-in-capture/exports/tudor_watches.jsonl` — fields plus complete catalogue hits, raw technical specifications, descriptions, selected gallery image URLs, JSON-LD and provenance.
- Reusable collector: `tools/capture_tudor_browser.mjs`; parser/exporter: `tools/capture_tudor_in.py`; audit: `tools/validate_tudor_in.py`.
- Reproduction and mapping notes: `docs/tudor_in.md`.

## Validation

- Five catalogue pages: 48 + 48 + 48 + 48 + 24 = 216 entries, with no duplicate references.
- All 216 selected product pages captured, including five special-edition campaign redirects.
- All 221 referenced snapshots verified by SHA-256.
- Every product reference, technical specification set and visible INR price checked against the catalogue.
- Exact agreement between CSV, JSONL and a fresh parse of the saved sources.
- All ten core fields populated for every record; no record validation errors.
- 92 repository tests passed; the browser collector passes its JavaScript syntax check.

## Coverage by published catalogue family

| Family | References |
|---|---:|
| 1926 | 46 |
| Black Bay | 8 |
| Black Bay 54 | 4 |
| Black Bay 58 | 14 |
| Black Bay 68 | 2 |
| Black Bay Bronze | 2 |
| Black Bay Chrono | 11 |
| Black Bay GMT | 7 |
| Black Bay One | 57 |
| Black Bay Pro | 6 |
| Clair de Rose | 12 |
| Daring Watches | 5 |
| Pelagos | 5 |
| Pelagos FXD | 4 |
| Ranger | 8 |
| TUDOR Monarch | 1 |
| TUDOR Northflag | 1 |
| TUDOR Royal | 23 |

## Source details and limits

The successful capture used one normal in-app browser tab and sequential product navigations at least three seconds apart. Plain HTTP and a separate ordinary headless Chrome session returned HTTP 403. No proxies, stealth options, challenge solving or reference guessing were used. Tudor’s robots file permits the catalogue/product paths used here; the robots file and compiled rules are saved with the run.

The JSONL retains all ten labelled technical sections for each watch, the original public catalogue data, product editorial copy and current-watch image links. Related watches remain separate. Precise dial colours come from the selected Dial specification rather than the broader catalogue colour facet.

Tudor’s internal lugToLugSpec key is labelled lug width on the visible product page: it maps to between_lugs. Two watches also explicitly disclose a 52 mm lug-to-lug length. The case-thickness column uses the separately displayed thickness value, while more precise wording inside the Case text remains in raw specifications. Two Pelagos models use a display reference different from their URL code; both are preserved.

Introduction year, nickname, case shape, weight, movement frequency and jewel count remain blank because these pages do not explicitly disclose them. Other optional fields are populated only where stated. Case/strap materials and finishes are normalizations of published words; raw wording remains available. Swiss manufacture is filled only where the selected page includes a Swiss Made certification section.

Capture completed: `2026-10-03T20:27:55.829Z`.
