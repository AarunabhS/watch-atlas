"""Sequential Jaeger-LeCoultre US catalog collection in a normal headless browser."""
import argparse,json,shutil,subprocess,sys,hashlib
from collections import Counter
from pathlib import Path
from watch_atlas_scraper.jlc_data import ORIGIN,FINDER,catalog,product,editorial_watch
from watch_atlas_scraper.robots import Robots
from watch_atlas_scraper.state import write_json
from watch_atlas_scraper.export import save_csv
from watch_atlas_scraper.schema import COLUMNS

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('scraping_runs/jlc-personal-research'));p.add_argument('--node',default=shutil.which('node') or 'node');p.add_argument('--playwright-path');p.add_argument('--chrome');p.add_argument('--delay',type=float,default=3);p.add_argument('--limit',type=int);p.add_argument('--offline',action='store_true');a=p.parse_args(argv)
 if a.delay<3 or a.limit is not None and a.limit<1:p.error('Delay >=3 and positive limit required')
 folder=a.output;folder.mkdir(parents=True,exist_ok=True);cachefile=folder/'browser_cache.json'
 def load():return json.loads(cachefile.read_text()) if cachefile.exists() else {}
 def body(meta):
  content=(folder/'snapshots'/meta['sha256']).read_bytes()
  if hashlib.sha256(content).hexdigest()!=meta['sha256']:raise ValueError('Snapshot integrity error')
  return content
 def browse(queue,rules=None):
  write_json(folder/'queue.json',queue);command=[a.node,str(Path(__file__).with_name('browser_snapshots.mjs')),'--output',str(folder),'--queue',str(folder/'queue.json'),'--origin',ORIGIN,'--delay',str(max(a.delay,rules.delay if rules else 0))]
  if rules:
   write_json(folder/'robots_rules.json',{'rules':[{'specificity':n,'allow':allow,'pattern':pattern.pattern} for n,allow,pattern in rules.rules]});command+=['--robots',str(folder/'robots_rules.json')]
  if a.playwright_path:command+=['--playwright',a.playwright_path]
  if a.chrome:command+=['--chrome',a.chrome]
  return subprocess.run(command).returncode
 robots_url=ORIGIN+'/robots.txt'
 if not a.offline and browse([{'url':robots_url}]):return 2
 cache=load();rules=Robots(body(cache[robots_url]).decode(),'WatchAtlasCatalogBot')
 if not rules.allowed(FINDER):raise ValueError('Catalog denied by robots')
 listing_urls=[FINDER,ORIGIN+'/us-en/watches/calibre-101',ORIGIN+'/us-en/watches/high-complication',ORIGIN+'/us-en/watches/hybris']
 if not a.offline and browse([{'url':url,'selector':'[data-cy="mixed-grid-products-count"]'} for url in listing_urls],rules):return 2
 cache=load();inventory_map={};listing_pages=[];excluded=[];editorial=[]
 for listing in listing_urls:
  items,declared,exceptions=catalog(body(cache[listing]));listing_pages.append({'url':listing,'declared_count':declared,'source_hash':cache[listing]['sha256'],'watch_reference_cards':len(items),'exceptions':exceptions})
  for item in items:
   if item['reference'] not in inventory_map:inventory_map[item['reference']]={**item,'discovered_in':[]}
   inventory_map[item['reference']]['discovered_in'].append(listing)
  for item in exceptions:
   if '/news/' in item['url']:editorial.append(item)
   else:excluded.append(item)
 if not a.offline and browse([{'url':x['url'],'selector':'main'} for x in editorial],rules):return 2
 cache=load()
 for item in editorial:
  resolved=editorial_watch(body(cache[item['url']]),item) if item['url'] in cache else None
  if resolved:inventory_map.setdefault(resolved['reference'],{**resolved,'discovered_in':[FINDER]})
  else:excluded.append(item)
 excluded=list({x['url']:x for x in excluded}.values());inventory=list(inventory_map.values());expected=len(inventory);listing_total=listing_pages[0]['declared_count'];write_json(folder/'inventory.json',inventory);write_json(folder/'listing_pages.json',listing_pages)
 queue=[{'url':x['url'],'selector':'script[type="application/ld+json"]'} for x in inventory if x['url'] not in cache]
 if a.limit:queue=queue[:a.limit]
 if not a.offline: browse(queue,rules)
 cache=load();rows=[];errors=[]
 for item in inventory:
  if item['url'] not in cache:continue
  try:
   row=product(body(cache[item['url']]),item['url'],item,cache[item['url']]);rows.append(row)
   if row['validation_errors']:errors.append({'reference':row['reference_number'],'errors':row['validation_errors']})
  except (ValueError,KeyError,IndexError) as e:errors.append({'reference':item['reference'],'error':str(e)})
 rows.sort(key=lambda r:(r['parent_model'],r['reference_number']));exports=folder/'exports';exports.mkdir(exist_ok=True);save_csv(exports/'jlc_watches.csv',rows)
 temp=exports/'jlc_watches.jsonl.tmp';temp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));temp.replace(exports/'jlc_watches.jsonl')
 manifest={'source':FINDER,'listing_total':listing_total,'catalog_listing_pages':listing_pages,'excluded_listing_cards':excluded,'market':'US','language':'en','watches_expected':expected,'watches_captured':len(rows),'reference_coverage_complete':len(rows)==expected and not errors,'detail_errors':errors,'validation_errors':[{'reference':r['reference_number'],'errors':r['validation_errors']} for r in rows if r['validation_errors']],'collections':dict(Counter(r['parent_model'] for r in rows)),'published_price_records':sum(bool(r['price']) for r in rows),'missing_fields':{k:sum(not r[k] for r in rows) for k in COLUMNS},'source_field_counts':dict(Counter(r['source_field_count'] for r in rows)),'scope':'All watch references in the published US all-watches, Calibre 101, high-complication and Hybris listings, plus watch-identified editorial product pages. Atmos clocks and historical Collectibles are excluded. Raw product, technical, calibre, accordion and listing values retained.'}
 write_json(folder/'manifest.json',manifest);print(json.dumps(manifest),flush=True);return 0 if manifest['reference_coverage_complete'] else 2
if __name__=='__main__':sys.exit(main())
