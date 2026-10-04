'use strict';
const test=require('node:test');const assert=require('node:assert/strict');
const {mergeRecords,historical}=require('../tools/apply_watch_refresh.cjs');
const original={id:'saved-shortlist-id',brand:'Breguet',reference_number:'7038BR/CT/3V6/D00D',specific_model:'Tradition 7038',parent_model:'Tradition',is_watch:true,sources:['archive'],case_material:'Gold',gemstones:[],coverage:70};
const capture={brand:'Breguet',reference_number:'7038BR/CT/3V6 D00D',specific_model:'Tradition 7038',parent_model:'Tradition',id:'new-source-id',product_detail_parsed:true,validation_errors:[],captured_at:'2026-10-04T10:00:00Z',image_URL:'https://www.breguet.com/image.png',watch_URL:'https://www.breguet.com/en/watches/7038',source_hash:'proof',market:'Global',language:'en'};
const datasets=[{id:'breguet-official-refresh',brand:'Breguet',label:'Official reference refresh'}];
test('exact reference refresh keeps saved IDs and unrelated records and is repeatable',()=>{
 const unrelated={id:'other',brand:'Tudor',is_watch:true};const baseline=[original,unrelated];const proofs={[capture.image_URL]:{status:'working'}};
 const rows=mergeRecords(baseline,baseline,[capture],proofs,datasets);assert.equal(rows[0].id,original.id);assert.equal(rows[0].verification_status,'verified');assert.strictEqual(rows[1],unrelated);
 assert.deepEqual(mergeRecords(rows,baseline,[capture],proofs,datasets),rows);
});
test('a broken image prevents importing a record',()=>{assert.throws(()=>mergeRecords([original],[original],[capture],{[capture.image_URL]:{status:'unavailable'}},datasets),/Unverified image/);});
test('conflicted historical Breguet details are withheld while reference and identity survive',()=>{
 const row=historical({...original,reference_number:'7057BR/G9/9W6',price:'10000',currency:'USD',diameter:'37 mm',diameter_mm:37,caliber:'505SR',caliber_key:'505SR'});
 assert.equal(row.id,original.id);assert.equal(row.reference_number,'7057BR/G9/9W6');assert.equal(row.verification_status,'unverified');assert.equal(row.case_material,'');assert.equal(row.diameter_mm,null);assert.equal(row.caliber_key,'');assert.equal(row.price_value,null);assert.equal(row.watch_URL,'');assert.equal(row.image_url,'');
});
test('unavailable Rolex records retain historical specifications and clear known invalid materials',()=>{
 const row=historical({...original,brand:'Rolex',reference_number:'126655-0005',case_material:'Flexible metal blades overmoulded with high-performance elastomer',diameter:'40 mm',diameter_mm:40});
 assert.equal(row.diameter_mm,40);assert.equal(row.case_material,'');assert.equal(row.verification_status,'unverified');assert.equal(row.is_watch,true);
});
