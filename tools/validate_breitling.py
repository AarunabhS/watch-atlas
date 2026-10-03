"""Validate a saved Breitling run against its original snapshots; no network."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from watch_atlas_scraper.breitling_data import catalog_page, page_data, product
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import State, write_json


def validate(folder):
    folder = Path(folder)
    inventory = json.loads((folder / 'inventory.json').read_text())
    manifest = json.loads((folder / 'manifest.json').read_text())
    browser = json.loads((folder / 'rendered_pages' / 'manifest.json').read_text())
    rows = [json.loads(line) for line in (folder / 'exports' / 'breitling_watches.jsonl').read_text().splitlines()]
    with (folder / 'exports' / 'breitling_watches.csv').open(newline='',encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        fields, csv_rows = reader.fieldnames, list(reader)
    errors, checks = [], Counter()

    def check(condition, name, reference=''):
        checks[name] += 1
        if not condition:
            errors.append({'check':name, 'reference':reference})

    wanted = {x['reference'] for x in inventory}
    by_reference = {x['reference']:x for x in inventory}
    check(len(wanted) == len(inventory) == browser['expected'], 'unique_catalog_inventory')
    check({x['reference_number'] for x in rows} == wanted and len(rows) == len(wanted), 'complete_unique_jsonl')
    check(fields == COLUMNS and len(csv_rows) == len(rows), 'csv_schema_and_count')
    check(all(c == {k:r[k] for k in COLUMNS} for c,r in zip(csv_rows,rows)), 'csv_jsonl_equality')
    check(manifest['reference_coverage_complete'] and not manifest['detail_errors'] and not manifest['validation_errors'], 'complete_manifest_without_errors')
    check(set(x['page'] for x in browser['pages']) == set(range(browser['declared_page_count'])), 'all_catalog_pages')

    discovered = []
    listing_hashes = {}
    for entry in browser['pages']:
        body = (folder / 'rendered_pages' / entry['file']).read_bytes()
        check(hashlib.sha256(body).hexdigest() == entry['sha256'], 'catalog_snapshot_integrity', entry['file'])
        parsed = catalog_page(body,entry['url'],entry)
        refs = [x['reference'] for x in parsed['items']]
        check(refs == entry['references'], 'rendered_catalog_reference_identity', entry['file'])
        discovered.extend(refs)
        listing_hashes.update({ref:entry['sha256'] for ref in refs})
    check(set(discovered) == wanted and len(discovered) == len(wanted), 'rendered_pages_match_inventory')

    state = State(folder)
    try:
        for row in rows:
            ref = row['reference_number']
            if ref not in wanted:
                continue
            cached = state.cached(row['watch_URL'])
            check(cached is not None, 'detail_snapshot_exists', ref)
            if not cached:
                continue
            meta, body = cached
            check(hashlib.sha256(body).hexdigest() == row['source_hash'] == meta['sha256'], 'detail_snapshot_integrity', ref)
            _, props = page_data(body)
            variant = props['productVariant']
            check(variant['sku'] == ref, 'selected_source_reference', ref)
            check(row['raw_product_fields'] == variant['product'] and row['source_field_count'] == len(variant['product']), 'all_product_fields_preserved', ref)
            check(row['raw_variant_fields'] == {k:v for k,v in variant.items() if k!='product'}, 'all_variant_fields_preserved', ref)
            check(row['raw_structured_product'] == props.get('productStructuredData',{}), 'structured_product_preserved', ref)
            check(row['catalog_source_hash'] == listing_hashes.get(ref), 'catalog_provenance', ref)
            check(not row['validation_errors'], 'record_validation', ref)
            check(all(p['value'] == row[k] and p['url'] == row['watch_URL'] for k,p in row['provenance'].items()), 'field_provenance_matches_export', ref)
            check(product(body,meta['url'],by_reference[ref],meta) == row, 'mapping_reproduces_saved_record', ref)
        network_events = dict(state.db.execute("SELECT kind,count(*) FROM events WHERE kind IN ('circuit_open','robots_denied') GROUP BY kind"))
        check(not network_events and not state.blocked('www.breitling.com'), 'no_access_or_robots_blocks')
    finally:
        state.close()
    report = {
        'validated_at':datetime.now(timezone.utc).isoformat(), 'network_requests':0,
        'passed':not errors, 'watches':len(rows), 'catalog_pages':len(browser['pages']),
        'checks':dict(checks), 'errors':errors,
        'source_fields_preserved':sum(x['source_field_count'] for x in rows),
        'source_field_counts':dict(Counter(x['source_field_count'] for x in rows)),
        'missing_core_fields':dict(Counter(k for x in rows for k in x['missing_core_fields'])),
    }
    write_json(folder / 'validation.json',report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('scraping_runs/breitling-personal-research'))
    args = parser.parse_args()
    report = validate(args.output)
    print(json.dumps({k:report[k] for k in ('passed','watches','catalog_pages','source_fields_preserved','errors')}))
    return 0 if report['passed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
