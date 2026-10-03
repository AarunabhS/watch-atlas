"""Sequential Breitling US catalog collector for local non-commercial research."""
import argparse
import json
import hashlib
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from watch_atlas_scraper.adapters import ADAPTERS
from watch_atlas_scraper.breitling_data import FINDER, catalog_page, product
from watch_atlas_scraper.client import Client, FetchError, HostBlocked
from watch_atlas_scraper.curl_transport import CurlTransport
from watch_atlas_scraper.export import save_csv
from watch_atlas_scraper.policy import PermissionDenied
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import State, write_json


class PersonalResearch:
    def require(self, brand, url, purpose='collection'):
        p = urlsplit(url)
        if brand != 'breitling' or purpose != 'collection' or p.scheme != 'https' or p.netloc != 'www.breitling.com' or not p.path.startswith('/us-en/watches/'):
            raise PermissionDenied('This collector is scoped to Breitling US personal catalog research')


def discover(client, folder):
    todo, seen, inventory, pages = [FINDER], set(), {}, {}
    expected = total_pages = None
    while todo:
        url = todo.pop(0)
        if url in seen:
            continue
        seen.add(url)
        meta, body = client.get(url)
        data = catalog_page(body,meta['url'],meta)
        if expected is None:
            expected,total_pages = data['expected'],data['pages']
        if (data['expected'],data['pages']) != (expected,total_pages):
            raise ValueError('Catalog totals changed during discovery; do not claim complete coverage')
        if data['page'] in pages and pages[data['page']]['source_hash'] != data['source_hash']:
            raise ValueError('Conflicting snapshots for one listing page')
        pages[data['page']] = {'url':meta['url'],'source_hash':data['source_hash'],'references':[x['reference'] for x in data['items']]}
        for item in data['items']:
            if item['reference'] in inventory and inventory[item['reference']]['url'] != item['url']:
                raise ValueError('Conflicting URLs for one catalog reference')
            inventory[item['reference']] = item
        for link in data['pagination']:
            if link not in seen and link not in todo:
                todo.append(link)
        print(f'Listing page {data["page"]+1}/{total_pages}: {len(inventory)}/{expected} distinct references',flush=True)
        write_json(folder / 'listing_pages.json',pages)
        write_json(folder / 'inventory.json',list(inventory.values()))
        if len(seen) > total_pages + 1:
            raise ValueError('Pagination exceeded the published page count')
    if set(pages) != set(range(total_pages)) or len(inventory) != expected:
        raise ValueError(f'Incomplete catalog discovery: {len(inventory)}/{expected} references, {len(pages)}/{total_pages} pages')
    return sorted(inventory.values(),key=lambda x:(x['raw_listing_fields'].get('collection',''),x['reference'])),pages


def discover_browser(client, folder, args):
    client.policy.require('breitling',FINDER)
    rules=client.ensure_robots(FINDER)
    if not rules.allowed(FINDER):
        raise PermissionDenied('Catalog is disallowed by robots')
    manifest_path=folder/'rendered_pages'/'manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if not manifest.get('complete') or time.time()-manifest.get('captured_epoch',0)>=86400:
        (folder/'rendered_pages'/'discovery_error.json').unlink(missing_ok=True)
        robots_path=folder/'rendered_pages'/'robots_rules.json'
        write_json(robots_path,{'rules':[{'specificity':n,'allow':allow,'pattern':pattern.pattern} for n,allow,pattern in rules.rules]})
        command=[args.node,str(Path(__file__).with_name('discover_breitling.mjs')),'--output',str(folder),'--delay',str(max(args.delay,rules.delay)), '--robots',str(robots_path)]
        if args.playwright_path: command+=['--playwright',args.playwright_path]
        if args.chrome: command+=['--chrome',args.chrome]
        client._pace('www.breitling.com')
        result=subprocess.run(command,timeout=240)
        client.last['www.breitling.com']=client.clock()
        if result.returncode:
            error_path=folder/'rendered_pages'/'discovery_error.json'
            error=json.loads(error_path.read_text()) if error_path.exists() else {}
            if error.get('robots_denied'):
                client.state.event('robots_denied',error['robots_denied'],'Browser pagination preflight')
                raise PermissionDenied('Browser pagination disallowed by robots')
            if error.get('denied'):
                client.state.block('www.breitling.com','Browser catalog access block')
                client.state.event('circuit_open',FINDER,'Browser catalog access block')
                raise HostBlocked('Browser catalog access block')
            raise FetchError('Browser discovery failed: '+error.get('error','see browser output'))
        manifest=json.loads(manifest_path.read_text())
    inventory,pages={},{}
    for entry in manifest['pages']:
        body=(folder/'rendered_pages'/entry['file']).read_bytes()
        if hashlib.sha256(body).hexdigest()!=entry['sha256']:
            raise ValueError('Rendered catalog snapshot hash mismatch')
        client.policy.require('breitling',entry['url'])
        if not client.ensure_robots(entry['url']).allowed(entry['url']):
            raise PermissionDenied('Rendered catalog page is disallowed by robots')
        data=catalog_page(body,entry['url'],entry)
        if (data['expected'],data['pages']) != (manifest['expected'],manifest['declared_page_count']):
            raise ValueError('Catalog totals changed during browser discovery')
        if data['page'] in pages or data['page'] != entry['page']:
            raise ValueError('Duplicate or mismatched browser page number')
        if [x['reference'] for x in data['items']] != entry['references']:
            raise ValueError('Rendered references disagree with snapshot manifest')
        expected_here=min(manifest['hitsPerPage'],manifest['expected']-data['page']*manifest['hitsPerPage'])
        if len(data['items']) != expected_here:
            raise ValueError('Incomplete rendered page')
        pages[data['page']]={'url':entry['url'],'source_hash':entry['sha256'],'representation':'rendered_dom','file':entry['file'], 'references':entry['references']}
        for item in data['items']:
            if item['reference'] in inventory:
                raise ValueError('Repeated reference across browser catalog pages')
            inventory[item['reference']]=item
    if len(inventory)!=manifest['expected'] or set(pages)!=set(range(manifest['declared_page_count'])):
        raise ValueError('Incomplete rendered catalog')
    (folder/'rendered_pages'/'discovery_error.json').unlink(missing_ok=True)
    write_json(folder/'listing_pages.json',pages)
    write_json(folder/'inventory.json',list(inventory.values()))
    return sorted(inventory.values(),key=lambda x:x['reference']),pages


def save_outputs(state, folder, inventory, pages, errors):
    wanted = {x['reference'] for x in inventory}
    rows = [x for x in state.records(['Breitling']) if x['reference_number'] in wanted]
    rows.sort(key=lambda x:(x['parent_model'],x['reference_number']))
    exports = folder / 'exports'
    exports.mkdir(exist_ok=True)
    save_csv(exports / 'breitling_watches.csv',rows)
    path = exports / 'breitling_watches.jsonl'
    temp = path.with_suffix('.jsonl.tmp')
    temp.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
    temp.replace(path)
    invalid = [{'reference':x['reference_number'],'errors':x['validation_errors']} for x in rows if x['validation_errors']]
    manifest = {
        'captured_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(), 'source':FINDER,
        'usage':'local personal non-commercial research', 'market':'US', 'language':'en',
        'catalog_listing_pages':len(pages), 'watches_expected':len(inventory),'watches_captured':len(rows),
        'reference_coverage_complete':len(rows)==len(inventory) and not errors,
        'detail_errors':errors, 'validation_errors':invalid,
        'collections':dict(Counter(x['parent_model'] for x in rows)),
        'source_field_counts':dict(Counter(x['source_field_count'] for x in rows)),
        'published_price_records':sum(bool(x['price']) for x in rows),
        'source_discrepancy_records':sum(bool(x['source_discrepancies']) for x in rows),
        'missing_fields':{key:sum(not x.get(key) for x in rows) for key in COLUMNS},
        'specification_note':'All selected product fields, variant fields and listing fields are preserved. Coverage refers to the references in the US all-watches listing, not every historical reference or every separately mentioned strap configuration.',
    }
    write_json(folder / 'manifest.json',manifest)
    return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('scraping_runs/breitling-personal-research'))
    p.add_argument('--delay',type=float,default=3)
    p.add_argument('--limit',type=int,help='Pilot size; omit to collect the complete catalog')
    p.add_argument('--reparse',action='store_true',help='Reparse saved pages using the current mapping')
    p.add_argument('--transport',choices=['curl','urllib'],default='curl' if shutil.which('curl') else 'urllib')
    p.add_argument('--discovery',choices=['browser','http'],default='browser')
    p.add_argument('--node',default='node')
    p.add_argument('--playwright-path',help='Optional installed Playwright package path')
    p.add_argument('--chrome',help='Optional installed Chrome executable path')
    args=p.parse_args(argv)
    if args.delay < 3 or (args.limit is not None and args.limit < 1):
        p.error('delay must be >=3 seconds and limit must be positive')
    state=State(args.output)
    client=Client('breitling',ADAPTERS['breitling'],PersonalResearch(),state,args.delay,
                  transport=CurlTransport() if args.transport=='curl' else None)
    errors=[]
    try:
        try:
            inventory,pages=discover_browser(client,args.output,args) if args.discovery=='browser' else discover(client,args.output)
        except (FetchError,PermissionDenied,ValueError,KeyError,subprocess.TimeoutExpired) as error:
            write_json(args.output/'discovery_failure.json',{'source':FINDER,'error':str(error),'reference_coverage_complete':False})
            print('Catalog discovery stopped: '+str(error),file=sys.stderr)
            return 2
        (args.output/'discovery_failure.json').unlink(missing_ok=True)
        captured={x['reference_number'] for x in state.records(['Breitling']) if x.get('product_detail_parsed')}
        remaining=[x for x in inventory if args.reparse or x['reference'] not in captured]
        items=remaining[:args.limit] if args.limit else remaining
        save_outputs(state,args.output,inventory,pages,errors)
        for position,item in enumerate(items,1):
            try:
                meta,body=client.get(item['url'])
                row=product(body,meta['url'],item,meta)
                state.save_record(row)
                print(f'{row["reference_number"]}: {row["source_field_count"]} product fields; {row["currency"]} {row["price"]}',flush=True)
            except (HostBlocked,PermissionDenied) as e:
                errors.append({'reference':item['reference'],'url':item['url'],'error':str(e)})
                print(f'Stopped at access or scope restriction: {e}',flush=True)
                break
            except (FetchError,ValueError,KeyError,StopIteration) as e:
                errors.append({'reference':item['reference'],'url':item['url'],'error':str(e)})
                print(f'{item["reference"]}: {e}',flush=True)
            if not args.reparse or position % 25 == 0:
                save_outputs(state,args.output,inventory,pages,errors)
        manifest=save_outputs(state,args.output,inventory,pages,errors)
        print(json.dumps({'captured':manifest['watches_captured'],'expected':manifest['watches_expected'],
                          'complete':manifest['reference_coverage_complete'],'output':str(args.output/'exports')}),flush=True)
        return 0 if manifest['reference_coverage_complete'] and not manifest['validation_errors'] else 2
    finally:
        state.close()


if __name__=='__main__':
    sys.exit(main())
