# Omega collection

The Omega-specific collector follows the public US collection catalogue pages,
then downloads each listed watch detail page sequentially. It saves the same
40-column CSV used by the earlier Patek Philippe and Breitling captures, plus
JSONL with source fields and provenance. Captures are local and ignored by Git.

Run from the repository with Python 3.11 or later, `lxml` and `curl` available:

```sh
python3 -m tools.capture_omega_us --output scraping_runs/omega-us-capture
python3 -m tools.validate_omega_us --output scraping_runs/omega-us-capture
```

The default delay is three seconds between request starts. Downloads are
sequential; network failures have bounded retries. Progress, content-addressed
HTML snapshots and exports are saved locally. Running the same command resumes
missing references. Use `--limit 5` for a pilot, and `--offline --reparse` to
apply mapping changes to saved pages without any network access. A pilot
correctly reports incomplete catalogue coverage.

## Site structure

Omega's Magento site already publishes the catalogue and technical tables in
its HTML, so this capture needs no headless browser. Catalogue pagination is
cumulative: page two contains 48 watches, including page one's 24. The collector
follows the actual next-page links, deduplicates references, checks cumulative
containment, and reconciles collection counts with the unfiltered watch finder.
It does not generate product reference numbers.

The main collection pages cover Seamaster, Speedmaster, Constellation and
De Ville. Specialities uses two separate subcatalogues: Olympic Pocket Watch
and Olympic 1932 Chrono Chime. Its parent catalogue redirects to the marketing
index. The three pocket references use the older `5108.20.00` style, while
current references use `310.30.42.50.01.002` formatting.

The robots checks allow the actual collection page links, including their `p`
pagination parameters. Watch-finder query URLs are disallowed and are not used.
The scope excludes accounts, checkout, private APIs and other locales. A denied
request or challenge stops the host's run; no identity rotation is used.

## Field mapping

Technical table `data-code` attributes identify the current reference, case
diameter and thickness, lug measurements, case and dial materials, crystal,
water resistance, weight, calibre, movement, power reserve and strap details.
The collector validates the technical reference against the requested and
canonical product URLs before saving a record. H1 collection, subcollection and
configuration provide its model identity. Selected Product JSON-LD supplies
its image and published USD offer. Movement indicators supply explicitly stated
frequency in Hz. `addOn` offers are related watches and never
supply a missing current price. Feature tags and current movement prose are
retained separately from related watches and accessories.

Unpublished values remain blank; descriptions are not used to invent a case
shape, introduction year or jewel count. Raw technical fields,
headings, selected structured product and tracking data, movement description,
image links and related watch links are retained in JSONL. Full source HTML and
SHA-256 hashes remain available for later mapping improvements.

Where Omega omits a collection heading to avoid repetition, the selected
product's published tracking taxonomy supplies the parent collection. Detailed
dial colours take precedence over broad colour labels. Strap colours and buckle
types come from the selected technical table. The Bond edition's binary text is
decoded to readable UTF-8 while its original text remains in the raw fields.

The offline validator checks the complete reference set, every saved source
hash, each catalogue page and every mapped field against both exports.
