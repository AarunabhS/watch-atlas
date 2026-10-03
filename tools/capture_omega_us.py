"""Focused Omega US collector. Sequential public catalogue and watch page downloads."""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from zoneinfo import ZoneInfo
from watch_atlas_scraper.adapters import ADAPTERS
from watch_atlas_scraper.client import Client,FetchError,HostBlocked
from watch_atlas_scraper.curl_transport import CurlTransport
from watch_atlas_scraper.export import save_csv
from watch_atlas_scraper.omega_us_data import FINDER,ORIGIN,PRODUCT_PATH,COLLECTION_PATH,catalog_page,collection_roots,finder_totals,product
from watch_atlas_scraper.policy import PermissionDenied
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import State,write_json


class SavedPages:
    """A cache-only reader for reprocessing a completed capture without network."""
    def __init__(self,state): self.state=state
    def get(self,url):
        result=self.state.cached(url)
        if result is None: raise FetchError('No saved snapshot: '+url)
        return result


class PersonalResearch:
    def require(self,brand,url,purpose='collection'):
        p=urlsplit(url)
        allowed=p.path=='/en-us/watchfinder' and not p.query
        allowed |= bool(PRODUCT_PATH.fullmatch(p.path)) and not p.query
        allowed |= bool(COLLECTION_PATH.fullmatch(p.path)) and (not p.query or
            (set(parse_qs(p.query))=={'p'} and len(parse_qs(p.query)['p'])==1 and parse_qs(p.query)['p'][0].isdigit()))
        if brand!='omega' or purpose!='collection' or p.scheme!='https' or p.netloc!='www.omegawatches.com' or not allowed:
            raise PermissionDenied('This collector is scoped to Omega US public watch catalogue pages')


def discover(client,folder):
    finder_meta,body=client.get(FINDER);expected,groups=finder_totals(body);roots=collection_roots(body)
    if 'Specialities' in groups:
        roots.extend([ORIGIN+'/en-us/watches/specialities/olympic-pocket-watch/catalog',ORIGIN+'/en-us/watches/specialities/olympic-1932-chrono-chime/catalog'])
    inventory,pages,collections={},{},{}
    for root in roots:
        url,seen,local,published_total=root,set(),{},None
        while url:
            if url in seen: raise ValueError('Pagination loop')
            seen.add(url);meta,body=client.get(url);data=catalog_page(body,meta['url'],meta)
            if published_total is None: published_total=data['expected']
            if data['expected']!=published_total: raise ValueError('Collection total changed during discovery')
            if not set(local).issubset({x['reference'] for x in data['items']}): raise ValueError('Cumulative page dropped earlier references')
            for item in data['items']:
                if item['reference'] in inventory and inventory[item['reference']]['url']!=item['url']: raise ValueError('Conflicting URLs for one reference')
                local[item['reference']]=item;inventory[item['reference']]=item
            pages[url]={'source_hash':data['source_hash'],'page':data['page'],'expected':data['expected'],'references':list(local)}
            print(f'{root.split("/watches/")[1]} page {data["page"]}: {len(local)}/{published_total}; {len(inventory)}/{expected} distinct watches',flush=True)
            write_json(folder/'listing_pages.json',pages);write_json(folder/'inventory.json',list(inventory.values()));url=data['next']
        if len(local)!=published_total: raise ValueError('Incomplete collection')
        collections[root]=published_total
    grouped={}
    for root,count in collections.items():
        family=root.split('/watches/')[1].split('/')[0];grouped[family]=grouped.get(family,0)+count
    if len(inventory)!=expected or grouped!={name.lower().replace(' ','-'):n for name,n in groups.items()}:
        raise ValueError(f'Collection totals disagree with finder: {len(inventory)}/{expected}')
    write_json(folder/'discovery.json',{'expected':expected,'finder_source_hash':finder_meta['sha256'],'finder_collections':groups,'collection_totals':collections,'complete':True})
    return sorted(inventory.values(),key=lambda x:x['reference']),pages


def save_outputs(state,folder,inventory,pages,errors):
    wanted={x['reference'] for x in inventory}
    rows=sorted((x for x in state.records(['Omega']) if x['reference_number'] in wanted),key=lambda x:(x['parent_model'],x['reference_number']))
    exports=folder/'exports';exports.mkdir(exist_ok=True);save_csv(exports/'omega_watches.csv',rows)
    path=exports/'omega_watches.jsonl';temp=path.with_suffix('.jsonl.tmp')
    temp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8');temp.replace(path)
    manifest={'captured_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),'source':FINDER,'market':'US','language':'en',
        'usage':'local personal non-commercial research','catalog_listing_pages':len(pages),'watches_expected':len(inventory),'watches_captured':len(rows),
        'reference_coverage_complete':len(rows)==len(inventory) and not errors,'detail_errors':errors,
        'validation_errors':[{'reference':x['reference_number'],'errors':x['validation_errors']} for x in rows if x['validation_errors']],
        'collections':dict(Counter(x['parent_model'] for x in rows)),'published_price_records':sum(bool(x['price']) for x in rows),
        'technical_field_counts':dict(Counter(x['source_field_count'] for x in rows)),'missing_fields':{key:sum(not x.get(key) for x in rows) for key in COLUMNS},
        'specification_note':'Coverage is the current US finder and its collection catalogues. Full source HTML, technical fields, selected JSON-LD, headings, feature labels, movement description, image links and selected tracking data are retained. Related watches are kept separately. Undisclosed fields stay blank.'}
    write_json(folder/'manifest.json',manifest);return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('scraping_runs/omega-us-capture'))
    p.add_argument('--delay',type=float,default=3);p.add_argument('--limit',type=int);p.add_argument('--reparse',action='store_true')
    p.add_argument('--offline',action='store_true',help='Read saved snapshots only, with no network requests')
    args=p.parse_args(argv)
    if args.delay<3 or (args.limit is not None and args.limit<1): p.error('delay must be >=3 seconds; limit must be positive')
    state=State(args.output)
    client=SavedPages(state) if args.offline else Client('omega',ADAPTERS['omega'],PersonalResearch(),state,args.delay,transport=CurlTransport())
    errors=[]
    try:
        try: inventory,pages=discover(client,args.output)
        except (FetchError,PermissionDenied,ValueError,KeyError) as error:
            write_json(args.output/'discovery_failure.json',{'source':FINDER,'error':str(error),'reference_coverage_complete':False});print('Discovery stopped: '+str(error),file=sys.stderr);return 2
        (args.output/'discovery_failure.json').unlink(missing_ok=True)
        captured={x['reference_number'] for x in state.records(['Omega']) if x.get('product_detail_parsed')}
        remaining=[x for x in inventory if args.reparse or x['reference'] not in captured];items=remaining[:args.limit] if args.limit else remaining
        save_outputs(state,args.output,inventory,pages,errors)
        for position,item in enumerate(items,1):
            try:
                meta,body=client.get(item['url']);row=product(body,meta['url'],item,meta);state.save_record(row)
                print(f'{row["reference_number"]}: {row["source_field_count"]} technical fields; {row["currency"]} {row["price"]}',flush=True)
            except (HostBlocked,PermissionDenied) as error:
                errors.append({'reference':item['reference'],'url':item['url'],'error':str(error)});break
            except (FetchError,ValueError,KeyError,IndexError) as error:
                errors.append({'reference':item['reference'],'url':item['url'],'error':str(error)});print(f'{item["reference"]}: {error}',flush=True)
            if position%10==0: save_outputs(state,args.output,inventory,pages,errors)
        result=save_outputs(state,args.output,inventory,pages,errors)
        print(json.dumps({'captured':result['watches_captured'],'expected':result['watches_expected'],'complete':result['reference_coverage_complete'],'output':str(args.output/'exports')}),flush=True)
        return 0 if result['reference_coverage_complete'] and not result['validation_errors'] else 2
    finally: state.close()


if __name__=='__main__': sys.exit(main())
