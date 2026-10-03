"""Small Patek-specific collector for the user's local non-commercial research.

Run from the repository root: python -m tools.scrape_patek
No login, speculative URLs, APIs, image downloads or bot-evasion measures.
"""
import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from watch_atlas_scraper.adapters import ADAPTERS
from watch_atlas_scraper.client import Client, FetchError, HostBlocked
from watch_atlas_scraper.curl_transport import CurlTransport
from watch_atlas_scraper.export import save_csv
from watch_atlas_scraper.patek_data import ORIGIN, FINDER, catalog, product
from watch_atlas_scraper.policy import PermissionDenied
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import State, write_json


class PersonalResearch:
    """The clarified task scope, separate from a license to republish a database."""
    def require(self, brand, url, purpose='collection'):
        from watch_atlas_scraper.policy import PermissionDenied
        p = urlsplit(url)
        if brand != 'patek' or purpose != 'collection' or p.scheme != 'https' or p.netloc != 'www.patek.com' or not p.path.startswith('/en/collection/'):
            raise PermissionDenied('This script is scoped to local personal Patek catalog research')


def save_outputs(state, folder, inventory, future, selected, errors, as_of):
    rows = state.records(['Patek Philippe'])
    # Current inventory controls exports; old runs cannot leak removed references.
    wanted = {x['articleRef'] for x in selected}
    rows = [x for x in rows if x['reference_number'] in wanted]
    rows.sort(key=lambda x:(x.get('catalog_collection',x['parent_model']),x['reference_number']))
    exports = folder / 'exports'
    exports.mkdir(exist_ok=True)
    save_csv(exports / 'patek_watches.csv', rows)
    save_csv(exports / 'patek_wristwatches.csv', [x for x in rows if x['subtype'] == 'Wristwatch'])
    save_csv(exports / 'patek_pocket_watches.csv', [x for x in rows if x['subtype'] == 'Pocketwatch'])
    path = exports / 'patek_watches.jsonl'
    temp = path.with_suffix('.jsonl.tmp')
    temp.write_text(''.join(json.dumps(row,ensure_ascii=False) + '\n' for row in rows))
    temp.replace(path)
    failures = [x for x in rows if x.get('validation_errors')]
    manifest = {
        'captured_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(), 'catalog_as_of':as_of,
        'source':FINDER, 'usage':'local personal non-commercial research',
        'current_timepieces_discovered':len(inventory), 'not_current_entries':len(future),
        'current_subtypes':dict(Counter(x['subtype'] for x in inventory)),
        'watches_expected':len(selected), 'watches_captured':len(rows),
        'detail_errors':errors, 'validation_errors':[{'reference':x['reference_number'],'errors':x['validation_errors']} for x in failures],
        'source_discrepancy_records':sum(bool(x.get('source_discrepancies')) for x in rows),
        'collections':dict(Counter(x['parent_model'] for x in rows)),
        'catalog_watch_collections':dict(Counter(x['collectionName'] for x in selected)),
        'reference_coverage_complete':len(rows) == len(selected) and not errors,
        'specification_note':'Every ProductDetail datasource field is retained. Blank legacy fields were not published or lack a direct mapping; catalog coverage does not prove every conceivable specification exists.',
        'missing_fields':{key:sum(not x.get(key) for x in rows) for key in COLUMNS},
        'clocks_excluded_from_watch_export':sum('clock' in str(x['subtype']).lower() for x in inventory),
    }
    write_json(folder / 'manifest.json', manifest)
    return manifest


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('scraping_runs/patek-personal-research'))
    p.add_argument('--as-of',default=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat())
    p.add_argument('--limit',type=int,help='Optional pilot size; omitted means all current watches')
    p.add_argument('--reparse',action='store_true',help='Reparse saved pages after a mapping change; fresh cache avoids repeat downloads')
    p.add_argument('--delay',type=float,default=3)
    p.add_argument('--transport',choices=['curl','urllib'],default='curl' if shutil.which('curl') else 'urllib')
    args = p.parse_args(argv)
    if args.delay < 3 or (args.limit is not None and args.limit < 1):
        p.error('delay must be >=3 seconds; limit must be positive')
    state = State(args.output)
    client = Client('patek', ADAPTERS['patek'], PersonalResearch(), state, args.delay,
                    transport=CurlTransport() if args.transport == 'curl' else None)
    errors = []
    try:
        _, body = client.get(FINDER)
        current, future = catalog(body,args.as_of)
        write_json(args.output / 'current_inventory.json',current)
        write_json(args.output / 'not_current_inventory.json',future)
        selected = [x for x in current if x['subtype'] in ('Wristwatch','Pocketwatch')]
        selected.sort(key=lambda x:(x['collectionName'],x['articleRef']))
        captured = {x['reference_number'] for x in state.records() if x.get('product_detail_parsed')}
        remaining = [x for x in selected if args.reparse or x['articleRef'] not in captured]
        print(f'Current catalog: {len(current)} timepieces; {len(selected)} watches; {len(remaining)} detail pages remaining',flush=True)
        save_outputs(state,args.output,current,future,selected,errors,args.as_of)
        items = remaining[:args.limit] if args.limit else remaining
        for position,item in enumerate(items,1):
            url = urljoin(ORIGIN,item['url'])
            try:
                meta, page = client.get(url)
                row = product(page,meta['url'],item,meta)
                state.save_record(row)
                print(f'{row["reference_number"]}: {row["source_field_count"]} source fields; {row["caliber"] or "caliber not published"}',flush=True)
            except (HostBlocked,PermissionDenied) as e:
                errors.append({'reference':item['articleRef'],'url':url,'error':str(e)})
                print(f'Stopped at access or scope restriction: {e}',flush=True)
                break
            except (FetchError,ValueError,KeyError,StopIteration) as e:
                errors.append({'reference':item['articleRef'],'url':url,'error':str(e)})
                print(f'{item["articleRef"]}: recorded error {e}',flush=True)
            # Records are committed individually. Batch only the derived exports
            # during an offline reparse to avoid rewriting a large JSONL 252 times.
            if not args.reparse or position % 25 == 0:
                save_outputs(state,args.output,current,future,selected,errors,args.as_of)
        manifest = save_outputs(state,args.output,current,future,selected,errors,args.as_of)
        print(json.dumps({'captured':manifest['watches_captured'],'expected':manifest['watches_expected'],'complete':manifest['reference_coverage_complete'],'output':str(args.output / 'exports')}),flush=True)
        return 0 if manifest['reference_coverage_complete'] else 2
    finally:
        state.close()


if __name__ == '__main__':
    sys.exit(main())
