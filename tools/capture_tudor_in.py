"""Build the Tudor India export from cached normal-browser catalogue/product pages."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from watch_atlas_scraper.export import save_csv
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import State, write_json
from watch_atlas_scraper.tudor_in_data import CATALOG, catalog_page, official, product


def load_pages(folder):
    cache = json.loads((folder / 'browser_cache.json').read_text())
    pages = {}
    for url, meta in cache.items():
        if not official(url) and not official(url, 'listing'):
            raise ValueError('Unexpected URL in Tudor browser cache: ' + url)
        body = (folder / 'snapshots' / meta['sha256']).read_bytes()
        if hashlib.sha256(body).hexdigest() != meta['sha256']:
            raise ValueError('Source snapshot integrity failure: ' + url)
        pages[url] = (meta, body)
    return pages


def discover(pages):
    if CATALOG not in pages:
        raise ValueError('Initial Tudor catalogue page is missing')
    pending, seen, inventory, listing = [CATALOG], set(), {}, {}
    expected, page_count = None, None
    while pending:
        url = pending.pop(0)
        if url in seen:
            continue
        if url not in pages:
            raise ValueError('Published catalogue page is missing: ' + url)
        seen.add(url)
        meta, body = pages[url]
        page = catalog_page(body, url, meta)
        if expected is None:
            expected, page_count = page['expected'], page['pages']
        if (expected, page_count) != (page['expected'], page['pages']):
            raise ValueError('Catalogue total changed during capture')
        refs = []
        for item in page['items']:
            ref = item['reference']
            if ref in inventory:
                raise ValueError('Repeated reference across catalogue pages: ' + ref)
            inventory[ref] = item
            refs.append(ref)
        listing[url] = {'page': page['page'], 'references': refs, 'source_hash': page['source_hash']}
        pending.extend(u for u in page['pagers'] if u not in seen)
    if len(inventory) != expected or len(listing) != page_count or {p['page'] for p in listing.values()} != set(range(page_count)):
        raise ValueError('Incomplete Tudor catalogue discovery')
    return inventory, listing


def capture(folder):
    pages = load_pages(folder)
    inventory, listing = discover(pages)
    state = State(folder)
    rows, errors = [], []
    try:
        for url, (meta, body) in pages.items():
            state.save_response(url, meta, body)
        for ref, item in inventory.items():
            if item['url'] not in pages:
                errors.append({'reference': ref, 'error': 'Product snapshot not captured yet'})
                continue
            meta, body = pages[item['url']]
            try:
                row = product(body, item['url'], item, meta)
                state.save_record(row)
                rows.append(row)
            except (ValueError, KeyError, IndexError) as error:
                errors.append({'reference': ref, 'error': str(error)})
        rows.sort(key=lambda r: (r['parent_model'], r['reference_number']))
        exports = folder / 'exports'
        exports.mkdir(exist_ok=True)
        save_csv(exports / 'tudor_watches.csv', rows)
        path = exports / 'tudor_watches.jsonl'
        temp = path.with_suffix('.jsonl.tmp')
        temp.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        temp.replace(path)
        write_json(folder / 'inventory.json', list(inventory.values()))
        write_json(folder / 'listing_pages.json', listing)
        manifest = {
            'source': CATALOG, 'market': 'IN', 'language': 'en',
            'captured_at': max(meta['fetched_at'] for meta, _ in pages.values()),
            'usage': 'local personal non-commercial research',
            'watches_expected': len(inventory), 'watches_captured': len(rows),
            'catalog_listing_pages': len(listing), 'product_pages': sum(official(url) for url in pages),
            'reference_coverage_complete': len(rows) == len(inventory) and not errors,
            'detail_errors': errors,
            'validation_errors': [{'reference': r['reference_number'], 'errors': r['validation_errors']} for r in rows if r['validation_errors']],
            'collections': dict(Counter(r['parent_model'] for r in rows)),
            'published_price_records': sum(bool(r['price']) for r in rows),
            'core_coverage': dict(Counter(r['coverage'] for r in rows)),
            'missing_fields': {k: sum(not r[k] for r in rows) for k in COLUMNS},
            'specification_note': 'Current English India catalogue, five public paginated lists. Every exported watch is checked against its selected product page, including all technical specifications and INR suggested retail price. Full rendered sources and original catalogue data are retained. Tudor calls its lugToLugSpec field lug width on the visible page; this maps to between_lugs, never lug_to_lug. Undisclosed fields remain blank.'
        }
        write_json(folder / 'manifest.json', manifest)
        return manifest
    finally:
        state.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('scraping_runs/tudor-in-capture'))
    args = parser.parse_args(argv)
    try:
        result = capture(args.output)
    except (ValueError, KeyError, FileNotFoundError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({k: result[k] for k in ('watches_expected', 'watches_captured', 'reference_coverage_complete', 'validation_errors')}))
    return 0 if result['reference_coverage_complete'] and not result['validation_errors'] else 2


if __name__ == '__main__':
    sys.exit(main())
