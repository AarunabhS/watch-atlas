/* Rebuild the derived search index without mutating raw data or stable record IDs. */
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {DatabaseSync} from 'node:sqlite';
import M from '../dist/finder-model.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export function buildCatalog(data,{database,seed}={}){
 const db=database||new DatabaseSync(':memory:');const schema=fs.readFileSync(path.join(root,'backend/migrations/0001_watch_finder.sql'),'utf8');db.exec('DROP TABLE IF EXISTS finder_fts; DROP TABLE IF EXISTS finder_facets; DROP TABLE IF EXISTS finder_prices; DROP TABLE IF EXISTS finder_watches; DROP TABLE IF EXISTS finder_meta;');db.exec(schema);
 const sql=[schema,'DELETE FROM finder_fts;','DELETE FROM finder_facets;','DELETE FROM finder_prices;','DELETE FROM finder_watches;','DELETE FROM finder_meta;'];
 const quote=x=>x==null?'NULL':typeof x==='number'?String(x):"'"+String(x).replace(/'/g,"''")+"'";
 const insert=(table,values)=>{db.prepare(`INSERT INTO ${table} VALUES (${values.map(()=>'?').join(',')})`).run(...values);if(seed)sql.push(`INSERT INTO ${table} VALUES (${values.map(quote).join(',')});`);};
 db.exec('BEGIN');db.exec(sql.slice(1).join('\n'));
 const rows=data.records.filter(r=>r.is_watch),vocabulary={};
 let i=0;for(const r of rows){const n=M.normalize(r);const card={...r,finder:n};delete card.description;delete card.short_description;delete card.image_urls;delete card.extra_specs;
  insert('finder_watches',[r.id,r.brand,r.collection_label||r.parent_model||'',r.specific_model||'',r.reference_number||'',n.reference,M.fold(r.specific_model),n.diameter,n.thickness,n.lug,n.reserve,n.water,n.frequency,n.jewels,n.captured,n.production,n.status,JSON.stringify(card),JSON.stringify({...r,finder:n}),n.width,n.weight]);
  for(const [facet,values]of Object.entries(n.facets))for(const value of values){insert('finder_facets',[r.id,facet,value]);(vocabulary[facet]??=new Map()).set(value,(vocabulary[facet].get(value)||0)+1);}
  if(Number.isFinite(r.price_value)&&r.price_value>0&&/^[A-Z]{3}$/.test(r.currency||''))insert('finder_prices',[r.id,r.source_kind==='Official catalog'?'official_retail':'recorded_catalog',r.currency,r.price_value,r.market||null,n.captured||null]);
  db.prepare('INSERT INTO finder_fts(rowid,identity,reference_key,aliases,specs,content) VALUES (?,?,?,?,?,?)').run(++i,[r.brand,r.collection_label,r.parent_model,r.specific_model].filter(Boolean).join(' '),n.reference,n.aliases,[r.case_material,r.dial_color,r.movement,r.caliber,r.features].filter(Boolean).join(' '),[r.marketing_name,r.nickname,r.short_description,r.description].filter(Boolean).join(' '));
  // FTS rowids align with the watch rowids; both are rebuilt in the same transaction.
  if(seed)sql.push(`INSERT INTO finder_fts(rowid,identity,reference_key,aliases,specs,content) VALUES (${[i,[r.brand,r.collection_label,r.parent_model,r.specific_model].filter(Boolean).join(' '),n.reference,n.aliases,[r.case_material,r.dial_color,r.movement,r.caliber,r.features].filter(Boolean).join(' '),[r.marketing_name,r.nickname,r.short_description,r.description].filter(Boolean).join(' ')].map(quote).join(',')});`);
 }
 const metadata={extraLabels:[...new Set(rows.flatMap(r=>(r.extra_specs||[]).map(x=>x.label)))],version:1,total:rows.length,facets:Object.fromEntries(Object.entries(vocabulary).map(([key,values])=>[key,[...values].map(([value,count])=>({value,count})).sort((a,b)=>a.value.localeCompare(b.value))])),currencies:[...new Set(rows.filter(r=>r.price_value!=null).map(r=>r.currency).filter(Boolean))].sort(),priceSources:[{value:'official_retail',label:'Official retail snapshot'},{value:'recorded_catalog',label:'Archive recorded price'}],notes:['Facets show documented values. Missing specifications stay unknown.','Styles use stated source labels; production status is not inferred from capture dates.','Budgets and price sorting use the chosen source and currency; no conversion is applied.']};
 insert('finder_meta',['catalog',JSON.stringify(metadata)]);db.exec('COMMIT');db.exec('ANALYZE');if(seed)fs.writeFileSync(seed,sql.join('\n')+'\nANALYZE;\n');return {db,metadata};
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const data=JSON.parse(fs.readFileSync(path.join(root,'dist/data.json'),'utf8'));const output=path.join(root,'.finder');fs.mkdirSync(output,{recursive:true});
 const database=new DatabaseSync(path.join(output,'catalog.sqlite'));const {metadata}=buildCatalog(data,{database,seed:path.join(output,'catalog.sql')});database.close();
 const featured=(data.showcaseBrands||['Audemars Piguet','H. Moser & Cie.','Bulgari']).map(brand=>data.records.find(r=>r.brand===brand&&r.image_url)).filter(Boolean);
 const bootstrap={...data,records:featured,partial:true,finderMetadata:metadata,comparisonExtraLabels:[...new Set(data.records.flatMap(r=>(r.extra_specs||[]).map(x=>x.label)))]};
 fs.writeFileSync(path.join(root,'dist/bootstrap.json'),JSON.stringify(bootstrap));console.log(JSON.stringify({watches:metadata.total,database:path.join(output,'catalog.sqlite'),seed:path.join(output,'catalog.sql'),bootstrapBytes:fs.statSync(path.join(root,'dist/bootstrap.json')).size}));
}
