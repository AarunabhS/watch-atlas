# Rolex and Breguet platform refresh

Prepared 5 October 2026 (Asia/Kolkata). Original snapshots and all existing watch IDs are preserved.

| Brand | Current verified references | Working images | Historical unverified references |
|---|---:|---:|---:|
| Rolex | 840 | 840 | 249 |
| Breguet | 199 | 198 | 67 |

The Atlas now contains 3,636 watches: 3,612 wristwatches and 24 pocket watches across 11 makers. Breguet adds 159 references. All 1,196 existing Rolex/Breguet IDs survive, retaining saved comparisons. Other watchmakers and the 73-file archive inventory are unchanged.

Rolex case and bracelet materials stay in their own sections. The 177 confirmed case-material errors are corrected; selected images, clasp, crown, precision, oscillator, winding and certification details are restored. Current function wording and bezel/dial descriptions are retained.

Breguet names, technical sections, images and URLs are rebuilt against exact reference identities. Case and movement dimensions remain separate; non-circular width/height measurements do not enter diameter averages. Explicit function phrases from each selected Product description are retained. Current Global/en sources do not provide comparable prices, so fresh records do not inherit archive prices/currencies. Reported-price lookup remains separate.

Unresolved records remain visibly marked historical/unverified. The 53 unresolved Breguet rows with mismatched archived model/reference identities have their unreliable details withheld; original values remain in the starting snapshot. Known broken links are removed from current source/image controls. Current verified records lead each brand’s curated view. Searches accept old slash-separated references and current printed separators.

## Source gaps and discrepancies

- 5177BR/15/RV0 publishes no selected front image. Its current reference/details are retained with the normal image fallback and an explanation.
- 8928BR8D944DD0D3L has a printed reference without 3L; the Product SKU, Product ID and canonical URL preserve the suffix. Its full identity and the disagreement are visible in additional specifications.
- All 201 finder cards were reconciled. Two undefined K8068 cards serve incomplete product documents without visible model/reference/specifications/images; source snapshots and reviewed exclusions are retained. The other 199 include two product templates under /news/.
- Missing current historical pages do not establish discontinuation.

## Validation and evidence

- 840 Rolex images: 641 positive browser loads and 199 valid HTTP image responses.
- 198 Breguet images: valid HTTP image responses, including 40 checks reused from the completed audit.
- 107 Python tests and 51 JavaScript tests pass; source hashes, exact identities, IDs, catalog totals and the unchanged other brands were verified.
- Importing the same snapshot again produces identical catalog bytes.
- [Per-reference field changes and integration evidence](rolex_breguet_refresh.json).
- [Collector/import instructions](../docs/rolex_breguet_refresh.md).
- Ignored source/export/image evidence: scraping_runs/rolex-breguet-refresh-2026-10-05/.

## Publication verified

The refresh is live at [Watch Atlas](https://www.arunabhosom.com/watch-atlas/).
Catalog commit `e413c5772959354e49ee665778f17aa0d04189e1` passed the
[GitHub Pages deployment](https://github.com/AarunabhS/watch-atlas/actions/runs/37232968686).
The public index, catalog JSON, application script, catalog model and stylesheet
each returned HTTP 200 and matched the validated local bytes. Catalog SHA-256:
`b6ee623a127710a8ce73e88e9e1fcb4c80f25cd209f5372c91d80893e93cc2ee`.

The live catalog displays 3,636 references, Breguet 266 and Rolex 1,089. Live
details for new Breguet Marine Chronographe 5527TI/G2/TW0 and refreshed Rolex
Datejust 36 126234-0051 load their exact selected images and restored technical
details. Local screenshots are retained with the ignored refresh evidence.

The existing price worker was deployed with 1,792 eligible identities as version
`06464ef2-4991-429c-ac5c-363ac9fcf7b4`. Its website CORS preflight returned 204.
Existing bindings and server-side secret were preserved; verification made no
paid provider searches.
