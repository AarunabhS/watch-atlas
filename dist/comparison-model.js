/* Comparison values and requirements share the same rules in the UI and tests. */
(function(root){
'use strict';
const missing='Not recorded';
const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
function measure(value,unit){
 const s=clean(value).replace(/,/g,'');
 if(!s||/\d\s*(?:-|–|to|x|×)\s*\d|\d\s*\/\s*\d/i.test(s))return null;
 const pattern=unit==='mm'?/(\d+(?:\.\d+)?)\s*mm\b/i:unit==='g'?/(\d+(?:\.\d+)?)\s*(?:g|grams?)\b/i:/(\d+(?:\.\d+)?)\s*(?:h|hours?|hrs?)\b/i;
 const m=pattern.exec(s);if(m)return Number(m[1]);
 return /^\d+(?:\.\d+)?$/.test(s)?Number(s):null;
}
function water(value){
 const s=clean(value).replace(/,/g,'');
 if(/not water[- ]resistant|non [ée]tanche|humidity.*only/i.test(s))return 0;
 const m=/(\d+(?:\.\d+)?)\s*(?:m\b|meters?\b|metres?\b)/i.exec(s);if(m)return Number(m[1]);
 const b=/(\d+(?:\.\d+)?)\s*(?:bars?|atm)\b/i.exec(s);return b?Number(b[1])*10:null;
}
const field=(id,label,group,read,type='text',unit='')=>({id,label,group,read,type,unit});
const fields=[
 field('brand','Watchmaker','Identity',r=>r.brand),field('specific_model','Model','Identity',r=>r.specific_model),
 field('reference_number','Reference','Identity',r=>r.reference_number),field('collection_label','Collection','Identity',r=>r.collection_label||r.parent_model),
 field('watch_kind','Watch type','Identity',r=>r.watch_kind||'Wristwatch'),field('segment','Style / segment','Identity',r=>r.segment),
 field('year_introduced','Year introduced','Identity',r=>r.year_introduced),field('made_in','Country of manufacture','Identity',r=>r.made_in),
 field('nickname','Nickname','Identity',r=>r.nickname),field('marketing_name','Marketing name','Identity',r=>r.marketing_name),
 field('price_value','Recorded catalog price','Price & source',r=>Number.isFinite(r.price_value)?r.price_value:null,'price'),
 field('currency','Catalog currency','Price & source',r=>r.currency),field('market','Source market','Price & source',r=>r.market),
 field('captured_date','Catalog snapshot','Price & source',r=>r.captured_label||'2023–2024 archive'),
 field('watch_URL','Watchmaker source','Price & source',r=>r.watch_URL,'url'),
 field('diameter','Case diameter','Case & dimensions',r=>r.diameter_metric_eligible===false?null:r.diameter_mm??measure(r.diameter,'mm'),'number','mm'),
 field('case_thickness','Case thickness','Case & dimensions',r=>measure(r.case_thickness,'mm'),'number','mm'),
 field('between_lugs','Lug width','Case & dimensions',r=>measure(r.between_lugs,'mm'),'number','mm'),
 field('lug_to_lug','Lug to lug','Case & dimensions',r=>measure(r.lug_to_lug,'mm'),'number','mm'),
 field('weight','Weight','Case & dimensions',r=>measure(r.weight,'g'),'number','g'),
 field('case_shape','Case shape','Case & dimensions',r=>r.case_shape),field('case_material','Case material','Case & dimensions',r=>r.case_material),
 field('case_finish','Case finish','Case & dimensions',r=>r.case_finish),field('caseback','Caseback','Case & dimensions',r=>r.caseback),
 field('bezel_material','Bezel material','Case & dimensions',r=>r.bezel_material),field('bezel_color','Bezel color','Case & dimensions',r=>r.bezel_color),
 field('crystal','Crystal','Case & dimensions',r=>r.crystal),field('water_resistance','Water resistance rating','Case & dimensions',r=>water(r.water_resistance),'number','m'),
 field('movement_family','Movement family','Movement & functions',r=>r.movement_family==='Not specified'?'':r.movement_family),
 field('movement','Movement description','Movement & functions',r=>r.movement),field('caliber','Caliber','Movement & functions',r=>r.caliber),
 field('power_reserve','Power reserve','Movement & functions',r=>measure(r.power_reserve,'h'),'number','h'),
 field('frequency','Frequency','Movement & functions',r=>r.frequency),field('jewels','Movement jewels','Movement & functions',r=>r.jewels),
 field('features','Functions / complications','Movement & functions',r=>r.features),
 field('dial_color','Dial color / finish','Dial & gemstones',r=>r.dial_color),field('numerals','Numerals / markers','Dial & gemstones',r=>r.numerals),
 field('gemstones','Recorded gemstones','Dial & gemstones',r=>r.gemstones?.length?r.gemstones.join(', '):''),
 field('bracelet_material','Strap / bracelet material','Strap & clasp',r=>r.bracelet_material),
 field('bracelet_color','Strap / bracelet color','Strap & clasp',r=>r.bracelet_color),field('clasp_type','Clasp','Strap & clasp',r=>r.clasp_type)
];
const defaults=['price_value','diameter','case_thickness','case_material','water_resistance','movement_family','caliber','power_reserve','features','dial_color','bracelet_material','captured_date'];
function allFields(records){
 const labels=[...new Set(records.flatMap(r=>(r.extra_specs||[]).map(x=>clean(x.label))).filter(Boolean))].sort();
 return [...fields,...labels.map(label=>field('extra:'+label,label,'Additional recorded details',r=>(r.extra_specs||[]).filter(x=>clean(x.label)===label).map(x=>x.value).join('; ')))];
}
function known(value){return value!==null&&value!==undefined&&clean(value)!=='';}
function display(r,f){
 const v=f.read(r);if(!known(v)){const raw=clean(r[f.id]);return f.id==='price_value'?(r.price||'Price unavailable'):raw?(f.type==='number'?'Source value: ':'')+raw:missing;}
 if(f.type==='price')return (r.currency||'Currency unspecified')+' '+Number(v).toLocaleString('en-US');
 if(f.type==='number')return v+' '+f.unit;
 return clean(v);
}
function operators(f){return ['number','price'].includes(f.type)?['lte','gte','eq','between','known']:['contains','equals','excludes','known'];}
function validateRule(rule,f){
 if(!f||!operators(f).includes(rule.op))return 'Choose a supported parameter and condition.';
 if(rule.op==='known')return '';
 if(['number','price'].includes(f.type)){
  if(clean(rule.value)===''||!Number.isFinite(Number(rule.value))||Number(rule.value)<0)return 'Enter a valid nonnegative number.';
  if(rule.op==='between'&&(clean(rule.value2)===''||!Number.isFinite(Number(rule.value2))||Number(rule.value2)<Number(rule.value)))return 'Enter an upper value at least as large as the lower value.';
  if(f.type==='price'&&!/^[A-Z]{3}$/.test(rule.currency||''))return 'Choose a currency for the budget.';
 }else if(!clean(rule.value))return 'Enter a value for this condition.';
 return '';
}
function evaluate(r,rule,f,includeUnknown=false){
 if(validateRule(rule,f))return {pass:false,unknown:false};
 const v=f.read(r),unknown=!known(v)||(f.type==='price'&&!r.currency);
 if(rule.op==='known')return {pass:!unknown,unknown};
 if(unknown)return {pass:includeUnknown,unknown:true};
 if(f.type==='price'&&r.currency!==rule.currency)return {pass:false,unknown:false};
 let pass=false;
 if(['number','price'].includes(f.type)){
  const n=Number(rule.value);pass=rule.op==='lte'?v<=n:rule.op==='gte'?v>=n:rule.op==='eq'?v===n:v>=n&&v<=Number(rule.value2);
 }else{const a=clean(v).toLocaleLowerCase(),b=clean(rule.value).toLocaleLowerCase();pass=rule.op==='equals'?a===b:rule.op==='excludes'?!a.includes(b):a.includes(b);}
 return {pass,unknown:false};
}
function match(r,rules,available,includeUnknown=false){
 const results=rules.map(rule=>evaluate(r,rule,available.find(f=>f.id===rule.field),includeUnknown));
 return {pass:results.every(x=>x.pass),unknown:results.filter(x=>x.unknown).length};
}
function difference(rows,f){
 const values=rows.map(r=>{const v=f.read(r);return known(v)?(f.type==='price'?r.currency+'|':'')+clean(v).toLocaleLowerCase():'__missing__';});
 return new Set(values).size>1;
}
function csvCell(value){let s=String(value??'');if(/^[\s]*[=+@-]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';}
function toCsv(rows,selectedFields){const matrix=[['Parameter',...rows.map(r=>r.brand+' '+r.specific_model+' ('+r.reference_number+')')],...selectedFields.map(f=>[f.label,...rows.map(r=>display(r,f))])];return '\uFEFF'+matrix.map(row=>row.map(csvCell).join(',')).join('\r\n');}
const api={fields,defaults,allFields,known,measure,water,display,operators,validateRule,evaluate,match,difference,csvCell,toCsv};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AtlasCompare=api;
})(globalThis);
