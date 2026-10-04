'use strict';
const assert=require('node:assert/strict');
const data=require('../dist/data.json');const model=require('../dist/catalog-model.js');
const watches=data.records.filter(r=>r.is_watch);
assert.equal(new Set(data.records.map(r=>r.id)).size,data.records.length,'duplicate record IDs');
assert.deepEqual(data.insights.overall,model.summarizeWatches(watches,'All watchmakers'));
assert.equal(data.stats.records,data.records.length);
assert.equal(data.stats.preparedBrands,new Set(watches.map(r=>r.brand)).size);
assert.equal(model.curatedOrder(watches,data.brandOrder).length,watches.length);
assert.equal(data.stats.pocketWatches,watches.filter(r=>r.watch_kind==='Pocket watch').length);
assert.equal(data.stats.wristwatches+data.stats.pocketWatches,watches.length);
assert.equal(data.inventory.length,data.archiveStats.files);
for(const dataset of data.catalogImports){
 const rows=watches.filter(r=>r.source_dataset===dataset.id);
 assert.equal(rows.length,dataset.rows);
 for(const r of rows){assert.equal(r.brand,dataset.brand);assert.ok((dataset.captured_dates||[dataset.captured_date]).includes(r.captured_date));assert.equal(r.source_kind,'Official catalog');assert.ok(r.reference_number&&r.watch_URL&&r.source_hash);assert.ok(r.price_value===null||r.price_value>0);}
}
for(const b of data.insights.brands)assert.deepEqual(b,model.summarizeWatches(watches.filter(r=>r.brand===b.name),b.name));
assert.equal(data.insights.brands.reduce((sum,b)=>sum+b.count,0),watches.length);
assert.equal(data.records.filter(r=>!r.source_dataset||r.archive_record_id).length,data.archiveStats.records,'archive record identities were lost during refresh');
console.log(`Validated ${watches.length} watches, ${data.stats.preparedBrands} watchmakers, ${data.inventory.length} archived files`);
