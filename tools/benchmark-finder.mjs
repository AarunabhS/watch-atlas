/* Repeatable local benchmark; synthetic rows test query scale, not catalog accuracy. */
import {DatabaseSync} from 'node:sqlite';import {performance} from 'node:perf_hooks';import {buildCatalog} from './build-finder-catalog.mjs';import {compile} from '../backend/finder-service.mjs';import M from '../dist/finder-model.js';import fs from 'node:fs';
const source=JSON.parse(fs.readFileSync(new URL('../dist/data.json',import.meta.url),'utf8'));const template=source.records.filter(r=>r.is_watch).slice(0,12).map(r=>Object.fromEntries(Object.entries(r).filter(([key])=>['id','is_watch','brand','collection_label','parent_model','specific_model','reference_number','diameter','case_thickness','case_material','movement_family','water_resistance','features','price_value','currency','source_kind'].includes(key))));
const db=new DatabaseSync(':memory:');const {metadata}=buildCatalog({records:template},{database:db});const target=100000;
db.exec(`CREATE TEMP TABLE copies(n INTEGER); WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<${Math.ceil(target/template.length)}) INSERT INTO copies SELECT x FROM n; CREATE TEMP TABLE original AS SELECT * FROM finder_watches;`);
db.exec(`CREATE TEMP TABLE mapping(new_id TEXT PRIMARY KEY,old_id TEXT); INSERT INTO mapping SELECT o.id||'-synthetic-'||c.n,o.id FROM original o CROSS JOIN copies c LIMIT ${target-template.length};`);
const columns=db.prepare('PRAGMA table_info(finder_watches)').all().map(x=>x.name);db.exec('BEGIN');
console.error('Building synthetic watch rows');
const select=columns.map(name=>name==='id'?"o.id||'-synthetic-'||c.n":name==='reference_key'?"o.reference_key||c.n":'o.'+name).join(',');
db.exec(`INSERT INTO finder_watches SELECT ${select} FROM original o CROSS JOIN copies c LIMIT ${target-template.length};`);
console.error('Indexing synthetic facets');
db.exec("INSERT INTO finder_facets SELECT m.new_id,f.facet,f.value FROM mapping m JOIN finder_facets f ON f.watch_id=m.old_id;");
console.error('Indexing synthetic prices');
db.exec("INSERT INTO finder_prices SELECT m.new_id,p.source,p.currency,p.amount,p.market,p.captured FROM mapping m JOIN finder_prices p ON p.watch_id=m.old_id;");
console.error('Indexing synthetic text');
db.exec("INSERT INTO finder_fts(rowid,identity,reference_key,aliases,specs,content) SELECT w.rowid,w.brand||' '||w.collection||' '||w.model,w.reference_key,'','Titanium Automatic GMT','' FROM finder_watches w WHERE w.id NOT IN (SELECT id FROM original);");db.exec('COMMIT; ANALYZE;');
const cases=[{name:'catalog page',params:{}},{name:'reference prefix',params:{q:template[0].reference_number.slice(0,5)}},{name:'combined filters',params:{material:'White gold',movement:'Automatic',complication:'Tourbillon','diameter.max':43}},{name:'numeric sorting',params:{sort:'diameter-asc'}}];
const report={kind:'Synthetic local SQLite benchmark (in-memory; no network or D1 latency)',rows:db.prepare('SELECT COUNT(*) n FROM finder_watches').get().n,results:[]};
for(const c of cases){console.error('Benchmarking '+c.name);const q=compile(M.read(new URLSearchParams(c.params)),metadata),times=[];let matches;for(let i=0;i<8;i++){const start=performance.now();matches=db.prepare(q.count.sql).get(...q.count.params).total;const rows=db.prepare(q.results.sql).all(...q.results.params);if(rows.length>24)throw Error('Unbounded results');times.push(performance.now()-start);}times.sort((a,b)=>a-b);report.results.push({name:c.name,matches,medianMs:+times[4].toFixed(1),maxMs:+times.at(-1).toFixed(1)});}
console.log(JSON.stringify(report,null,2));db.close();
