"""Build IWC's 40-column CSV and full JSONL from saved official browser pages."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from watch_atlas_scraper.export import save_csv
from watch_atlas_scraper.iwc_us_data import CATALOG, catalogue, official, product
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import State, write_json


def load_pages(folder):
    cache = json.loads((folder / 'browser_cache.json').read_text())
    pages = {}
    for url, meta in cache.items():
        if not official(url) and not official(url, listing=True):
            raise ValueError('Unexpected URL in IWC browser cache: ' + url)
        body = (folder / 'snapshots' / meta['sha256']).read_bytes()
        if hashlib.sha256(body).hexdigest() != meta['sha256'] or b'[Truncated]' in body or not body.rstrip().endswith(b'</html>'):
            raise ValueError('Source integrity failure: ' + url)
        pages[url] = (meta, body)
    return pages


def capture(folder):
    pages = load_pages(folder)
    inventory, counts = catalogue(pages[CATALOG][1])
    state = State(folder)
    rows, errors = [], []
    try:
        for url, (meta, body) in pages.items():
            state.save_response(url, meta, body)
        for ref, item in inventory.items():
            if item['url'] not in pages:
                errors.append({'reference': ref, 'error': 'Product not captured yet'})
                continue
            meta, body = pages[item['url']]
            try:
                row = product(body, item['url'], item, meta)
                state.save_record(row)
                rows.append(row)
            except (ValueError, KeyError, IndexError, TypeError) as error:
                errors.append({'reference': ref, 'error': str(error)})
        rows.sort(key=lambda r: (r['parent_model'], r['reference_number']))
        exports = folder / 'exports'
        exports.mkdir(exist_ok=True)
        save_csv(exports / 'iwc_watches.csv', rows)
        target = exports / 'iwc_watches.jsonl'
        temp = target.with_suffix('.jsonl.tmp')
        temp.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        temp.replace(target)
        write_json(folder / 'inventory.json', list(inventory.values()))
        write_json(folder / 'listing_pages.json', {CATALOG: {'source_hash': pages[CATALOG][0]['sha256'], 'collections': counts, 'references': list(inventory)}})
        manifest = {'source': CATALOG, 'market': 'US', 'language': 'en', 'usage': 'local personal non-commercial research',
                    'captured_at': max(meta['fetched_at'] for meta, _ in pages.values()),
                    'watches_expected': len(inventory), 'watches_captured': len(rows), 'catalog_listing_pages': 1,
                    'reference_coverage_complete': len(rows) == len(inventory) and not errors,
                    'detail_errors': errors, 'validation_errors': [{'reference': r['reference_number'], 'errors': r['validation_errors']} for r in rows if r['validation_errors']],
                    'expected_collections': counts, 'collections': dict(Counter(r['parent_model'] for r in rows)),
                    'published_price_records': sum(bool(r['price']) for r in rows),
                    'missing_fields': {k: sum(not r[k] for r in rows) for k in COLUMNS},
                    'core_coverage': dict(Counter(r['coverage'] for r in rows))}
        write_json(folder / 'manifest.json', manifest)
        return manifest
    finally:
        state.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('scraping_runs/iwc-us-capture'))
    args = parser.parse_args(argv)
    try:
        m = capture(args.output)
    except (ValueError, KeyError, FileNotFoundError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({k: m[k] for k in ('watches_expected', 'watches_captured', 'reference_coverage_complete', 'detail_errors', 'validation_errors')}))
    return 0 if m['reference_coverage_complete'] and not m['validation_errors'] else 2


if __name__ == '__main__':
    sys.exit(main())
