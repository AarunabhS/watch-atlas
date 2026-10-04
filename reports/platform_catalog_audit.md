# Watch Atlas platform catalog audit

Audited 4 October 2026, Asia/Kolkata.

The public dashboard initially matched the existing local bundle exactly: 3,036
watches across nine watchmakers. The completed Tudor and IWC exports were absent
from that bundle and the live site. Adding those 441 references produces 3,477
watches across eleven watchmakers, including 3,454 wristwatches and 23 pocket
watches. Jacob & Co. and Universal Genève are being collected separately and are
outside this completed-capture audit.

| Completed capture | Exported references | Corrected catalog references | Source market |
|---|---:|---:|---|
| Patek Philippe | 252 | 252 | International |
| Breitling | 402 | 402 | US |
| Jaeger-LeCoultre | 197 | 197 | US |
| Omega | 556 | 556 | US |
| Tudor | 216 | 216 | India |
| IWC | 225 | 225 | US |
| Total official captures | 1,848 | 1,848 | |

Every normalized field of all 1,848 imported references matches its completed
JSONL export through the shared catalog model. Export hashes match the catalog
provenance. Record IDs are unique. Repeating all six imports produces a byte-for-
byte identical catalog. All archive records, archive statistics and the 73-file
inventory match the pre-change public bundle exactly.

The new imports preserve Tudor's INR prices and IWC's USD prices. Grouped IWC
prices such as `6,900` now become numeric values with a visible currency. The 15
unpriced IWC references remain unpriced. IWC's parser explicitly marks successfully
parsed product details, allowing the importer to retain its existing validation
gate. Additional source specifications include strap descriptions, crowns,
movement component counts, Tudor guarantees and price basis. Tudor Chrono,
Pelagos and IWC Aquatimer names feed the existing segment filters; selected IWC
diamond specifications feed gemstone filters.

Validation passed: eleven catalog tests, eight IWC parser tests, complete IWC
and Tudor offline source audits, catalog consistency checks and script syntax
checks. Desktop browser checks found one representative reference and a loaded
image from every completed capture. Tudor INR and IWC USD details, IWC's
unpublished-price display, eleven maker filters and IWC insights were checked.
At a 390 × 844 mobile viewport, combined Tudor/Chronograph/Automatic filters
returned 16 references with no page overflow.

Missing source data remain unspecified. Patek publishes no prices in this
capture; JLC has 79 unpriced references; Omega has one unpriced reference and one
reference with no captured image. That Omega entry remains accessible using the
existing image fallback. Image checks were representative browser checks, not an
HTTP audit of every remotely hosted image. Capture dates describe dated snapshots
and do not assert present-day manufacturer availability.
