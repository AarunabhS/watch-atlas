import C from '../dist/comparison-model.js';
import M from '../dist/finder-model.js';
const size=24,ops={min:'>=',max:'<=',lt:'<',gt:'>'};
export function compile(state,metadata){
 const parsed=M.parse(state.q,metadata.facets);const effective={...state,...parsed.filters,q:parsed.text};
 // Explicit UI / URL filters override interpreted query filters.
 for(const [key,value]of Object.entries(state))if(key in M.facets||key.includes('.'))effective[key]=value;
 if(!/[$€£]|\b(?:USD|EUR|GBP|CHF|INR)\b/i.test(state.q))effective.currency=state.currency;
 const terms=M.fold(effective.q).match(/[a-z0-9]+/g)||[];const reference=M.compact(effective.q);const exact=terms.length&&/\d/.test(reference)?reference:'';
 const where=[],params=[];let join='',cte='',textParams=[];
 if(terms.length){const match=terms.map((t,i)=>'"'+t+'"'+(i===terms.length-1&&t.length>=2?'*':'')).join(' AND ');cte='WITH text_matches AS MATERIALIZED (SELECT rowid,bm25(finder_fts,8,12,6,2,1) AS relevance FROM finder_fts WHERE finder_fts MATCH ?) ';textParams=[match];join=' LEFT JOIN text_matches tm ON tm.rowid=w.rowid';where.push('(w.reference_key = ? OR w.reference_key GLOB ? OR tm.rowid IS NOT NULL)');params.push(exact||'__none__',exact?exact+'*':'__none__');}
 for(const key of Object.keys(M.facets)){const values=effective[key];if(!values?.length)continue;
  if(key==='complication'&&effective.complicationsMode!=='any')for(const value of values){where.push('w.id IN (SELECT watch_id FROM finder_facets WHERE facet=? AND value=?)');params.push(key,value);}
  else{where.push(`w.id IN (SELECT watch_id FROM finder_facets WHERE facet=? AND value IN (${values.map(()=>'?').join(',')}))`);params.push(key,...values);}
 }
 let priceJoin=' LEFT JOIN finder_prices p ON p.watch_id=w.id AND p.source=? AND p.currency=?';const prefix=[effective.source,effective.currency];
 for(const key of Object.keys(M.numeric))for(const bound of Object.keys(ops))if(effective[key+'.'+bound]!=null){where.push((key==='price'?'p.amount':'w.'+key)+' '+ops[bound]+' ?');params.push(effective[key+'.'+bound]);}
 const clause=where.length?' WHERE '+where.join(' AND '):'';
 const from=' FROM finder_watches w'+priceJoin+join+clause;
 const sort={brand:'w.brand COLLATE NOCASE,w.model COLLATE NOCASE',newest:"(w.captured='') ASC,w.captured DESC",'price-asc':'p.amount IS NULL,p.amount ASC','price-desc':'p.amount IS NULL,p.amount DESC','diameter-asc':'w.diameter IS NULL,w.diameter ASC','diameter-desc':'w.diameter IS NULL,w.diameter DESC'};
 const rank=terms.length?'CASE WHEN w.reference_key=? THEN 0 WHEN w.reference_key GLOB ? THEN 1 WHEN w.model_key=? OR lower(w.collection)=? THEN 2 ELSE 3 END, tm.relevance':"(w.status='Historical · unverified') ASC,w.brand COLLATE NOCASE,w.model COLLATE NOCASE";
 const order=sort[effective.sort]||rank;const rankingParams=!sort[effective.sort]&&terms.length?[reference,reference?reference+'*':'__none__',M.fold(effective.q),M.fold(effective.q)]:[];
 return {effective,parsed,count:{sql:cte+'SELECT COUNT(*) AS total'+from,params:[...textParams,...prefix,...params]},results:{sql:cte+'SELECT w.card_json,p.amount AS sort_price,p.source AS price_source,p.currency AS price_currency,p.market AS price_market,p.captured AS price_captured'+from+' ORDER BY '+order+',w.id LIMIT ? OFFSET ?',params:[...textParams,...prefix,...params,...rankingParams,size,(effective.page-1)*size]}};
}
export function createFinderService({database}){
 let metadata,metadataAt=0;async function all(sql,params=[]){const result=await database.prepare(sql).bind(...params).all();return result.results;}
 async function meta(){if(!metadata||Date.now()-metadataAt>30000){metadata=JSON.parse((await all("SELECT value FROM finder_meta WHERE key='catalog'"))[0].value);metadataAt=Date.now();}return metadata;}
 return async function(request,env={}){
  const origin=request.headers.get('Origin'),allowed=(env.ALLOWED_ORIGINS||'').split(',').map(x=>x.trim()).filter(Boolean);
  const headers={'Content-Type':'application/json; charset=utf-8','Cache-Control':'public, max-age=30','Vary':'Origin','X-Content-Type-Options':'nosniff'};
  if(origin&&allowed.includes(origin))headers['Access-Control-Allow-Origin']=origin;
  const reply=(value,status=200)=>new Response(JSON.stringify(value),{status,headers});
  if(origin&&allowed.length&&!allowed.includes(origin))return reply({error:'Origin not allowed'},403);
  if(request.method==='OPTIONS'){headers['Access-Control-Allow-Methods']='GET, OPTIONS';return new Response(null,{status:204,headers});}
  if(request.method!=='GET')return reply({error:'Use GET'},405);
  if(!database)return reply({error:'Watch Finder database is not configured.'},503);
  const url=new URL(request.url);if(url.search.length>8000)return reply({error:'Query is too long'},400);
  try{
   if(url.pathname==='/v1/finder/meta')return reply(await meta());
   if(url.pathname==='/v1/finder/watches'){
    const ids=[...new Set((url.searchParams.get('ids')||'').split(',').filter(Boolean))];if(!ids.length||ids.length>6||ids.some(x=>x.length>100))return reply({error:'Supply one to six watch IDs'},400);
    return reply({watches:(await all(`SELECT record_json FROM finder_watches WHERE id IN (${ids.map(()=>'?').join(',')})`,ids)).map(x=>JSON.parse(x.record_json))});
   }
   if(url.pathname==='/v1/finder/compare'){
    let rules;try{rules=JSON.parse(url.searchParams.get('rules')||'[]');}catch{return reply({error:'Invalid comparison rules'},400);}
    const metadata=await meta(),fields=C.allFields([{extra_specs:(metadata.extraLabels||[]).map(label=>({label,value:''}))}]);
    if(!Array.isArray(rules)||rules.length>12||rules.some(r=>!r||typeof r.value!=='string'||r.value.length>200||C.validateRule(r,fields.find(f=>f.id===r.field))))return reply({error:'Invalid comparison requirements'},400);
    const base=compile(M.read(new URLSearchParams({q:cleanQuery(url.searchParams.get('q'))})),metadata);const where=[],values=[];const unknown=url.searchParams.get('unknown')==='1';
    const mapped={diameter:'w.diameter',case_thickness:'w.thickness',between_lugs:'w.width',weight:'w.weight',lug_to_lug:'w.lug',water_resistance:'w.water',power_reserve:'w.reserve'};
    for(const rule of rules){const field=fields.find(f=>f.id===rule.field);let expression;
     if(rule.field.startsWith('extra:')){expression="(SELECT group_concat(json_extract(value,'$.value'),'; ') FROM json_each(w.record_json,'$.extra_specs') WHERE json_extract(value,'$.label')=?)";}
     else if(rule.field==='price_value')expression="json_extract(w.record_json,'$.price_value')";
     else if(rule.field in mapped&&mapped[rule.field])expression=mapped[rule.field];
     else expression="NULLIF(json_extract(w.record_json,'$."+rule.field+"'),'')";
     if(rule.field==='watch_kind')expression="COALESCE("+expression+",'Wristwatch')";
     if(rule.field==='captured_date')expression="COALESCE(NULLIF(json_extract(w.record_json,'$.captured_label'),''),'2023–2024 archive')";
     if(rule.field==='movement_family')expression="NULLIF("+expression+",'Not specified')";
     if(rule.field==='gemstones')expression="CASE WHEN json_array_length(json_extract(w.record_json,'$.gemstones'))>0 THEN json_extract(w.record_json,'$.gemstones') END";
     const exprParams=rule.field.startsWith('extra:')?[rule.field.slice(6)]:[];
     if(rule.op==='known'){where.push(expression+' IS NOT NULL');values.push(...exprParams);continue;}
     let condition,params=[];
     if(['number','price'].includes(field.type)){condition=expression+' '+({lte:'<=',gte:'>=',eq:'=',between:'BETWEEN'}[rule.op])+' ?';params=[+rule.value];if(rule.op==='between'){condition+=' AND ?';params.push(+rule.value2);}}
     else {condition=rule.op==='equals'?'lower('+expression+')=lower(?)':'instr(lower('+expression+'),lower(?))'+(rule.op==='excludes'?'=0':'>0');params=[rule.value];}
     if(field.type==='price'){condition="("+condition+" AND json_extract(w.record_json,'$.currency')=?)";params.push(rule.currency);}
     where.push('('+expression+(unknown?' IS NULL OR ':' IS NOT NULL AND ')+condition+')');values.push(...exprParams,...exprParams,...params);
    }
    const insert=(sql,extra)=>sql.replace(' ORDER BY ',extra+' ORDER BY ');const extra=(base.count.sql.includes(' WHERE ')?' AND ':' WHERE ')+where.join(' AND ');
    const countSQL=base.count.sql+(where.length?extra:'');const limit=Math.min(96,Math.max(12,parseInt(url.searchParams.get('limit'),10)||12));
    const resultsSQL=insert(base.results.sql.replace('w.card_json','w.record_json'),where.length?extra:'');
    const resultParams=[...base.results.params.slice(0,base.count.params.length),...values,...base.results.params.slice(base.count.params.length,-2),limit,0];
    const [counts,watches]=await Promise.all([all(countSQL,[...base.count.params,...values]),all(resultsSQL,resultParams)]);
    return reply({total:counts[0].total,watches:watches.map(x=>JSON.parse(x.record_json))});
   }
   if(url.pathname==='/v1/finder/suggest'){
    const q=cleanQuery(url.searchParams.get('q'));const metadata=await meta();if(!q)return reply({groups:[]});const parsed=M.parse(q,metadata.facets),compiled=compile(M.read(new URLSearchParams({q})),metadata);
    const watches=(await all(compiled.results.sql,[...compiled.results.params.slice(0,-2),5,0])).map(x=>JSON.parse(x.card_json));
    const prefix=M.fold(q),brands=(metadata.facets.brand||[]).filter(x=>M.fold(x.value).startsWith(prefix)||M.aliases.some(a=>a.group==='brand'&&a.value===x.value&&M.fold(a.term)===prefix)).slice(0,3);
    const collections=await all(compiled.count.sql.replace('SELECT COUNT(*) AS total','SELECT w.collection AS value,w.brand,COUNT(*) AS count')+' GROUP BY w.collection,w.brand ORDER BY count DESC LIMIT 3',compiled.count.params);
    const groups=[{label:'Brands',items:brands.map(x=>({label:x.value,state:{brand:[x.value]}}))},{label:'Collections',items:collections.map(x=>({label:(x.brand?x.brand+' ':'')+x.value,state:{collection:[x.value],...(x.brand?{brand:[x.brand]}:{})}}))},{label:'References',items:watches.map(r=>({label:r.brand+' '+r.reference_number,detail:r.specific_model,state:{q:r.reference_number,brand:[r.brand]}}))},{label:'Suggested searches',items:[{label:q,state:{...parsed.filters,q:parsed.text}},...(brands[0]?[{label:brands[0].value+' watches under 40mm',state:{brand:[brands[0].value],'diameter.lt':40}}]:[])]}].filter(x=>x.items.length);
    return reply({groups,notes:parsed.notes});
   }
   if(url.pathname!=='/v1/finder/search')return reply({error:'Not found'},404);
   const state=M.read(url.searchParams);const compiled=compile(state,await meta());
   if(compiled.results.params.length>90)return reply({error:'Please use fewer selected filter values.'},400);
   for(const key of Object.keys(M.numeric)){const min=compiled.effective[key+'.min']??compiled.effective[key+'.gt'],max=compiled.effective[key+'.max']??compiled.effective[key+'.lt'];if(min!=null&&max!=null&&min>max)return reply({error:`${M.numeric[key]} minimum exceeds maximum`},400);}
   const [counts,records]=await Promise.all([all(compiled.count.sql,compiled.count.params),all(compiled.results.sql,compiled.results.params)]);const total=counts[0].total;
   const relaxations=[];if(!total){for(const key of [...Object.keys(M.facets),...Object.keys(M.numeric).flatMap(k=>['min','max','lt','gt'].map(b=>k+'.'+b))].filter(k=>compiled.effective[k]!=null).slice(0,10)){
     const relaxed={...compiled.effective};delete relaxed[key];const c=compile(relaxed,await meta());const n=(await all(c.count.sql,c.count.params))[0].total;if(n)relaxations.push({key,count:n});if(relaxations.length===3)break;
   }}
   return reply({total,page:state.page,pageSize:size,pages:Math.ceil(total/size),watches:records.map(x=>({...JSON.parse(x.card_json),finder_price:x.sort_price!=null?{amount:x.sort_price,source:x.price_source,currency:x.price_currency,market:x.price_market,captured:x.price_captured}:null})),state:compiled.effective,interpretation:compiled.parsed,relaxations});
  }catch(error){console.error('Finder query failed',error.message);return reply({error:'The watch search could not complete. Please retry.'},500);}
 };
}
const cleanQuery=q=>String(q||'').trim().slice(0,240);
// D1-compatible adapter used by the local preview and SQL integration tests.
export function sqliteAdapter(db){return {prepare(sql){return {bind(...params){return {async all(){return {results:db.prepare(sql).all(...params)};}};}};}};}
