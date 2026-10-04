/* Shared vocabulary, conservative source normalization and replaceable query parser. */
(function(root){'use strict';
const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
const fold=v=>clean(v).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const compact=v=>fold(v).replace(/[^a-z0-9]/g,'');
const facets={brand:'Watchmaker',collection:'Collection',material:'Case material',shape:'Case shape',dial:'Dial color',movement:'Movement',caliber:'Calibre',inhouse:'Manufacture movement',complication:'Complications',strap:'Strap / bracelet',style:'Stated style',kind:'Watch type',production:'Production',status:'Catalog status'};
// Extend vocabulary here; identities are discovered from the catalog, never query fixtures.
const terms={
 material:{Titanium:['titanium'],Ceramic:['ceramic'],Steel:['stainless steel','oystersteel','steel'], 'Rose gold':['rose gold','pink gold','everose','sedna gold'], 'Yellow gold':['yellow gold','yellow rolesor','moonshine gold'],'White gold':['white gold'],Platinum:['platinum'],Bronze:['bronze'],Carbon:['carbon','carbotech'],Aluminium:['aluminium','aluminum'],Gold:['gold']},
 movement:{Automatic:['automatic','self winding','selfwinding','self-winding'],Manual:['manual winding','manual-winding','manual','hand wound','hand-wound','hand winding','hand-winding'],Quartz:['quartz']},
 complication:{Date:['date','large date','big date'],'Day-date':['day-date','day date'],GMT:['gmt','dual time','second timezone','second time zone','second time-zone','travel time'],'Chronograph':['chronograph','chronographe'], 'Moon phase':['moon phase','moon phases','moonphase','moon-phase'], 'Annual calendar':['annual calendar'],'Perpetual calendar':['perpetual calendar'],'Minute repeater':['minute repeater'],Tourbillon:['tourbillon'],'World time':['world time','worldtime'],Alarm:['alarm'],'Power reserve indicator':['power reserve indicator','power reserve display'],'Equation of time':['equation of time'],Rattrapante:['rattrapante','split seconds','split-seconds'],'Flyback chronograph':['flyback chronograph','flyback'],Retrograde:['retrograde']},
 dial:{Blue:['blue'],Green:['green'],Black:['black'],White:['white'],Silver:['silver','silvery'],Grey:['grey','gray'],Brown:['brown'],Champagne:['champagne'],Pink:['pink'],Red:['red'],Beige:['beige','ivory'], 'Mother of pearl':['mother of pearl','mother-of-pearl'],Skeleton:['skeleton','openworked','open-worked']},
 shape:{Round:['round'],Rectangular:['rectangular','rectangle'],Square:['square'],Tonneau:['tonneau']},
 strap:{Leather:['leather','alligator','calfskin','crocodile'],Rubber:['rubber'],Textile:['textile','fabric','nato','nylon'],Steel:['steel','oystersteel'],Titanium:['titanium'],Gold:['gold'],Ceramic:['ceramic']},
 style:{Dress:['dress'],Sports:['sports','sport'],Diving:['diving','diver','dive watch'],Pilot:['pilot','aviation'],Classic:['classic']},
 kind:{Wristwatch:['wristwatch'], 'Pocket watch':['pocket watch'], 'Pendant watch':['pendant watch']}
};
const aliases=[{term:'AP',group:'brand',value:'Audemars Piguet'},{term:'JLC',group:'brand',value:'Jaeger-LeCoultre'},{term:'VC',group:'brand',value:'Vacheron Constantin'},{term:'Patek',group:'brand',value:'Patek Philippe'},{term:'Speedy',text:'Speedmaster'}];
const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const pattern=word=>new RegExp('\\b'+escape(fold(word)).replace(/ /g,'[ -]+')+'\\b','i');
function labels(value,group){const s=fold(value);return Object.entries(terms[group]||{}).filter(([,words])=>words.some(w=>[...s.matchAll(new RegExp(pattern(w).source,'gi'))].some(m=>!/(?:\bno|\bwithout|\bnot|\bnon)[ -]*$/.test(s.slice(0,m.index))&&!/^\s*(?::|=)?\s*(?:none\b|not present\b|not available\b)/.test(s.slice(m.index+m[0].length))))).map(([label])=>label);}
function number(value,unit){let s=fold(value).replace(/,/g,'');if(!s||/\d\s*(?:-|–|to|x|×|\/)\s*\d/.test(s))return null;const re=unit==='mm'?/^(\d+(?:\.\d+)?)\s*mm$/:unit==='h'?/(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b/:unit==='j'?/^(\d+)\s*(?:jewels?|rubies)?$/:/(\d+(?:\.\d+)?)\s*hz\b/;const m=re.exec(s);return m?Number(m[1]):null;}
function water(v){const s=fold(v).replace(/,/g,'');if(/not water[- ]resistant|non etanche/.test(s))return 0;const m=/(\d+(?:\.\d+)?)\s*(?:m\b|meters?\b|metres?\b)/.exec(s);if(m)return +m[1];const b=/(\d+(?:\.\d+)?)\s*(?:bar|atm)\b/.exec(s);return b?+b[1]*10:null;}
function normalize(r){
 const f={brand:[r.brand],collection:[r.collection_label||r.parent_model].filter(Boolean),material:labels(r.case_material,'material'),shape:labels(r.case_shape,'shape'),dial:labels(clean(r.dial_color).split(/[,;]/).filter(x=>!/hands|hour.markers|appliques|numerals|counters|subdials|inner bezel|external zone/i.test(x)).join(' ').replace(/(?:white|rose|pink|yellow) gold/gi,''),'dial'),movement:r.movement_family&&r.movement_family!=='Not specified'?[r.movement_family]:labels(r.movement,'movement'),caliber:[r.caliber_key||r.caliber].filter(Boolean),complication:labels([r.features,r.specific_model,r.marketing_name].join(' '),'complication'),strap:labels(r.bracelet_material,'strap'),style:labels(r.style,'style'),kind:[r.watch_kind||'Wristwatch'],inhouse:[],production:[],status:[]};
 if(f.material.some(x=>/gold/i.test(x))&&!f.material.includes('Gold'))f.material.push('Gold');
 if(/manufacture|in.house/i.test(r.movement+' '+(r.extra_specs||[]).filter(x=>/movement|calib/i.test(x.label)).map(x=>x.value).join(' ')))f.inhouse=['Yes'];
 if(typeof r.in_house_movement==='boolean')f.inhouse=[r.in_house_movement?'Yes':'No'];
 if(['Current','Discontinued','Limited edition'].includes(r.production_status))f.production=[r.production_status];
 f.status=[r.verification_status==='unverified'?'Historical · unverified':r.source_kind==='Official catalog'?'Official snapshot':'Archive snapshot'];
 const aliasText=[r.nickname];
 // Nicknames need source evidence. No reference lists or inferred panda subdial layouts.
 const bezel=[r.bezel_color,r.bezel_material,...(r.extra_specs||[]).filter(x=>/bezel/i.test(x.label)).map(x=>x.value)].join(' ');
 if(r.brand==='Rolex'&&/gmt/i.test(r.parent_model+' '+r.collection_label)&&(/red/i.test(bezel)&&/blue/i.test(bezel)||/blro/i.test(r.reference_number)))aliasText.push('Pepsi');
 if(/\bpanda\b/i.test(r.dial_color+' '+r.nickname))aliasText.push('Panda');
 const hz=number(r.frequency,'hz');const vph=/([\d,]+)\s*(?:vph|semi.oscillations|vibrations)/i.exec(r.frequency||'');
 return {width:number(r.between_lugs,'mm'),weight:(()=>{const match=/^(\d+(?:\.\d+)?)\s*(?:g|grams?)$/i.exec(clean(r.weight));return match?+match[1]:null;})(),facets:f,diameter:r.diameter_metric_eligible===false||r.watch_kind==='Pocket watch'?null:number(r.diameter,'mm'),thickness:number(r.case_thickness,'mm'),lug: number(r.lug_to_lug,'mm'),reserve:number(r.power_reserve,'h'),water:water(r.water_resistance),frequency:hz??(vph?Number(vph[1].replace(/,/g,''))/7200:null),jewels:number(r.jewels,'j'),aliases:aliasText.filter(Boolean).join(' '),reference:compact(r.reference_number),captured:r.captured_at||r.captured_date||'',production:f.production[0]||null,status:f.status[0]};
}
const numeric={price:'Price',diameter:'Diameter',thickness:'Thickness',lug:'Lug to lug',reserve:'Power reserve',water:'Water resistance',frequency:'Frequency',jewels:'Jewels'};
const sorts={'relevance':'Relevance','price-asc':'Price: low to high','price-desc':'Price: high to low','diameter-asc':'Diameter: small to large','diameter-desc':'Diameter: large to small',newest:'Latest catalog capture','brand':'Watchmaker A–Z'};
function read(params){const p=params instanceof URLSearchParams?params:new URLSearchParams(params);const s={q:(p.get('q')||'').slice(0,240),sort:sorts[p.get('sort')]?p.get('sort'):'relevance',page:Math.max(1,Math.min(5000,parseInt(p.get('page'),10)||1)),currency:/^[A-Z]{3}$/.test(p.get('currency')||'')?p.get('currency'):'USD',source:/^[a-z][a-z0-9_-]{0,63}$/.test(p.get('source')||'')?p.get('source'):'official_retail',complicationsMode:p.get('complicationsMode')==='any'?'any':'all'};
 for(const key of Object.keys(facets)){const values=[...new Set(p.getAll(key).map(clean).filter(Boolean))].slice(0,20);if(values.length)s[key]=values.map(x=>x.slice(0,100)).sort();}
 for(const key of Object.keys(numeric))for(const bound of ['min','max','lt','gt']){const raw=p.get(key+'.'+bound);if(raw!==null&&raw.trim()!==''&&Number.isFinite(+raw)&&+raw>=0)s[key+'.'+bound]=+raw;}
 return s;}
function serialize(s){const p=new URLSearchParams();if(s.q)p.set('q',s.q);for(const key of Object.keys(facets))for(const value of [...s[key]||[]].sort())p.append(key,value);for(const key of Object.keys(numeric))for(const bound of ['min','max','lt','gt'])if(s[key+'.'+bound]!=null)p.set(key+'.'+bound,s[key+'.'+bound]);if(s.sort&&s.sort!=='relevance')p.set('sort',s.sort);if(s.page>1)p.set('page',s.page);if(s.currency!=='USD')p.set('currency',s.currency);if(s.source!=='official_retail')p.set('source',s.source);if(s.complicationsMode==='any')p.set('complicationsMode','any');return p;}
function parse(query,vocabulary={}){
 let residual=fold(query),filters={},notes=[],interpreted=[];
 if(/\b(?:not|without|except)\b/.test(residual))return {filters,text:residual,interpreted,notes:['Negation is searched literally. Use explicit filter controls to avoid assumptions about undocumented values.']};
 function consume(re,fn){residual=residual.replace(re,(...args)=>{const value=fn(...args);return value===false?args[0]:' ';});}
 const amount='([0-9]+(?:,[0-9]{3})*(?:\\.[0-9]+)?)(k)?';
 const relation='(under|below|less than|at most|up to|over|above|at least|minimum|more than|with)?\\s*';
 function bound(op){return /^(under|below|less than)$/.test(op)?'lt':/^(over|above|more than)$/.test(op)?'gt':/^(at least|minimum|with)$/.test(op)?'min':'max';}
 function add(key,val,phrase){filters[key]=val;interpreted.push({key,value:val,phrase});}
 consume(new RegExp(relation+'(?:([$€£])\\s*|\\b(usd|eur|gbp|chf|inr)\\s*)'+amount,'gi'),(all,op,symbol,currency,value,k)=>{add('price.'+bound(op||'at most'),+value.replace(/,/g,'')*(k?1000:1),all);filters.currency=currency?.toUpperCase()||({'$':'USD','€':'EUR','£':'GBP'}[symbol]);return true;});
 // Natural ranges are distinct from ambiguous source ranges (which stay unknown).
 consume(/\b(?:between\s+)?(\d+(?:\.\d+)?)\s*(?:–|-|to|and)\s*(\d+(?:\.\d+)?)\s*mm\b/g,(all,a,b)=>{if(+b<+a)return false;add('diameter.min',+a,all);add('diameter.max',+b,all);return true;});
 consume(new RegExp(relation+amount+'\\s*(mm|millimeters?|millimetres?|hours?|hrs?|h|meters?|metres?|m|bar|atm|hz|jewels?)\\b(?:\\s*(thick|thickness|diameter|wide|power reserve|water resistance|wr))?(\\+)?','gi'),(all,op,value,k,unit,qualifier,plus)=>{
  let field=/^mm|^mill/.test(unit)?(/thick/.test(qualifier||'')||/thick\s*$/.test(residual.slice(0,residual.indexOf(all)))?'thickness':'diameter'):/^h/.test(unit)?'reserve':/^hz/.test(unit)?'frequency':/^j/.test(unit)?'jewels':'water';
  // Frequency must be checked before the hours prefix.
  if(unit==='hz')field='frequency';let n=+value.replace(/,/g,'')*(k?1000:1);if(/bar|atm/.test(unit))n*=10;
  add(field+'.'+(plus?'min':op?bound(op):['reserve','water','frequency','jewels'].includes(field)?'min':'max'),n,all);return true;
 });
 const identity=[];for(const group of ['brand','collection'])for(const value of vocabulary[group]||[])identity.push({term:typeof value==='string'?value:value.value,group,value:typeof value==='string'?value:value.value});
 const entries=[...identity,...aliases,...Object.entries(terms).filter(([g])=>!['strap','shape','kind'].includes(g)).flatMap(([group,values])=>Object.entries(values).flatMap(([value,words])=>words.map(term=>({term,group,value}))))].sort((a,b)=>b.term.length-a.term.length);
 for(const entry of entries){const re=pattern(entry.term);if(!re.test(residual))continue;if(entry.group){filters[entry.group]=[...new Set([...(filters[entry.group]||[]),entry.value])];interpreted.push({key:entry.group,value:entry.value,phrase:entry.term});residual=residual.replace(re,' ');}else residual=residual.replace(re,entry.text);}
 // Soft words are removed only after actual constraints have been recognized.
 residual=residual.replace(/\b(show me|find me|watches|watch|with|and|at least|power reserve|water resistance|wr|case|winding|thick|below|under|at|least|a|an|the|of)\b/g,' ').replace(/\s+/g,' ').trim();
 if(/\bthin\b/.test(residual)){notes.push('“Thin” is subjective; set a thickness limit to make it precise.');residual=residual.replace(/\bthin\b/g,'').trim();}
 if(/\b(?:not|without|except|or)\b/.test(residual))notes.push('Negation and mixed OR expressions need the filter controls; remaining words are searched literally.');
 if(!/[a-z0-9]/i.test(residual))residual='';
 return {filters,text:residual,interpreted,notes};
}
const api={clean,fold,compact,facets,terms,aliases,numeric,sorts,normalize,number,water,read,serialize,parse};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AtlasFinderModel=api;
})(globalThis);
