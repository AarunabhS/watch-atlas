/* Import completed official catalogs without changing the preserved archive. */
'use strict';
const fs=require('node:fs');const path=require('node:path');const crypto=require('node:crypto');
const model=require('../dist/catalog-model.js');
const root=path.resolve(__dirname,'..');
const target=path.join(root,'dist/data.json');
const data=JSON.parse(fs.readFileSync(target,'utf8'));
const registry=[
 {id:'patek-official-catalog',brand:'Patek Philippe',slug:'patek',label:'Patek Philippe official catalog · 2 October 2026'},
 {id:'breitling-official-catalog',brand:'Breitling',slug:'breitling',label:'Breitling US official catalog · 2 October 2026'},
 {id:'jlc-official-catalog',brand:'Jaeger-LeCoultre',slug:'jlc',label:'Jaeger-LeCoultre US official catalog'},
 {id:'omega-official-catalog',brand:'Omega',slug:'omega',folder:'omega-us-capture',label:'Omega US official catalog'},
 {id:'tudor-official-catalog',brand:'Tudor',slug:'tudor',folder:'tudor-in-capture',label:'Tudor India official catalog'},
 {id:'iwc-official-catalog',brand:'IWC',slug:'iwc',folder:'iwc-us-capture',label:'IWC US official catalog'}
];
const requested=process.argv.slice(2);
if(requested.some(x=>!registry.some(d=>d.slug===x)))throw new Error('Unknown catalog; choose '+registry.map(d=>d.slug).join(', '));
const datasets=registry.filter(x=>(requested.length?requested:['patek','breitling']).includes(x.slug));
const imported=[];
for(const dataset of datasets){
 const folder=path.join(root,'scraping_runs',dataset.folder||dataset.slug+'-personal-research');
 const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json'),'utf8'));
 if(!manifest.reference_coverage_complete||manifest.detail_errors.length||manifest.validation_errors.length)throw new Error(dataset.brand+' catalog is incomplete');
 const file=path.join(folder,'exports',dataset.slug+'_watches.jsonl');
 const body=fs.readFileSync(file,'utf8');
 const rows=body.trim().split('\n').map(line=>JSON.parse(line));
 if(rows.length!==manifest.watches_expected||rows.length!==manifest.watches_captured||rows.some(r=>r.brand!==dataset.brand||manifest.market&&r.market!==manifest.market))throw new Error('Source catalog count, market or identity mismatch');
 dataset.market=manifest.market||rows[0].market;
 if(!dataset.label.includes('October'))dataset.label+=' · '+new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',day:'numeric',month:'long',year:'numeric'}).format(new Date(rows[0].captured_at));
 const normalized=rows.map(row=>model.normalize(row,dataset));
 if(new Set(normalized.map(r=>r.id)).size!==normalized.length)throw new Error('Duplicate source identity');
 imported.push(...normalized);
 dataset.rows=normalized.length;dataset.file=path.relative(root,file);
 dataset.sha256=crypto.createHash('sha256').update(body).digest('hex');
 dataset.source=manifest.source;dataset.captured_dates=[...new Set(normalized.map(r=>r.captured_date))].sort();dataset.captured_date=dataset.captured_dates[0];dataset.captured_date_range=dataset.captured_dates.length>1?dataset.captured_dates[0]+' to '+dataset.captured_dates.at(-1):dataset.captured_date;
 if(dataset.captured_dates.length>1){dataset.label=dataset.label.split(' · ')[0]+' · '+normalized.find(r=>r.captured_date===dataset.captured_dates[0]).captured_label+' to '+normalized.find(r=>r.captured_date===dataset.captured_dates.at(-1)).captured_label;for(const row of normalized)row.sources=[dataset.label];}
}
const ids=new Set(datasets.map(x=>x.id));
const archive=data.records.filter(r=>!ids.has(r.source_dataset));
data.records=[...archive,...imported];
if(new Set(data.records.map(r=>r.id)).size!==data.records.length)throw new Error('Duplicate catalog ID');
data.catalogImports=[...(data.catalogImports||[]).filter(x=>!ids.has(x.id)),...datasets];
data.brandOrder=['Jaeger-LeCoultre','Omega','Patek Philippe','Breitling','Tudor','IWC','Audemars Piguet','H. Moser & Cie.','Bulgari','Breguet','Rolex'];
data.showcaseBrands=data.brandOrder.filter(name=>data.records.some(r=>r.brand===name&&r.is_watch&&r.image_url)).slice(0,3);
data.snapshotLabel='2023–2024 archive + October 2026 catalogs';
data.archiveStats=data.archiveStats||{...data.stats};
const watches=data.records.filter(r=>r.is_watch);
for(const dataset of datasets){
 let brand=data.brands.find(x=>x.name===dataset.brand);
 if(!brand){brand={name:dataset.brand};data.brands.push(brand);}
 Object.assign(brand,{status:'Official catalog snapshot',captured_date:dataset.captured_date});
}
for(const brand of data.brands){
 const rows=data.records.filter(r=>r.brand===brand.name);brand.records=rows.length;
 if(rows.length){brand.coverage=Math.round(rows.reduce((a,r)=>a+r.coverage,0)/rows.length);brand.families=new Set(rows.map(r=>r.parent_model)).size;brand.fields=Object.fromEntries(data.coreFields.map(k=>[k,rows.filter(r=>r[k]).length]));}
}
const names=[...new Set([...data.brandOrder,...watches.map(r=>r.brand)])].filter(name=>watches.some(r=>r.brand===name));
data.insights={categories:model.categories,overall:model.summarizeWatches(watches,'All watchmakers'),brands:names.map(name=>model.summarizeWatches(watches.filter(r=>r.brand===name),name)),segments:model.categories.map(name=>model.summarizeWatches(watches.filter(r=>r.segment===name),name)),excludedDiameter:watches.filter(r=>r.diameter_mm===null||r.diameter_metric_eligible===false).length,nonWatchItems:data.records.filter(r=>!r.is_watch).length};
const counts={};for(const row of watches)counts[row.collection_label]=(counts[row.collection_label]||0)+1;
data.collections=Object.entries(counts).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,8).map(([name,count])=>({name,count}));
data.sources=data.sources.filter(x=>!ids.has(x.id));data.sources.push(...datasets);
data.stats={...data.archiveStats,records:data.records.length,sourceRows:data.archiveStats.sourceRows+data.catalogImports.reduce((sum,x)=>sum+x.rows,0),preparedBrands:names.length,exploredBrands:data.brands.filter(b=>!b.records).length,families:new Set(watches.map(r=>r.brand+'|'+r.parent_model)).size,coverage:Math.round(watches.reduce((a,r)=>a+data.coreFields.filter(k=>r[k]).length,0)/(watches.length*data.coreFields.length)*100),wristwatches:watches.filter(r=>r.watch_kind!=='Pocket watch').length,pocketWatches:watches.filter(r=>r.watch_kind==='Pocket watch').length};
fs.writeFileSync(target+'.tmp',JSON.stringify(data));fs.renameSync(target+'.tmp',target);
console.log(JSON.stringify({added:imported.length,watches:watches.length,watchmakers:names.length,wristwatches:data.stats.wristwatches,pocketWatches:data.stats.pocketWatches}));

const finderBuild=require('node:child_process').spawnSync(process.execPath,[path.join(root,'tools/build-finder-catalog.mjs')],{stdio:'inherit'});if(finderBuild.status!==0)throw new Error('Catalog imported, but the derived Finder index could not rebuild. Run tools/build-finder-catalog.mjs.');
