/* Import completed official catalogs without changing the preserved archive. */
'use strict';
const fs=require('node:fs');const path=require('node:path');const crypto=require('node:crypto');
const model=require('../dist/catalog-model.js');
const root=path.resolve(__dirname,'..');
const target=path.join(root,'dist/data.json');
const data=JSON.parse(fs.readFileSync(target,'utf8'));
const datasets=[
 {id:'patek-official-catalog',brand:'Patek Philippe',slug:'patek',label:'Patek Philippe official catalog · 2 October 2026'},
 {id:'breitling-official-catalog',brand:'Breitling',slug:'breitling',label:'Breitling US official catalog · 2 October 2026'}
];
const imported=[];
for(const dataset of datasets){
 const folder=path.join(root,'scraping_runs',dataset.slug+'-personal-research');
 const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json'),'utf8'));
 if(!manifest.reference_coverage_complete||manifest.detail_errors.length||manifest.validation_errors.length)throw new Error(dataset.brand+' catalog is incomplete');
 const file=path.join(folder,'exports',dataset.slug+'_watches.jsonl');
 const body=fs.readFileSync(file,'utf8');
 const rows=body.trim().split('\n').map(line=>JSON.parse(line));
 if(rows.length!==manifest.watches_expected||rows.some(r=>r.brand!==dataset.brand))throw new Error('Source catalog count or identity mismatch');
 const normalized=rows.map(row=>model.normalize(row,dataset));
 if(new Set(normalized.map(r=>r.id)).size!==normalized.length)throw new Error('Duplicate source identity');
 imported.push(...normalized);
 dataset.rows=normalized.length;dataset.file=path.relative(root,file);
 dataset.sha256=crypto.createHash('sha256').update(body).digest('hex');
 dataset.source=manifest.source;dataset.captured_date=normalized[0].captured_date;
}
const ids=new Set(datasets.map(x=>x.id));
const archive=data.records.filter(r=>!ids.has(r.source_dataset));
data.records=[...archive,...imported];
if(new Set(data.records.map(r=>r.id)).size!==data.records.length)throw new Error('Duplicate catalog ID');
data.catalogImports=datasets;
data.brandOrder=['Patek Philippe','Breitling','Audemars Piguet','H. Moser & Cie.','Bulgari','Breguet','Rolex'];
data.showcaseBrands=['Patek Philippe','Breitling','Audemars Piguet'];
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
data.stats={...data.archiveStats,records:data.records.length,sourceRows:data.archiveStats.sourceRows+imported.length,preparedBrands:names.length,exploredBrands:data.brands.filter(b=>!b.records).length,families:new Set(watches.map(r=>r.brand+'|'+r.parent_model)).size,coverage:Math.round(watches.reduce((a,r)=>a+data.coreFields.filter(k=>r[k]).length,0)/(watches.length*data.coreFields.length)*100),wristwatches:watches.filter(r=>r.watch_kind!=='Pocket watch').length,pocketWatches:watches.filter(r=>r.watch_kind==='Pocket watch').length};
fs.writeFileSync(target+'.tmp',JSON.stringify(data));fs.renameSync(target+'.tmp',target);
console.log(JSON.stringify({added:imported.length,watches:watches.length,watchmakers:names.length,wristwatches:data.stats.wristwatches,pocketWatches:data.stats.pocketWatches}));
