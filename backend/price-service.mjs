/* Extract only explicit amounts attached to an exact reference in Google snippets. */
export const countries=['us','in','gb','ch','de','fr','jp','ae','sg','hk'];
export function searchQuery(watch){return `${watch.brand} "${watch.reference}" watch price -replica`;}
export function googleUrl(watch,country='us'){return 'https://www.google.com/search?'+new URLSearchParams({q:searchQuery(watch),gl:country,hl:'en'});}
const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
function exactReference(text,reference){
 const parts=reference.match(/[a-z0-9]+/gi)||[];
 return parts.length>0&&new RegExp('(?<![a-z0-9])'+parts.map(escape).join('[\\s._/–-]*')+'(?![a-z0-9])','i').test(text);
}
function conflictingReference(text,reference){
 const parts=reference.match(/[a-z0-9]+/gi)||[];
 // A bare numeric reference has the same shape as many legitimate prices.
 if(parts.length===1&&/^\d+$/.test(reference))return false;
 const shape=parts.map(part=>[...part].map(c=>/\d/.test(c)?'\\d':'[a-z]').join('')).join('[\\s._/–-]*');
 if(!shape)return false;
 return [...text.matchAll(new RegExp('(?<![a-z0-9])'+shape+'(?![a-z0-9])','gi'))].some(m=>!exactReference(m[0],reference));
}
export function reportedDate(raw,now){
 if(typeof raw!=='string')return null;
 const relative=/^(\d+)\s+(hour|day|week|month|year)s?\s+ago$/i.exec(raw.trim());
 let ms;
 if(relative){const scale={hour:3600000,day:86400000,week:604800000,month:2592000000,year:31536000000};ms=now-Number(relative[1])*scale[relative[2].toLowerCase()];}
 else if(/^\d{4}-\d{2}-\d{2}$/.test(raw.trim()))ms=Date.parse(raw.trim()+'T00:00:00Z');
 else if(/^(?:[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Z][a-z]+\s+\d{4})$/.test(raw.trim()))ms=Date.parse(raw.trim()+' UTC');
 else return null;
 return Number.isFinite(ms)&&ms<=now&&ms>0?new Date(ms).toISOString().slice(0,10):null;
}
const currencyMap={'US$':'USD','USD':'USD','EUR':'EUR','€':'EUR','GBP':'GBP','£':'GBP','CHF':'CHF','INR':'INR','₹':'INR','Rs.':'INR','Rs':'INR','AED':'AED','HKD':'HKD','HK$':'HKD','SGD':'SGD','S$':'SGD','JPY':'JPY'};
export function extractPrice(text){
 const number='(?:\\d{1,3}(?:,\\d{2,3})+|\\d+)(?:\\.\\d{1,2})?';
 const token='US\\$|HK\\$|S\\$|USD|EUR|GBP|CHF|INR|AED|HKD|SGD|JPY|Rs\\.?|[$€£₹¥]';
 const re=new RegExp('(?<![A-Za-z0-9])('+token+')\\s*('+number+')(?!\\d|[,.]\\d)|(?<![\\d.,])('+number+')\\s*(USD|EUR|GBP|CHF|INR|AED|HKD|SGD|JPY)\\b','gi');
 const prices=[];
 for(const m of text.matchAll(re)){
  const raw=m[0],symbol=m[1]||m[4],n=m[2]||m[3],amount=Number(n.replace(/,/g,''));
  const around=text.slice(Math.max(0,m.index-30),m.index+raw.length+35);
  if(!Number.isFinite(amount)||amount<100||/\b(?:per month|monthly|installment|instalment|shipping|deposit|save|discount|off|from|starting at)\b|\/\s*(?:mo|month)|[-–]\s*(?:[$€£₹¥]|\d)|\bto\s*(?:USD|EUR|GBP|CHF|INR|[$€£₹¥])?\s*\d/i.test(around))continue;
  const key=Object.keys(currencyMap).find(k=>k.toUpperCase()===symbol.toUpperCase());
  if(n.includes(',')&&!/^\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?$/.test(n)&&!(currencyMap[key]==='INR'&&/^\d{1,2}(?:,\d{2})*,\d{3}(?:\.\d{1,2})?$/.test(n)))continue;
  prices.push({amount,currency:key?currencyMap[key]:null,raw});
 }
 const unique=[...new Map(prices.map(p=>[(p.currency||p.raw.replace(/[\d.,\s]/g,''))+'|'+p.amount,p])).values()];
 return unique.length===1?unique[0]:null;
}
export function choosePrices(payload,watch,now=Date.now()){
 const organic=Array.isArray(payload.organic)?payload.organic:[];
 const brandWord=watch.brand.match(/[a-z]{3,}/i)?.[0];
 const results=[];
 for(const item of organic.slice(0,10)){
  const title=String(item.title||'').slice(0,240),snippet=String(item.snippet||'').slice(0,1200),evidence=title+' '+snippet;
  let url;try{url=new URL(item.link);if(url.protocol!=='https:'||url.username||url.password)continue;}catch{continue;}
  if(!exactReference(evidence,watch.reference)||!brandWord||!new RegExp('\\b'+escape(brandWord)+'\\b','i').test(evidence))continue;
  if(conflictingReference(snippet,watch.reference))continue;
  if(/\b(?:replica|counterfeit|replacement|watch bands?|watch straps?|box only|parts only)\b|^(?:strap|bracelet|box|buckle)\s+(?:for|compatible)/i.test(title))continue;
  // When snippets omit the reference, require both an exact product title and URL.
  // A title alone cannot identify a multi-product search snippet.
  if(!exactReference(snippet,watch.reference)&&!(exactReference(title,watch.reference)&&exactReference(url.pathname,watch.reference)))continue;
  const price=extractPrice(snippet);if(!price)continue;
  const sourceDate=reportedDate(item.date,now),used=/pre[- ]?owned|used|second[- ]hand/i.test(evidence),retail=/retail|msrp|rrp/i.test(evidence);
  results.push({...price,source_title:title,source_url:url.href,source_domain:url.hostname,source_date:sourceDate,source_date_label:sourceDate?String(item.date):null,snippet,condition:used&&!retail?'Pre-owned listing':retail&&!used?'Reported retail price':'Condition / price basis unspecified',position:Number(item.position)||results.length+1});
 }
 const unique=[...new Map(results.map(p=>[p.source_url,p])).values()];
 return unique.sort((a,b)=>a.source_date&&b.source_date?b.source_date.localeCompare(a.source_date)||a.position-b.position:a.source_date?-1:b.source_date?1:a.position-b.position).slice(0,3);
}
export function createPriceService({catalog,fetcher=fetch,now=Date.now,cache}){
 const inFlight=new Map();
 async function refresh(key,watch,country,env,ctx){
  if(inFlight.has(key))return inFlight.get(key);
  const task=(async()=>{
   if(!env.SERPER_API_KEY)throw Object.assign(new Error('Price search is not connected yet.'),{status:503,code:'not_configured'});
   if(!env.SEARCH_BUDGET)throw Object.assign(new Error('Price search configuration is incomplete.'),{status:503,code:'not_configured'});
   const budget=await env.SEARCH_BUDGET.limit({key:'provider-searches'});
   if(!budget.success)throw Object.assign(new Error('Price search is busy. Please try again shortly.'),{status:429,code:'busy'});
   const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),8000);
   let payload;
   try{
    const response=await fetcher('https://google.serper.dev/search',{method:'POST',headers:{'Content-Type':'application/json','X-API-KEY':env.SERPER_API_KEY},body:JSON.stringify({q:searchQuery(watch),gl:country,hl:'en',num:10}),signal:controller.signal});
    if(!response.ok)throw new Error('Provider unavailable');payload=await response.json();
    if(!Array.isArray(payload.organic))throw new Error('Invalid provider response');
   }catch(error){throw Object.assign(new Error(controller.signal.aborted?'Price search took too long. Try Google directly.':'Price search is temporarily unavailable.'),{status:controller.signal.aborted?504:502,code:controller.signal.aborted?'timeout':'provider_error'});}
   finally{clearTimeout(timer);}
   const checked=now(),prices=choosePrices(payload,watch,checked),ttl=prices.length?6*3600000:15*60000;
   const result={status:prices.length?'found':'not_found',watch,country,prices,checked_at:new Date(checked).toISOString(),expires_at:new Date(checked+ttl).toISOString(),google_url:googleUrl(watch,country),basis:prices[0]?.source_date?'Newest dated result among the matching Google results':'Google result; source date unavailable'};
   if(cache){const write=cache.put(key,new Response(JSON.stringify(result),{headers:{'Content-Type':'application/json','Cache-Control':`public, max-age=${prices.length?7*86400:900}`}})).catch(()=>{});ctx.waitUntil(write);}
   return result;
  })();
  inFlight.set(key,task);try{return await task;}finally{inFlight.delete(key);}
 }
 return async function handle(request,env,ctx){
  const url=new URL(request.url),origin=request.headers.get('Origin')||'';
  const allowed=(env.ALLOWED_ORIGINS||'').split(',').map(s=>s.trim());
  const headers={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Vary':'Origin'};
  if(allowed.includes(origin)&&origin)Object.assign(headers,{'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Methods':'GET, OPTIONS','Access-Control-Allow-Headers':'Content-Type','Access-Control-Max-Age':'86400'});
  const json=(body,status=200,extra={})=>new Response(JSON.stringify(body),{status,headers:{...headers,...extra}});
  if(!origin||!allowed.includes(origin))return json({error:'Origin not allowed',code:'forbidden'},403);
  if(url.pathname!=='/v1/price')return json({error:'Not found'},404);
  if(request.method==='OPTIONS')return new Response(null,{status:204,headers});
  if(request.method!=='GET')return json({error:'Method not allowed'},405,{Allow:'GET, OPTIONS'});
  const id=url.searchParams.get('id'),country=url.searchParams.get('country')||'us',watch=catalog[id];
  if(!Object.hasOwn(catalog,id)||!countries.includes(country)||[...url.searchParams.keys()].some(k=>!['id','country'].includes(k)))return json({error:'Choose a supported watch and search country.'},400);
  const key=new Request(new URL('/cached-price/v2/'+encodeURIComponent(id)+'/'+country,url.origin));
  let cached;try{cached=cache?await cache.match(key):null;}catch{}
  if(cached){
   try{const result=await cached.json();const stale=Date.parse(result.expires_at)<=now();
    if(stale)ctx.waitUntil(refresh(key.url,watch,country,env,ctx).catch(()=>{}));
    return json({...result,cached:true,stale});
   }catch{}
  }
  if(!env.LOOKUP_LIMITER)return json({error:'Price search configuration is incomplete.',code:'not_configured',google_url:googleUrl(watch,country)},503);
  const limit=await env.LOOKUP_LIMITER.limit({key:request.headers.get('CF-Connecting-IP')||'anonymous'});
  if(!limit.success)return json({error:'Too many lookups. Please try again in a minute.',code:'rate_limited',google_url:googleUrl(watch,country)},429,{'Retry-After':'60'});
  try{return json({...await refresh(key.url,watch,country,env,ctx),cached:false,stale:false});}
  catch(error){return json({error:error.message,code:error.code||'provider_error',google_url:googleUrl(watch,country)},error.status||502,error.status===429?{'Retry-After':'60'}:{});}
 };
}
