"""Offline source/export verification of the Jaeger-LeCoultre capture."""
import argparse,csv,hashlib,json
from pathlib import Path
from watch_atlas_scraper.jlc_data import FINDER,catalog,product,editorial_watch
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import write_json

def validate(folder):
 folder=Path(folder);cache=json.loads((folder/'browser_cache.json').read_text());manifest=json.loads((folder/'manifest.json').read_text())
 def snapshot(url):
  meta=cache[url];body=(folder/'snapshots'/meta['sha256']).read_bytes()
  if hashlib.sha256(body).hexdigest()!=meta['sha256']:raise ValueError('Source hash mismatch')
  return meta,body
 inventory_map={};listing_count=0;excluded=[];verified_listings=0;editorial=[]
 for listing in manifest['catalog_listing_pages']:
  meta,body=snapshot(listing['url']);items,declared,exceptions=catalog(body)
  if declared!=listing['declared_count'] or meta['sha256']!=listing['source_hash']:raise ValueError('Listing manifest mismatch')
  if listing['url']==FINDER:listing_count=declared
  verified_listings+=1
  for item in items:
   if item['reference'] not in inventory_map:inventory_map[item['reference']]={**item,'discovered_in':[]}
   inventory_map[item['reference']]['discovered_in'].append(listing['url'])
  for item in exceptions:
   if '/news/' in item['url']:editorial.append(item)
   else:excluded.append(item)
 for item in editorial:
  _,body=snapshot(item['url']);resolved=editorial_watch(body,item)
  if resolved:inventory_map.setdefault(resolved['reference'],{**resolved,'discovered_in':[FINDER]})
  else:excluded.append(item)
 inventory=list(inventory_map.values())
 if inventory!=json.loads((folder/'inventory.json').read_text()):raise ValueError('Inventory/source listings disagree')
 rows=[json.loads(x) for x in (folder/'exports/jlc_watches.jsonl').read_text().splitlines()]
 with (folder/'exports/jlc_watches.csv').open(newline='') as stream:
  reader=csv.DictReader(stream)
  if reader.fieldnames!=COLUMNS:raise ValueError('CSV column mismatch')
  csvrows=list(reader)
 if not manifest['reference_coverage_complete'] or manifest['detail_errors'] or manifest['validation_errors']:raise ValueError('Incomplete capture')
 if set(x['reference'] for x in inventory)!=set(x['reference_number'] for x in rows) or len(rows)!=len(inventory):raise ValueError('Reference set mismatch')
 if len(rows)!=len(csvrows):raise ValueError('CSV row count mismatch')
 byref={x['reference']:x for x in inventory}
 for row,csvrow in zip(rows,csvrows):
  item=byref[row['reference_number']];meta,body=snapshot(item['url']);parsed=product(body,item['url'],item,meta)
  if parsed!=row:raise ValueError('Saved product/source disagreement: '+row['reference_number'])
  if any(csvrow[k]!=row[k] for k in COLUMNS):raise ValueError('CSV and JSONL disagreement')
 result={'valid':True,'watches':len(rows),'listing_results':listing_count,'excluded_cards':list({x['url']:x for x in excluded}.values()),'listing_pages_verified':verified_listings,'resolved_editorial_watches':sum(bool(r.get('raw_listing_fields',{}).get('reference_source')) for r in rows),'csv_columns':len(COLUMNS),'source_snapshots_verified':len(rows)+verified_listings,'source_hashes_verified':True,'csv_jsonl_source_agreement':True,'published_prices':sum(bool(r['price']) for r in rows),'marketing_templates':sum(r['template']=='marketing_product' for r in rows),'source_discrepancy_records':sum(bool(r['source_discrepancies']) for r in rows)}
 write_json(folder/'validation.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('scraping_runs/jlc-personal-research'));args=p.parse_args();print(json.dumps(validate(args.output),indent=2))
