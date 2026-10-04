# Rolex and Breguet reference refresh

The refresh replaces verified archive fields in place, preserves existing Atlas
IDs and the 73-file archive inventory, and adds current Breguet references that
were absent from the archive. It does not modify other watchmakers.

Rolex uses the 840 exact-variant rendered DOM captures from the completed audit.
Case, movement, bracelet and dial labels stay scoped to their sections. In
particular, case Material and bracelet Material cannot overwrite one another.
Images come from the selected variant's observed image URL; the same full
reference must occur in the image path. Positive browser image loads verify 641
images, and paced HTTP response checks verify the remaining 199.

Breguet starts from all 201 observed finder cards. Selected printed references,
canonical URLs and Product SKUs establish identity, and only actually published
variant links enter the queue. The two cards whose names are `undefined` also
serve empty product templates with no visible identity/specifications/images;
their source bytes and exclusion reasons remain in the manifest. The other 199
references include the two product templates served under `/en/news/`.

For 8928BR8D944DD0D3L, the printed reference omits `3L`; the Product SKU, Product
ID and canonical URL retain it. The full SKU is preserved and the discrepancy is
shown in additional specifications. This narrow exception does not treat arbitrary
reference differences as equivalent. The 5177BR/15/RV0 page publishes no selected
front image. Its record retains the normal fallback and explains the omission.

Historical Rolex pages that are unavailable retain their historical specifications
and an unverified notice. Unresolved Breguet rows whose model/reference identities
conflict retain the original Atlas ID/reference while unreliable model/details are
withheld. The starting snapshot preserves the original values for review.
Known broken product/image links are not offered as current watchmaker links.

Fresh records do not inherit archive prices or currencies. The current Global/en
documents publish no comparable prices, so price values remain empty; the reported
price lookup continues separately. Source dates are the actual capture dates,
including reused audit captures, rather than the date of import.

## Reproduction

Run from the isolated refresh worktree. `scraping_runs/` remains ignored and must
be preserved separately. It contains the starting snapshot, finder inventory,
source documents/DOM snapshots, SQLite cache, export JSONL, image proofs and final
integration report. `--audit-root` points to the original completed audit folder.

```sh
python3 -m tools.refresh_breguet --audit-root /path/to/rolex-breguet-audit-2026-10-04
python3 -m tools.prepare_rolex_refresh --audit-root /path/to/rolex-breguet-audit-2026-10-04
python3 -m tools.prepare_refresh_images --audit-root /path/to/rolex-breguet-audit-2026-10-04
python3 -m tools.audit_archive_links --baseline scraping_runs/rolex-breguet-refresh-2026-10-05/rolex-image-candidates.json --brand Rolex --output scraping_runs/rolex-breguet-refresh-2026-10-05/rolex-images
python3 -m tools.audit_archive_links --baseline scraping_runs/rolex-breguet-refresh-2026-10-05/breguet-image-candidates.json --brand Breguet --output scraping_runs/rolex-breguet-refresh-2026-10-05/breguet-images
node tools/apply_watch_refresh.cjs
node tools/build-price-catalog.cjs
python3 -m unittest discover -s tests -q
node tools/validate_catalog.cjs
node --test tests/*.test.cjs tests/*.test.mjs
```

The importer refuses pending/unreviewed documents, duplicate source identities,
unverified nonempty image URLs, changed source hashes or lost archive IDs. Importing
the same snapshot twice produces identical catalog data. Publish through the
existing GitHub Pages workflow; redeploy the existing price worker when its public
identity allowlist changes. Retain its server-side secret and existing permissions.
