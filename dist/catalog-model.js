/* Shared catalog normalization and summaries for imports and the browser. */
(function(root){
'use strict';
const categories=['Time & date','Chronograph','Diving','Travel & GMT','Complications','Jewellery'];
const columns='reference_number watch_URL type brand year_introduced parent_model specific_model nickname marketing_name style currency price made_in case_shape case_material case_finish caseback diameter between_lugs lug_to_lug case_thickness bezel_material bezel_color crystal water_resistance weight dial_color numerals bracelet_material bracelet_color clasp_type movement caliber power_reserve frequency jewels features short_description description'.split(' ');
const coreFields='reference_number watch_URL parent_model case_material diameter movement water_resistance power_reserve dial_color image_url'.split(' ');
const text=value=>value===null||value===undefined?'':String(value).replace(/\s+/g,' ').trim();
function movementFamily(row){
 const value=text(row.movement);
 if(/quartz/i.test(value))return 'Quartz';
 if(/self[ -]?winding|selfwinding|automatic|automatique/i.test(value))return 'Automatic';
 if(/manual|hand[ -]?(?:wound|winding)|remontage manuel/i.test(value))return 'Manual';
 return 'Not specified';
}
function segment(row){
 const selected=[row.specific_model,row.marketing_name,row.features].join(' ');
 if(/perpetual|annual calendar|tourbillon|repeater|sonnerie|moon.?phase|split.?seconds|rattrapante|world time|alarm|retrograde|power reserve (?:display|indicator)/i.test(selected))return 'Complications';
 if(/chronograph|chronographe|\bchrono\b/i.test(selected))return 'Chronograph';
 if(/superocean|submariner|sea.?dweller|aquatimer|pelagos|diving|diver/i.test(selected+' '+row.parent_model))return 'Diving';
 if(/\bgmt\b|dual time|second time zone|travel time/i.test(selected))return 'Travel & GMT';
 if(/joaillerie|jewell?ery|jewell?er|jewelry|serpenti|divas|allegra/i.test(selected))return 'Jewellery';
 return 'Time & date';
}
function stoneDetails(source,row){
 const evidenceFields=['dial_color','numerals','case_material','bezel_material','bracelet_material','clasp_type'];
 const values=evidenceFields.map(key=>[key,text(row[key])]);
 for(const [key,value] of Object.entries(source.raw_specifications||{})){if(/gem|diamond|stone|setting/i.test(key))values.push([key,text(value)]);}
 for(const feature of source.brand==='IWC'&&Array.isArray(source.raw_specifications?.Features)?source.raw_specifications.Features:[]){if(/gem|diamond|stone|setting/i.test(feature.label+' '+feature.value))values.push(['Features',text(feature.label+' '+feature.value)]);}
 if(source.gem_setting)values.push(['gem_setting',text(source.gem_setting)]);
 const patterns={Diamond:/\bdiamonds?\b|\bdiamants?\b/i,Ruby:/\brub(?:y|ies)\b(?![ -]?red)/i,Emerald:/\bemeralds?\b(?![ -]?green)/i,Sapphire:/\bsapphires?\b(?![ -]?(?:blue|crystal|glass))/i,Amethyst:/\bamethysts?\b/i,Tourmaline:/\btourmalines?\b/i,Rubellite:/\brubellites?\b/i,Peridot:/\bperidots?\b/i,Spinel:/\bspinels?\b/i,Tsavorite:/\btsavorites?\b/i};
 const stones=[],evidence=[];
 for(const [name,pattern] of Object.entries(patterns)){
  const matches=values.filter(([,value])=>pattern.test(value));
  if(matches.length){stones.push(name);evidence.push(...matches.map(([field,value])=>({stone:name,field,value})));}
 }
 return {gemstones:stones,gem_set:stones.length>0,gemstone_evidence:evidence};
}
function dateParts(value){
 const date=new Date(value);if(!Number.isFinite(date.getTime()))throw new Error('Missing or invalid capture date');
 const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date).map(x=>[x.type,x.value]));
 return {date:`${parts.year}-${parts.month}-${parts.day}`,label:new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',year:'numeric',month:'long',day:'numeric'}).format(date)};
}
function normalize(source,dataset){
 if(!source.product_detail_parsed||source.validation_errors?.length||!source.reference_number||!source.id)throw new Error('Invalid or unparsed watch record');
 const row=Object.fromEntries(columns.map(key=>[key,text(source[key])]));
 row.image_url=text(source.image_url||source.image_URL);
 row.id=source.id;row.sources=[dataset.label];row.source_dataset=dataset.id;
 row.source_hash=source.source_hash;row.captured_at=source.captured_at;
 const captured=dateParts(source.captured_at);row.captured_date=captured.date;row.captured_label=captured.label;
 row.market=source.market;row.language=source.language;row.source_kind='Official catalog';
 row.watch_kind=source.subtype==='Pocketwatch'||/pocket/i.test(source.type||'')?'Pocket watch':'Wristwatch';row.is_watch=true;
 const numericPrice=/^(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$/.test(row.price)?Number(row.price.replace(/,/g,'')):null;
 row.price_value=numericPrice!==null&&numericPrice>0?numericPrice:null;
 row.price_status=source.price_status||'';row.price_tax_label=source.price_tax_label||'';
 const diameter=/^(\d+(?:[.,]\d+)?)\s*mm$/i.exec(row.diameter);
 row.diameter_mm=diameter?Number(diameter[1].replace(',','.')):null;
 row.diameter_source=diameter?'Case diameter field':'';
 row.diameter_note=text(source.case_dimensions_display);
 row.diameter_metric_eligible=row.watch_kind!=='Pocket watch'&&row.diameter_mm!==null&&!/diagonal/i.test(row.diameter_note);
 row.collection_label=text(source.catalog_collection||source.collection_label||row.parent_model)||'Other';
 row.movement_family=movementFamily(row);row.movement_source=row.movement?'Movement field':'';
 row.caliber_key=row.caliber.replace(/\((?:manufacture|automatic|manual|self-winding)\)/gi,'').replace(/\s+/g,' ').trim().toUpperCase();
 row.segment=segment(row);Object.assign(row,stoneDetails(source,row));
 row.coverage=Math.round(coreFields.filter(key=>row[key]).length/coreFields.length*100);
 const extras={crown:'Crown',hands:'Hands',hands_reverse:'Reverse hands',case_decoration:'Case decoration',movement_diameter:'Movement diameter',movement_thickness:'Movement thickness',number_of_parts:'Movement parts',number_of_bridges:'Movement bridges',balance_wheel:'Balance wheel',balance_spring:'Balance spring',winding_rotor:'Winding rotor',quality_seal:'Quality seal',gem_setting:'Gem setting',additional_strap:'Additional strap',bracelet_adjustment:'Bracelet adjustment',pocket_chain_or_stand:'Pocket chain or stand',pocket_bow:'Pocket bow',pocket_crown:'Pocket crown',bezel:'Bezel',strapType:'Strap type',lug:'Strap dimensions',buckleMaterial:'Clasp material',buckleSize:'Clasp size'};
 row.extra_specs=Object.entries(extras).filter(([key])=>text(source[key])).map(([key,label])=>({label,value:text(source[key])}));
 if(source.strap_description)row.extra_specs.push({label:'Strap description',value:text(source.strap_description)});
 if(source.price_kind||source.price_note)row.extra_specs.push({label:'Price basis',value:text(source.price_kind||source.price_note)});
 if(source.brand==='Tudor')for(const label of ['Five-year Guarantee','Winding Crown']){const value=text(source.raw_specifications?.[label]);if(value)row.extra_specs.push({label,value});}
 if(source.brand==='IWC')for(const [section,label] of [['Case','Crown'],['Movement','Components']]){const value=text(source.raw_specifications?.[section]?.find(x=>x.label===label)?.value);if(value)row.extra_specs.push({label:label==='Components'?'Movement parts':label,value});}
 if(source.headWeight)row.extra_specs.push({label:'Watch-head weight',value:text(source.headWeight)+' g'});
 if(source.warrantyDuration)row.extra_specs.push({label:'Manufacturer warranty',value:text(source.warrantyDuration)+' years'});
 if(typeof source.limited_edition==='boolean')row.extra_specs.push({label:'Limited edition',value:source.limited_edition?'Yes':'No'});
 for(const extra of source.additional_specifications||[]){if(extra.label&&text(extra.value)&&!row.extra_specs.some(x=>x.label===extra.label&&x.value===text(extra.value)))row.extra_specs.push({label:extra.label,value:text(extra.value)});}
 for(const [key,value] of Object.entries(source.raw_specifications||{})){if(/^(?:battery_type|strap_surface|strap_underside|watch_size)$/.test(key)&&text(value))row.extra_specs.push({label:key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()),value:text(value)});}
 for(const difference of source.source_discrepancies||[]){if(!('accordion' in difference)||!('caliber_block' in difference))continue;row.extra_specs.push({label:'Source difference: '+difference.field,value:'Technical accordion: '+difference.accordion+'; separate calibre block: '+difference.caliber_block});}
 row.image_urls=source.image_urls||[row.image_url];
 return row;
}
function summarizeWatches(rows,name){
 const ds=rows.filter(r=>r.diameter_mm!==null&&r.diameter_mm!==undefined&&r.watch_kind!=='Pocket watch'&&r.diameter_metric_eligible!==false).map(r=>r.diameter_mm),g=rows.filter(r=>r.gem_set).length;
 const counts=key=>rows.reduce((a,r)=>(a[r[key]]=(a[r[key]]||0)+1,a),{});
 return{name,count:rows.length,diameterN:ds.length,diameterAvg:ds.length?ds.reduce((a,b)=>a+b,0)/ds.length:null,diameterMin:ds.length?Math.min(...ds):null,diameterMax:ds.length?Math.max(...ds):null,gemCount:g,gemPercent:rows.length?g/rows.length*100:0,calibers:new Set(rows.filter(r=>r.caliber_key).map(r=>r.brand+'|'+r.caliber_key)).size,caliberN:rows.filter(r=>r.caliber_key).length,movements:counts('movement_family'),segments:counts('segment'),collections:counts('collection_label'),stones:rows.reduce((a,r)=>(r.gemstones.forEach(stone=>a[stone]=(a[stone]||0)+1),a),{})};
}
function curatedOrder(rows,order=[]){
 const names=[...new Set([...order,...rows.map(r=>r.brand)])];
 const groups=names.map(name=>rows.filter(r=>r.brand===name));
 const result=[];for(let i=0;i<Math.max(0,...groups.map(g=>g.length));i++)for(const group of groups)if(group[i])result.push(group[i]);
 return result;
}
function snapshotLabel(rows){
 const labels=[...new Set(rows.map(r=>r.captured_label||'2023–2024 archive'))];
 return labels.length===1?labels[0]:'Archive + October 2026 catalogs';
}
const api={categories,columns,coreFields,normalize,summarizeWatches,curatedOrder,snapshotLabel};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AtlasModel=api;
})(globalThis);
