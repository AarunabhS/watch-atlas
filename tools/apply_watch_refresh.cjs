/* Apply exact-reference refreshes while retaining archive identities and other brands. */
'use strict';
const fs=require('node:fs');const path=require('node:path');const crypto=require('node:crypto');const assert=require('node:assert/strict');
const model=require('../dist/catalog-model.js');
const normRef=value=>String(value||'').toUpperCase().replace(/[^A-Z0-9]/g,'');
const key=row=>row.brand+'|'+normRef(row.reference_number);
const target=row=>row.is_watch&&['Rolex','Breguet'].includes(row.brand);

function historical(original){
 const row={...original,archive_record_id:original.id,archived_watch_URL:original.watch_URL,
  verification_status:'unverified',source_page_status:'unavailable',watch_URL:'',image_url:'',image_urls:[]};
 row.verification_note='Current manufacturer page unavailable. These are historical specifications.';
 if(row.brand==='Breguet'){
  row.price='';row.price_value=null;row.currency='';row.price_status='unverified_archive';
  const oldModel=/\b(\d{4})\b/.exec(original.specific_model||'');
  if(oldModel&&oldModel[1]!==normRef(original.reference_number).slice(0,4)){
   row.archived_model=original.specific_model;row.archive_identity_status='mismatched';
   for(const field of model.columns)if(!['brand','reference_number'].includes(field))row[field]='';
   row.specific_model='Historical reference '+original.reference_number;row.parent_model='Unverified archive';
   Object.assign(row,{collection_label:'Unverified archive',dial_details:'',bezel_description:'',extra_specs:[],
    diameter_mm:null,diameter_source:'',diameter_note:'',diameter_metric_eligible:false,
    caliber_key:'',movement_family:'Not specified',movement_source:'',gemstones:[],gem_set:false,gemstone_evidence:[],segment:'Time & date'});
   row.verification_note='The archived model and reference disagree. Details are withheld until verified.';
  }
 }else if(/leather|elastomer/i.test(row.case_material||''))row.case_material='';
 row.coverage=Math.round(model.coreFields.filter(f=>row[f]).length/model.coreFields.length*100);
 return row;
}

function mergeRecords(current,baseline,captures,proofs,datasets){
 const originals=new Map(baseline.filter(target).map(r=>[key(r),r]));
 assert.equal(originals.size,baseline.filter(target).length,'Ambiguous archive reference');
 const verified=new Map();
 for(const capture of captures){
  const k=key(capture);assert.ok(!verified.has(k),'Duplicate refreshed reference '+k);
  const image=capture.image_URL||capture.image_url;if(image)assert.equal(proofs[image]?.status,'working','Unverified image '+k);
  else assert.equal(capture.image_status,'not_published_by_source','Unexplained missing image '+k);
  const dataset=datasets.find(d=>d.brand===capture.brand);assert.ok(dataset,'Unknown refresh brand');
  const normalized=model.normalize(capture,dataset);const original=originals.get(k);
  if(capture.brand==='Rolex')normalized.caliber_key=normalized.caliber.replace(/,\s*Manufacture Rolex$/i,'').trim().toUpperCase();
  if(capture.brand==='Breguet')normalized.caliber_key=normalized.caliber.replace(/\s/g,'').replace(/[,/]/g,'.').toUpperCase();
  // Preserve fields outside the 40-column schema that users already saw.
  for(const field of ['dial_details','bezel_description'])if(capture[field])normalized[field]=capture[field];
  normalized.verification_status='verified';normalized.source_page_status='available';
  if(original){normalized.id=original.id;normalized.archive_record_id=original.id;normalized.archived_watch_URL=original.watch_URL;}
  verified.set(k,normalized);
 }
 const originalIds=new Set([...originals.values()].map(r=>r.id));
 // Reject someone else's concurrent edits to the requested brands, but allow unrelated imports.
 for(const r of current.filter(target))assert.ok(originalIds.has(r.id)||r.source_dataset==='breguet-official-refresh','Unexpected target record '+r.id);
 const replacements=new Map([...originals].map(([k,r])=>[r.id,verified.get(k)||historical(r)]));
 const rows=current.filter(r=>!target(r)||originalIds.has(r.id)).map(r=>target(r)?replacements.get(r.id):r);
 rows.push(...[...verified].filter(([k])=>!originals.has(k)).map(([,r])=>r));
 assert.equal(new Set(rows.map(r=>r.id)).size,rows.length,'Duplicate Atlas ID');
 for(const id of originalIds)assert.ok(rows.some(r=>r.id===id),'Lost archive ID '+id);
 assert.deepEqual(rows.filter(r=>!target(r)),current.filter(r=>!target(r)),'Unrelated catalog changed');
 return rows;
}

function summaries(data){
 const watches=data.records.filter(r=>r.is_watch);
 const names=[...new Set([...data.brandOrder,...watches.map(r=>r.brand)])].filter(n=>watches.some(r=>r.brand===n));
 for(const brand of data.brands){const rows=data.records.filter(r=>r.brand===brand.name);brand.records=rows.length;
  if(rows.length){brand.coverage=Math.round(rows.reduce((a,r)=>a+r.coverage,0)/rows.length);brand.families=new Set(rows.map(r=>r.parent_model)).size;brand.fields=Object.fromEntries(data.coreFields.map(k=>[k,rows.filter(r=>r[k]).length]));}
  if(['Rolex','Breguet'].includes(brand.name))brand.status='Official refresh + unverified archive';
 }
 data.insights={categories:model.categories,overall:model.summarizeWatches(watches,'All watchmakers'),brands:names.map(n=>model.summarizeWatches(watches.filter(r=>r.brand===n),n)),segments:model.categories.map(n=>model.summarizeWatches(watches.filter(r=>r.segment===n),n)),excludedDiameter:watches.filter(r=>r.diameter_mm===null||r.diameter_metric_eligible===false).length,nonWatchItems:data.records.filter(r=>!r.is_watch).length};
 const counts={};for(const r of watches)counts[r.collection_label]=(counts[r.collection_label]||0)+1;
 data.collections=Object.entries(counts).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,8).map(([name,count])=>({name,count}));
 data.stats={...data.archiveStats,records:data.records.length,sourceRows:data.archiveStats.sourceRows+data.catalogImports.reduce((a,d)=>a+d.rows,0),preparedBrands:names.length,exploredBrands:data.brands.filter(b=>!b.records).length,families:new Set(watches.map(r=>r.brand+'|'+r.parent_model)).size,coverage:Math.round(watches.reduce((a,r)=>a+data.coreFields.filter(k=>r[k]).length,0)/(watches.length*data.coreFields.length)*100),wristwatches:watches.filter(r=>r.watch_kind!=='Pocket watch').length,pocketWatches:watches.filter(r=>r.watch_kind==='Pocket watch').length};
}

function main(){
 const root=path.resolve(__dirname,'..');const folder=path.resolve(root,process.argv[2]||'scraping_runs/rolex-breguet-refresh-2026-10-05');
 const read=p=>JSON.parse(fs.readFileSync(path.join(folder,p),'utf8'));
 const baseline=read('baseline.json');const current=JSON.parse(fs.readFileSync(path.join(root,'dist/data.json'),'utf8'));
 const breguet=read('breguet/manifest.json');assert.equal(breguet.pages_captured,breguet.pages_expected);assert.equal(breguet.reference_conflicts.length,0);
 assert.ok(breguet.needs_review.every(r=>r.reviewed_exclusion),'Breguet pages still need review');
 const captures=[];const datasets=[];const proofs={...read('rolex-images/link_results.json'),...read('breguet-images/link_results.json')};
 for(const brand of ['Rolex','Breguet']){
  const slug=brand.toLowerCase();const file=path.join(folder,slug,'exports',slug+'_watches.jsonl');const body=fs.readFileSync(file,'utf8');
  const rows=body.trim().split('\n').map(line=>JSON.parse(line));
  assert.ok(rows.every(r=>r.brand===brand&&r.product_detail_parsed&&!r.validation_errors.length));
  for(const row of rows){if(row.image_URL)assert.equal(proofs[row.image_URL]?.status,'working','Image validation incomplete');else assert.equal(row.image_status,'not_published_by_source');const source=path.join(folder,slug,'snapshots',row.source_hash);assert.equal(crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),row.source_hash,'Source hash mismatch');}
  const dates=[...new Set(rows.map(r=>model.normalize(r,{id:'check',label:'check'}).captured_date))].sort();
  datasets.push({id:slug+'-official-refresh',brand,slug,market:'Global',label:brand+' official reference refresh · October 2026',rows:rows.length,file:path.relative(root,file),sha256:crypto.createHash('sha256').update(body).digest('hex'),source:brand==='Rolex'?'https://www.rolex.com/watches':'https://www.breguet.com/en/find-a-watch',captured_dates:dates,captured_date:dates[0],replaces_archive_fields:true});captures.push(...rows);
 }
 current.records=mergeRecords(current.records,baseline.records,captures,proofs,datasets);
 const ids=new Set(datasets.map(d=>d.id));current.catalogImports=[...current.catalogImports.filter(d=>!ids.has(d.id)),...datasets];
 current.sources=[...current.sources.filter(d=>!ids.has(d.id)),...datasets];
 summaries(current);
 const report={existing_ids_preserved:baseline.records.filter(target).length,verified:datasets.map(d=>({brand:d.brand,rows:d.rows})),historical_unverified:current.records.filter(r=>target(r)&&r.verification_status==='unverified').map(r=>({brand:r.brand,reference:r.reference_number,id:r.id,identity_status:r.archive_identity_status||'not_currently_verified'})),added_breguet:current.records.filter(r=>r.source_dataset==='breguet-official-refresh'&&!r.archive_record_id).length,watch_count:current.insights.overall.count};
 fs.writeFileSync(path.join(folder,'integration.json'),JSON.stringify(report,null,2)+'\n');
 const destination=path.join(root,'dist/data.json');fs.writeFileSync(destination+'.tmp',JSON.stringify(current));fs.renameSync(destination+'.tmp',destination);
 console.log(JSON.stringify({...report,historical_unverified:report.historical_unverified.length},null,2));
}
if(require.main===module)main();else module.exports={mergeRecords,historical,summaries};
