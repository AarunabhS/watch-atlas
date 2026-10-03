# Omega US capture — completed

All **556 references** in the captured official US watch finder were collected:
**553 wristwatches and 3 pocket watches**.
The reference set matches every collection's published count. There are zero
request/extraction failures and zero record validation errors.

Source pages were captured on **3 October 2026**, between approximately
17:48 and 18:47 India time. Final offline processing and validation were completed
on 04 October 2026.
The result is a dated US-market catalogue snapshot, rather than a claim about
all historical references or all countries.

| Collection | References |
| --- | ---: |
| Constellation | 128 |
| De Ville | 122 |
| Seamaster | 204 |
| Specialities | 4 |
| Speedmaster | 98 |
| **Total** | **556** |

## Files

- `scraping_runs/omega-us-capture/exports/omega_watches.csv`: original 40 columns.
- `scraping_runs/omega-us-capture/exports/omega_watches.jsonl`: mapped fields,
  raw technical fields, selected structured product and tracking data, headings,
  movement indicators and description, image links, related references and provenance.
- `scraping_runs/omega-us-capture/manifest.json`: completion and field coverage.
- `scraping_runs/omega-us-capture/validation.json`: completed offline audit.
- `scraping_runs/omega-us-capture/inventory.json` and `listing_pages.json`: source inventory.
- `scraping_runs/omega-us-capture/snapshots/` and `state.sqlite`: complete saved HTML,
  hashes, cache and resumable state.
- [Collector](../tools/capture_omega_us.py), [mapping](../watch_atlas_scraper/omega_us_data.py),
  [validator](../tools/validate_omega_us.py), [instructions](../docs/omega_us.md).

Capture files are local and ignored by Git. The script itself does not publish them.

## Collection method

Omega exposes its catalogue and detail tables in public HTML. A focused HTTP
collector was sufficient. It uses sequential requests with at least three seconds
between request starts, robots checks, cache, bounded retries and saved progress.
No product reference numbers were generated and no accounts or private endpoints
were accessed.

The 28 catalogue pages are cumulative: page two returns the first 48 watches,
including the first page's 24. References are deduplicated and cumulative membership
is verified. The unfiltered watch finder supplies the total and family counts;
its disallowed query pagination is not requested.

Specialities is absent from the main navigation and its parent catalogue redirects.
Its Olympic Pocket Watch and Olympic 1932 Chrono Chime subcatalogues provide the
remaining four references. Three pocket watches use the older eight-digit references,
such as `5108.20.00`.

## Mapping checks

Selected technical references must match the requested and canonical URLs.
Related `addOn` prices remain separate. Some pages omit a redundant collection
heading; their selected product's explicit tracking taxonomy supplies the parent
family. Detailed dial colours, strap colours and buckle types are mapped from
published technical fields. Frequency comes from the current movement indicators.
Quartz battery life preserves Omega's power-reserve wording and its original units.

The Bond reference `210.30.42.20.03.004` uses binary text for its description.
Its readable UTF-8 description and explicit calibre 8806 are exported, with the
original binary text preserved. That snapshot supplies no price, usable product
image, movement type or power reserve; those fields stay blank. The relative
`?w=230` placeholder is not exported as an image URL.

| Normalized field | Populated |
| --- | ---: |
| reference_number | 556 / 556 |
| parent_model | 556 / 556 |
| case_material | 556 / 556 |
| diameter | 556 / 556 |
| water_resistance | 556 / 556 |
| caliber | 556 / 556 |
| dial_color | 555 / 556 |
| movement | 555 / 556 |
| power_reserve | 555 / 556 |
| frequency | 452 / 556 |
| price | 555 / 556 |
| image_URL | 555 / 556 |
| bracelet_material | 552 / 556 |
| bracelet_color | 233 / 556 |
| clasp_type | 532 / 556 |

Fields absent from structured technical attributes, such as bezel material, can
still occur in the preserved description. They are not guessed into normalized
columns. All captured technical fields and full HTML remain available for further
mapping. No historical introduction years or undocumented specifications are invented.

## Verification

- **81 Python tests passed**, including 20 Omega-specific cases.
- Every exported reference matches the saved finder and collection inventory.
- **585 source snapshots** passed SHA-256 verification,
  including all 28 catalogue pages and all 556 product pages.
- Every one of the 40 CSV fields agrees with JSONL and the saved source mapping.
- **555 selected prices** independently agree
  with the page's visible price amount.
- Zero detail failures, duplicate references or record validation errors.

```sh
python3 -m tools.capture_omega_us --output scraping_runs/omega-us-capture
python3 -m tools.capture_omega_us --offline --reparse --output scraping_runs/omega-us-capture
python3 -m tools.validate_omega_us --output scraping_runs/omega-us-capture
```

Official sources: [US watch finder](https://www.omegawatches.com/en-us/watchfinder),
[Seamaster](https://www.omegawatches.com/en-us/watches/seamaster),
[Speedmaster](https://www.omegawatches.com/en-us/watches/speedmaster),
[Constellation](https://www.omegawatches.com/en-us/watches/constellation),
[De Ville](https://www.omegawatches.com/en-us/watches/de-ville),
[Olympic Pocket Watch](https://www.omegawatches.com/en-us/watches/specialities/olympic-pocket-watch/catalog),
[Olympic 1932 Chrono Chime](https://www.omegawatches.com/en-us/watches/specialities/olympic-1932-chrono-chime/catalog).
