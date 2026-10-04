'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),M=require('../dist/comparison-model.js'),data=require('../dist/data.json');
const field=id=>M.fields.find(f=>f.id===id);
const watch={diameter_mm:40,case_thickness:'9.5 mm',water_resistance:'10 bar',movement_family:'Automatic',price_value:6500,currency:'USD',power_reserve:'72 hours',features:'GMT, date',case_material:'Stainless steel',gemstones:[]};
test('requirements combine dimensions, budget, movement and complications with AND',()=>{
 const rules=[{field:'diameter',op:'lte',value:'40'},{field:'price_value',op:'lte',value:'7000',currency:'USD'},{field:'movement_family',op:'equals',value:'Automatic'},{field:'features',op:'contains',value:'gmt'}];
 assert.deepEqual(M.match(watch,rules,M.fields),{pass:true,unknown:0});assert.equal(M.match({...watch,diameter_mm:41},rules,M.fields).pass,false);
});
test('budgets never compare different currencies or treat missing prices as zero',()=>{
 const r={field:'price_value',op:'lte',value:'7000',currency:'USD'};
 assert.equal(M.evaluate({...watch,currency:'INR'},r,field(r.field)).pass,false);
 assert.deepEqual(M.evaluate({...watch,price_value:null},r,field(r.field)),{pass:false,unknown:true});
 assert.deepEqual(M.evaluate({...watch,price_value:null},r,field(r.field),true),{pass:true,unknown:true});
});
test('unknown values do not satisfy negative requirements or imply no gemstones',()=>{
 const r={field:'gemstones',op:'excludes',value:'Diamond'};assert.equal(M.evaluate(watch,r,field(r.field)).pass,false);assert.equal(M.display(watch,field('gemstones')),'Not recorded');
 assert.equal(M.evaluate(watch,{field:'gemstones',op:'known',value:''},field('gemstones'),true).pass,false);
});
test('numeric filters normalize stated units and reject ranges and battery durations',()=>{
 assert.equal(M.water('Waterproof to 1,220 metres / 4,000 feet'),1220);assert.equal(M.water('5 ATM'),50);assert.equal(M.water('not water-resistant'),0);assert.equal(M.water('Not specified'),null);
 assert.equal(M.measure('Approximately 72 hours','h'),72);assert.equal(M.measure('6-12 months','h'),null);assert.equal(M.measure('35 x 42 mm','mm'),null);assert.equal(M.measure('48–72 hours','h'),null);assert.equal(M.measure('120 g','g'),120);
});
test('invalid and reversed ranges are actionable validation errors',()=>{
 assert.ok(M.validateRule({op:'between',value:'42',value2:'38'},field('diameter')));assert.ok(M.validateRule({op:'lte',value:''},field('diameter')));assert.ok(M.validateRule({op:'lte',value:'abc'},field('diameter')));assert.ok(M.validateRule({op:'contains',value:''},field('case_material')));
});
test('same numbers in different currencies remain different comparison rows',()=>{
 assert.equal(M.difference([watch,{...watch,currency:'INR'}],field('price_value')),true);assert.equal(M.difference([watch,{...watch}],field('diameter')),false);assert.equal(M.difference([watch,{...watch,diameter_mm:null}],field('diameter')),true);
});
test('published additional specifications are selectable without overriding core fields',()=>{
 const f=M.allFields([{extra_specs:[{label:'Warranty',value:'5 years'},{label:'Warranty',value:'Worldwide'}]}]);assert.equal(f.filter(x=>x.id==='extra:Warranty').length,1);assert.equal(f.find(x=>x.id==='extra:Warranty').read({extra_specs:[{label:'Warranty',value:'5 years'}]}),'5 years');assert.ok(M.allFields(data.records).length>40);
});
test('CSV exports quote delimiters and neutralize spreadsheet formulas',()=>{
 assert.equal(M.csvCell('a,"b"'),'"a,""b"""');assert.equal(M.csvCell('=IMPORTXML("url")'),'"\'=IMPORTXML(""url"")"');assert.equal(M.csvCell('  @SUM(A1)'),'"\'  @SUM(A1)"');
});
test('comparison does not mutate source data or include diagonal diameter measurements',()=>{
 const r={...watch,diameter_metric_eligible:false,diameter:'Diagonal: 40 mm'};assert.equal(field('diameter').read(r),null);assert.equal(M.display(r,field('diameter')),'Source value: Diagonal: 40 mm');const before=JSON.stringify(watch);M.match(watch,[],M.fields);M.display(watch,field('price_value'));assert.equal(JSON.stringify(watch),before);
});
test('exported comparisons retain price currencies, headings and original references',()=>{const csv=M.toCsv([{...watch,brand:'Maker',specific_model:'Model, One',reference_number:'REF-1'},{...watch,brand:'Maker',specific_model:'Model Two',reference_number:'REF-2',currency:'INR'}],[field('price_value'),field('diameter')]);assert.ok(csv.includes('Model, One (REF-1)'));assert.ok(csv.includes('"USD 6,500","INR 6,500"'));assert.ok(csv.includes('"Case diameter","40 mm","40 mm"'));});
