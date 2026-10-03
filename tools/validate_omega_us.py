"""Audit Omega exports against every saved listing and product snapshot, offline."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from watch_atlas_scraper.omega_us_data import FINDER, catalog_page, finder_totals, product, tree
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import State, write_json


def validate(folder):
    folder = Path(folder)
    inventory = json.loads((folder/'inventory.json').read_text())
    pages = json.loads((folder/'listing_pages.json').read_text())
    manifest = json.loads((folder/'manifest.json').read_text())
    rows = [json.loads(line) for line in (folder/'exports/omega_watches.jsonl').read_text().splitlines()]
    with (folder/'exports/omega_watches.csv').open(newline='',encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != COLUMNS:
            raise ValueError('CSV columns differ from the 40-column source schema')
        csv_rows = list(reader)
    items = {x['reference']:x for x in inventory}
    if len(items) != len(inventory) or len(rows) != len({x['reference_number'] for x in rows}):
        raise ValueError('Duplicate inventory/export reference')
    if len(csv_rows) != len(rows) or set(items) != {x['reference_number'] for x in rows}:
        raise ValueError('CSV, JSONL and catalogue reference sets differ')
    if not manifest['reference_coverage_complete'] or manifest['detail_errors'] or manifest['validation_errors']:
        raise ValueError('Manifest reports incomplete capture or errors')
    state = State(folder)
    checked = set()

    def snapshot(url):
        cached = state.cached(url)
        if not cached:
            raise ValueError('Missing saved source: '+url)
        meta, body = cached
        if meta['sha256'] != hashlib.sha256(body).hexdigest():
            raise ValueError('Source hash mismatch: '+url)
        checked.add(url)
        return meta, body

    try:
        _, body = snapshot(FINDER)
        expected, groups = finder_totals(body)
        if expected != len(rows) or expected != manifest['watches_expected']:
            raise ValueError('Export count differs from official finder')
        listed = set()
        for url, entry in pages.items():
            meta, body = snapshot(url)
            data = catalog_page(body,url,meta)
            if data['source_hash'] != entry['source_hash'] or [x['reference'] for x in data['items']] != entry['references']:
                raise ValueError('Saved listing manifest differs from source: '+url)
            listed.update(x['reference'] for x in data['items'])
        if listed != set(items):
            raise ValueError('Listings do not reconcile to inventory')
        field_counts = {}
        visible_prices_verified = 0
        for exported, csv_row in zip(rows,csv_rows):
            ref = exported['reference_number']
            meta, body = snapshot(items[ref]['url'])
            parsed = product(body,meta['url'],items[ref],meta)
            amounts = {x for x in tree(body).xpath('//*[contains(concat(" ",@class," ")," product-info-price ")]//*[@data-price-type="finalPrice"]/@data-price-amount')}
            if len(amounts)>1:
                raise ValueError(f'{ref}: conflicting visible selected prices')
            if amounts and exported['price']:
                if float(next(iter(amounts))) != float(exported['price']):
                    raise ValueError(f'{ref}: visible price differs from structured offer')
                visible_prices_verified += 1
            for key in COLUMNS:
                if exported[key] != parsed[key] or csv_row[key] != exported[key]:
                    raise ValueError(f'{ref}: CSV/JSONL/source disagreement for {key}')
            for key in ('source_product_fields','raw_specifications','raw_listing_fields','provenance','image_urls','variant_urls','collection_label','source_hash','source_field_count','missing_fields','validation_errors'):
                if parsed[key] != exported[key]:
                    raise ValueError(f'{ref}: source metadata disagreement for {key}')
            if parsed['validation_errors']:
                raise ValueError(f'{ref}: validation errors')
            for code in parsed['raw_specifications']:
                field_counts[code] = field_counts.get(code,0)+1
        result = {'valid':True,'watches':len(rows),'csv_columns':len(COLUMNS),
                  'source_snapshots_verified':len(checked),'listing_pages_verified':len(pages),
                  'finder_collections':groups,'technical_field_coverage':field_counts,
                  'visible_selected_prices_verified':visible_prices_verified,
                  'csv_jsonl_source_agreement':True,'source_hashes_verified':True}
        write_json(folder/'validation.json',result)
        return result
    finally:
        state.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('scraping_runs/omega-us-capture'))
    args=p.parse_args()
    print(json.dumps(validate(args.output),indent=2))


if __name__ == '__main__': main()
