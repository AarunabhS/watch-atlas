# Watch Atlas — Codex handoff

Updated: 4 October 2026, Asia/Kolkata. Read this before changing anything.

## 1. Current objective and completion criteria

Maintain Arunabho Kanti Som's Watch Atlas watch research catalogue and existing
dashboard. The priority collection batch comprises Patek Philippe, Breitling,
Jaeger-LeCoultre, Omega, Tudor and IWC, retaining the established 40-column schema
plus full source detail, provenance and dated market-specific snapshots.

The latest product request was to scrape IWC using the successful Omega/Tudor
approach. **That request is complete:** 225/225 IWC US references exported and
audited locally. No further IWC crawling is necessary for this dated capture.
The immediate final request is a safe, recoverable handoff and checkpoint.

Collection success means reference/family count reconciliation, complete selected
product sources, CSV/JSONL/source agreement, hashes verified, no extraction or
record-validation errors, and undisclosed fields left blank. Dashboard integration
success would additionally require validated imports, preserved archive records,
correct totals/filters/details/insights, and desktop/mobile verification.

Do not redesign or restart the application. Latest requests authorize local
collection and handoff; they do not request publishing these two new catalogues.
Prepare reversible local integration when that work is resumed; do not push or
deploy merely because a new session starts.

## 2. Current implementation state

**Important directory distinction:** workspace is
`/Users/Arunabho/Documents/ChatGPT/Watch Atlas`; the real project Git root is
`/Users/Arunabho/Documents/ChatGPT/Watch Atlas/repository`. Run Git, Python and Node
commands in **repository/**. The outer folder has an unrelated empty Git repo on
`master`. Do not add the nested repository to it or initialize/rebuild either repo.
This document is checkpointed at the real root and copied to the workspace root.
All relative paths below refer to the real root.

Completed dashboard: 3,036 watches across nine watchmakers, 23 pocket watches,
73 preserved archive files. Four official imports are already present:

| Brand | References | State |
|---|---:|---|
| Patek Philippe | 252 | Imported; 232 wristwatches and 20 pocket watches |
| Breitling | 402 | Imported US snapshot |
| Jaeger-LeCoultre | 197 | Imported, including specialist/editorial-identified watches |
| Omega | 556 | Imported US snapshot; 553 wristwatches and three pocket watches |
| Tudor | 216 | Complete India/INR capture; import pending |
| IWC | 225 | Complete US capture; import pending |

IWC families: Pilot’s Watches 84, Portugieser 59, Portofino 56, Ingenieur 19,
Aquatimer 7. 210 published USD prices; 15 unpriced references. All 225 have
calibre, frequency, jewel count, movement, selected image and descriptions.
226 referenced source snapshots and 900 technical sections verified.

Tudor: five catalogue pages and all 216 products; 221 referenced snapshots,
216 INR prices, all ten core fields populated. Tudor code predated this session
and was untracked at arrival; it was preserved and revalidated for the checkpoint.

No collector/export/parser is partially implemented for this batch. The existing
`tools/import_catalog.cjs` only supports patek/breitling/jlc/omega. **Tudor and IWC
import support and dashboard integration remain unfinished.** No `dist/` files
were changed in this session. If both complete new catalogues are added without
removing archive records, expected totals are 3,477 watches / 11 watchmakers /
23 pocket watches (3,454 wristwatches). Do not confuse `records.length` with watch
count: the dataset also contains one non-watch wall clock.

Jacob & Co. and Universal Genève remain notebook explorations with zero records;
they are outside the completed six-brand priority batch.

## 3. Important files added or preserved

IWC files added during this session:

- `watch_atlas_scraper/iwc_us_data.py`: current US URL scope, catalogue discovery,
  four technical section parser, reference/price checks and source-preserving mapping.
- `tools/capture_iwc_browser.mjs`: reusable ordinary-browser collector, sequential
  >=3-second pacing, robots scope, content-addressed cache/resume, bounded waits.
- `tools/capture_iwc_us.py`: offline 40-column CSV/full JSONL export, inventory,
  SQLite state and completion manifest.
- `tools/validate_iwc_us.py`: complete reference/hash/technical/price/export audit.
- `tests/test_iwc_us.py`: eight meaningful source and failure cases.
- `tests/fixtures/iwc_us/{priced,unpriced}.{html,json}`: reduced public-source
  fixtures for a priced watch and unpriced specialist, with UTF-8 metadata.
- `docs/iwc_us.md`: reproduction, field mappings, access and source limitations.
- `reports/iwc_us_capture.md`: final capture metrics, verified omissions, exports.
- `CODEX_HANDOFF.md`: session state and continuation instructions.

Previously untracked completed Tudor work included in the recovery checkpoint:
`docs/tudor_in.md`, `reports/tudor_in_capture.md`,
`watch_atlas_scraper/tudor_in_data.py`, `tools/capture_tudor_browser.mjs`,
`tools/capture_tudor_in.py`, `tools/validate_tudor_in.py`,
`tests/test_tudor_in.py`, and four public fixtures under `tests/fixtures/tudor_in/`.

Critical local data (intentionally **ignored by Git**, do not delete):

- `scraping_runs/iwc-us-capture/exports/iwc_watches.csv` and `iwc_watches.jsonl`.
- `scraping_runs/tudor-in-capture/exports/tudor_watches.csv` and `tudor_watches.jsonl`.
- Each capture's `manifest.json`, `inventory.json`, `browser_cache.json`,
  `snapshots/`, `state.sqlite`, robots sources/rules and validation report.
- Existing Patek/Breitling/JLC/Omega research folders remain in place.

Git alone does not restore ignored captures on a different machine. Reuse this
checkout and local files; preserve them separately if relocating the project.

## 4. Architecture and conventions to preserve

- Static browser application in `dist/`; no build/install/backend is needed.
  `dist/data.json` bundles the catalogue. `dist/catalog-model.js` owns normalization
  and analytic summaries; reuse it rather than creating another schema.
- `tools/import_catalog.cjs` is a separate idempotent import step. Replace only
  the matching `source_dataset`; preserve archive records, file inventory,
  existing imports, capture dates, source markets and original currencies.
- `watch_atlas_scraper/schema.py` defines exact `COLUMNS` order (40) and ten `CORE`
  fields. `Record` adds hashes, provenance, missing-field diagnostics and IDs.
  Preserve `image_URL` export and `image_url` application alias.
- Keep raw specifications/structured fields/description/gallery links in JSONL,
  even where the 40 normalized columns do not represent the full disclosure.
  Do not invent years, dimensions, materials or prices from related products.
- Preserve pocket watches in counts while excluding them and the 430 mm wall
  clock from wristwatch diameter comparisons. Keep reduced-motion support,
  search/filter/detail UI, responsive layout and current insights methodology.
- Tudor is **India/INR**, IWC is **US/USD**. Do not overwrite either market.
  Strap width maps to `between_lugs`; buckle width never means lug-to-lug.
- IWC now uses `/us-en/watches/...`, not the old provisional adapter routes.
  The full catalogue DOM contains 225 cards despite initially visible subsets.
  Full `noscript` tables contain Overview/Features/Case/Movement; the mounted UI
  initially includes only Overview. Parse the public fallback, not private runtime.
- Ordinary sequential browsing, >=3 seconds between navigation starts, caches
  and resumable state. No stealth/proxies/CAPTCHA workarounds/reference guessing.
  Stop a transport at access denial; no blind retries. Dedicated collectors are
  local personal research; the historical generic permission-gated framework is
  separate and its old zero-record audit is not the current collection state.
- Git ignores `scraping_runs/`, credentials, permission grants, caches, runtimes
  and dependencies. Commit reusable code/docs/reduced public fixtures only.
- Pushes to `main` deploy `dist/` via GitHub Pages. A local checkpoint is not a
  publishing request. Existing site: https://www.arunabhosom.com/watch-atlas/.

## 5. Current problems and failed approaches

No known failing collector/parser tests or audit errors. Import integration is
the main remaining product task. The standalone IWC Playwright launcher is
syntax-checked, but the successful live capture used Codex's **normal in-app
browser**, not that launcher's separate browser session.

Source omissions are deliberate blank cells, not extraction errors: IWC case
material missing for IW328107/IW389411; dial colour missing for IW345901,
IW388304/IW388305/IW388306; IW659803 omits diameter, thickness, water resistance
and power reserve. Its frequency wording is only `(4 Hz)`. Preserve the raw prose.

Failed approaches that were corrected or abandoned:

- Plain HTTP IWC robots/catalogue requests returned 403. Do not retry with new
  user agents, proxies or alternate identities. The normal browser worked.
- In-app navigation to `/robots.txt` returned `ERR_BLOCKED_BY_CLIENT`. Official
  rules were read through web research; `robots_web.txt` and `robots_rules.json`
  disclose that provenance, while direct HTTP headers/body preserve the 403.
- A single browser-evaluate string was capped at 200,000 characters and appended
  `[Truncated]`. Reading chunks in separate evaluations also allowed DOM changes
  between slices. The final method returned an array of <=100,000-character
  slices from **one** DOM evaluation, checked exact length and closing HTML, then
  hashed/saved it. Do not reuse old incomplete snapshots. Cache references identify
  the validated sources; some orphan intermediate files may remain ignored.
- REPL function reassignment left an older batch closure bound to the initial
  save function. New `iwcSaveV2`/`iwcBatchV2` bindings fixed it. One temporarily
  miskeyed cache entry was replaced, and all final identities/audits passed.
  All browser tabs were closed; fresh sessions must initialize fresh handles.
- Initial IWC tests failed because reduced fixture HTML lacked UTF-8 metadata,
  corrupting currency symbols. Fixtures now declare UTF-8; all tests pass.
- Do not require Product JSON-LD on an unpriced IWC specialist. Some omit it;
  canonical URL and explicit specification reference provide selected identity.
- `node tools/import_catalog.cjs tudor iwc` currently rejects unknown slugs.
  Extend its registry deliberately before attempting these imports.

## 6. Testing state and exact reproduction

All checks below were rerun successfully during handoff preparation, 4 Oct 2026:
100 Python tests, eight dashboard/catalogue tests, both browser syntax checks,
existing 3,036-watch dashboard audit, IWC full audit, Tudor full audit.
No outstanding failed checks. Earlier transient failures are described above.
The checkpoint whitespace check initially flagged trailing spaces in two reduced
IWC HTML fixtures; those spaces were removed and tests/checks rerun.

Bundled Python and Node avoid installation. From the actual Git root:

```sh
cd '/Users/Arunabho/Documents/ChatGPT/Watch Atlas/repository'
PY='/Users/Arunabho/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
NODE='/Users/Arunabho/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
"$PY" -m unittest discover -s tests -q
"$PY" -m tools.validate_iwc_us --output scraping_runs/iwc-us-capture
"$PY" -m tools.validate_tudor_in --output scraping_runs/tudor-in-capture
"$NODE" --test tests/catalog.test.cjs
"$NODE" tools/validate_catalog.cjs
"$NODE" --check tools/capture_iwc_browser.mjs
"$NODE" --check tools/capture_tudor_browser.mjs
git diff --cached --check
```

IWC expected audit: valid=true, 225 references, 226 snapshots, 900 technical
sections, 210 prices, 40 columns. Tudor expected: passed=true, 216 references,
five catalogue pages, 221 snapshots, 216 prices, complete core fields.

To rebuild exports without network if parser code changes:

```sh
"$PY" -m tools.capture_iwc_us --output scraping_runs/iwc-us-capture
"$PY" -m tools.capture_tudor_in --output scraping_runs/tudor-in-capture
```

Optional existing-site preview: `python3 -m http.server 4173 --directory dist`.
No collectors need rerunning over the network for this completed snapshot.

## 7. Exact continuation plan

1. **Immediately** `cd` to the actual root, run `git status --short` and the two
   offline validators above. Confirm local exports/snapshots are present and valid.
   This requires no user questions, crawling, installation or publication.
2. Read `docs/iwc_us.md`, `docs/tudor_in.md`, both final reports,
   `tools/import_catalog.cjs`, `dist/catalog-model.js`, `tools/validate_catalog.cjs`
   and `tests/catalog.test.cjs`. Confirm the checkpoint and preserve working UI.
3. If resumed for the unfinished Atlas integration, extend the existing importer
   with Tudor (`folder: tudor-in-capture`, slug `tudor`, brand `Tudor`, INR/IN) and
   IWC (`folder: iwc-us-capture`, slug `iwc`, brand `IWC`, USD/US). Use distinct
   stable source IDs and existing normalization; update accepted-slug messaging
   and brand order to retain all watchmakers. Do not scrape anew or reset archive.
4. Add meaningful import checks for source counts, market/currency, preserved
   missing prices, idempotence/no duplicates and unchanged archive inventory.
   Review hardcoded current totals/brand sets in validator/tests before importing.
5. Import **locally**, run catalogue checks and relevant tests. Expected watch
   total is 3,477 / 11 brands / 23 pocket watches. Rerun imports to verify
   idempotence. Update README and visible methodology/count text as needed.
6. Preview existing UI on desktop/mobile: all 11 makers appear, combined filters,
   details, currencies, unpriced models and insights work. Preserve current design.
7. Report local integration and remaining publication status. Only push/deploy
   if user authorization for publishing these new datasets is established.

If the resumed task is only to verify the handoff, stop after steps 1–2 and report
that the completed collectors and data are safe; do not manufacture new scope.

## 8. Git state and recovery

- Real repository branch: `codex/modular-watch-scrapers`.
- Remote: `https://github.com/AarunabhS/watch-atlas.git`.
- Starting HEAD and local `origin/main`: `e3d3e49` — Add Jaeger-LeCoultre and Omega
  catalogs to Watch Atlas. Local `main` was `d3de8de`, behind origin/main by two
  commits; do not switch to that stale branch and discard newer work.
- Other relevant commits: `9ad97f9` — Patek/Breitling imports; `d3de8de` — live
  Pages documentation; `df97652` — original dashboard and insights.
- Before recovery checkpoint, only untracked IWC/Tudor source/docs/tests/fixtures
  were present. No tracked files were modified. Both sets passed the above checks.
- The commit containing this file is the local recovery checkpoint, titled
  **Checkpoint validated IWC and Tudor collectors with handoff**. Resolve its
  exact ID with `git log -1 --oneline`; it follows `e3d3e49`. No push is intended.
- Expected real working tree after checkpoint: clean. Raw capture data remain
  ignored and intact; no credentials, browser profiles, dependencies, state DBs
  or full capture dumps belong in the commit. Fixtures were checked for common
  credential patterns with no hits.
- The outer workspace Git repo still has no commits and sees `repository/` and
  the workspace handoff copy as untracked. That is intentional, not a reason to
  initialize, add, clean, delete or move the working project.
- Working functionality and capture exports are safe to continue from. Avoid
  `git clean -fdx`, reset/discard commands, or deleting ignored capture folders.
