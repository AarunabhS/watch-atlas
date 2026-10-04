'use strict';
const test=require('node:test');const assert=require('node:assert/strict');const model=require('../dist/catalog-model.js');const data=require('../dist/data.json');
const dataset={id:'fixture',label:'Official catalog'};
const source={product_detail_parsed:true,reference_number:'TEST-1',id:'test-1',captured_at:'2026-10-01T22:00:00Z',diameter:'40 mm',movement:'Self-winding',brand:'Fixture',specific_model:'Chronomat Automatic',description:'The manufacturer also makes chronographs and diamond watches.',crystal:'Sapphire crystal',jewels:'25'};
test('capture date uses the collection timezone and missing prices stay missing',()=>{const row=model.normalize(source,dataset);assert.equal(row.captured_date,'2026-10-02');assert.equal(row.price_value,null);assert.equal(row.movement_family,'Automatic');assert.equal(row.segment,'Time & date');assert.equal(row.gem_set,false);});
test('diagonal and multiple dimensions do not distort wristwatch diameter comparisons',()=>{const a=model.normalize({...source,diameter:'30 x 40 mm'},dataset),b=model.normalize({...source,case_dimensions_display:'Diagonal: 40 mm'},dataset);assert.equal(a.diameter_mm,null);assert.equal(b.diameter_metric_eligible,false);assert.equal(model.summarizeWatches([a,b],'test').diameterN,0);});
test('pocket watches remain in catalog counts and are excluded from wristwatch measurements',()=>{const row=model.normalize({...source,subtype:'Pocketwatch'},dataset);assert.equal(row.watch_kind,'Pocket watch');assert.equal(row.is_watch,true);assert.equal(model.summarizeWatches([row],'test').count,1);assert.equal(model.summarizeWatches([row],'test').diameterN,0);});
test('gemstone classification uses selected watch specifications',()=>{const row=model.normalize({...source,gem_setting:'Bezel set with 40 diamonds'},dataset);assert.equal(row.gem_set,true);assert.deepEqual(row.gemstones,['Diamond']);});
test('curated sorting retains new watchmakers and every reference',()=>{const rows=[{brand:'Old',id:1},{brand:'New',id:2},{brand:'Future',id:3},{brand:'New',id:4}];assert.deepEqual(model.curatedOrder(rows,['New','Old']).map(r=>r.id),[2,1,3,4]);});
test('current records lead their brand and historical references remain available',()=>{const rows=[{brand:'Breguet',id:'old',verification_status:'unverified'},{brand:'Breguet',id:'current',verification_status:'verified'}];assert.deepEqual(model.curatedOrder(rows,['Breguet']).map(r=>r.id),['current','old']);});
test('reference searches accept the archive slash format and the current printed format',()=>{const row={brand:'Breguet',reference_number:'7038BR/CT/3V6 D00D',specific_model:'Tradition 7038'};for(const query of ['7038BR/CT/3V6/D00D','7038BRCT3V6D00D','7038br/ct/3v6 d00d'])assert.ok(model.matchesSearch(row,query));assert.equal(model.matchesSearch(row,'7057BRG99W6'),false);});
test('imported catalogs preserve complete reference counts and pocket types',()=>{assert.equal(data.records.filter(r=>r.brand==='Patek Philippe'&&r.is_watch).length,252);assert.equal(data.records.filter(r=>r.brand==='Breitling'&&r.is_watch).length,402);assert.equal(data.records.filter(r=>r.brand==='Patek Philippe'&&r.watch_kind==='Pocket watch').length,20);});

test('Jaeger-LeCoultre and Omega imports match the completed exports',()=>{assert.equal(data.records.filter(r=>r.brand==='Jaeger-LeCoultre'&&r.is_watch).length,197);assert.equal(data.records.filter(r=>r.brand==='Omega'&&r.is_watch).length,556);assert.equal(data.records.filter(r=>r.brand==='Omega'&&r.watch_kind==='Pocket watch').length,3);});
test('missing images remain valid watch references with a catalog fallback',()=>{const row=model.normalize({...source,image_URL:'',brand:'Omega'},dataset);assert.equal(row.image_url,'');assert.equal(row.is_watch,true);});
test('published Breguet French complication names remain discoverable by style',()=>{for(const name of ['Classique Phase de Lune 7787','Classique Répétition Minutes 7637','Tradition Seconde Rétrograde 7097'])assert.equal(model.normalize({...source,brand:'Breguet',specific_model:name},dataset).segment,'Complications');});
test('grouped official prices retain their currency and malformed prices stay unspecified',()=>{const row=model.normalize({...source,price:'6,900',currency:'USD'},dataset);assert.equal(row.price_value,6900);assert.equal(row.currency,'USD');assert.equal(model.normalize({...source,price:'6,90'},dataset).price_value,null);});
test('new catalog families and selected IWC gemstone features feed the filters',()=>{
 assert.equal(model.normalize({...source,specific_model:'Black Bay Chrono',features:'Chrono; Date'},dataset).segment,'Chronograph');
 assert.equal(model.normalize({...source,specific_model:'Aquatimer Automatic',features:''},dataset).segment,'Diving');
 assert.equal(model.normalize({...source,specific_model:'Pelagos FXD',features:''},dataset).segment,'Diving');
 const row=model.normalize({...source,brand:'IWC',raw_specifications:{Features:[{label:'Bezel featuring 45 diamonds',value:''},{label:'Sapphire glass',value:''}]}},dataset);assert.deepEqual(row.gemstones,['Diamond']);
});
test('Tudor and IWC imports preserve completed references, markets and price omissions',()=>{
 const tudor=data.records.filter(r=>r.source_dataset==='tudor-official-catalog'),iwc=data.records.filter(r=>r.source_dataset==='iwc-official-catalog');
 assert.equal(tudor.length,216);assert.equal(iwc.length,225);
 assert.ok(tudor.every(r=>r.market==='IN'&&r.currency==='INR'&&r.price_value>0));
 assert.ok(iwc.every(r=>r.market==='US'));
 assert.equal(iwc.filter(r=>r.price_value!==null).length,210);assert.ok(iwc.filter(r=>r.price_value!==null).every(r=>r.currency==='USD'));
 assert.equal(iwc.filter(r=>r.price_value===null).length,15);
 const sparse=iwc.find(r=>r.reference_number==='IW659803');assert.equal(sparse.diameter_mm,null);assert.equal(sparse.power_reserve,'');
 assert.ok(iwc.find(r=>r.reference_number==='IW328801').extra_specs.some(s=>s.label==='Movement parts'&&s.value==='163'));
 const smallTudor=tudor.find(r=>r.reference_number==='M91350-0001');assert.equal(smallTudor.between_lugs,'15 mm');assert.equal(smallTudor.lug_to_lug,'');
 const fxd=tudor.find(r=>r.reference_number==='M25717N-0001');assert.equal(fxd.between_lugs,'22 mm');assert.equal(fxd.lug_to_lug,'52 mm');
 assert.equal(data.insights.overall.count,3636);assert.equal(data.stats.preparedBrands,11);assert.equal(data.stats.pocketWatches,24);assert.equal(data.inventory.length,73);
});
