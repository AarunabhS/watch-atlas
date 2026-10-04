import test from 'node:test';import assert from 'node:assert/strict';
import {createPriceService,choosePrices,extractPrice,reportedDate} from '../backend/price-service.mjs';
import catalog from '../backend/catalog.mjs';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),data=require('../dist/data.json');
const watch={brand:'IWC',reference:'IW659803',model:'Fixture watch'},now=Date.parse('2026-10-04T12:00:00Z');
const item=(patch={})=>({title:'IWC IW659803 watch',snippet:'IWC IW659803 price USD 6,500. Available to order.',link:'https://retailer.example/iwc/iw659803',date:'Oct 1, 2026',position:1,...patch});
const env={SERPER_API_KEY:'fixture-secret',ALLOWED_ORIGINS:'https://www.arunabhosom.com',LOOKUP_LIMITER:{limit:async()=>({success:true})},SEARCH_BUDGET:{limit:async()=>({success:true})}};
const request=(query='id=fixture&country=us',headers={})=>new Request('https://prices.example/v1/price?'+query,{headers:{Origin:'https://www.arunabhosom.com','CF-Connecting-IP':'192.0.2.1',...headers}});
function setup(fetcher){const entries=new Map(),pending=[],cache={async match(key){return entries.get(typeof key==='string'?key:key.url)?.clone();},async put(key,response){entries.set(typeof key==='string'?key:key.url,response.clone());}};const ctx={waitUntil(p){pending.push(p);}};return {entries,cache,pending,ctx,handle:createPriceService({catalog:{fixture:watch},fetcher,cache,now:()=>now})};}
test('only eligible catalog identities can generate paid queries',()=>{
 const eligible=data.records.filter(r=>r.is_watch&&r.price_value==null&&r.reference_number?.length>=3);assert.equal(Object.keys(catalog).length,eligible.length);for(const r of eligible)assert.equal(catalog[r.id].reference,r.reference_number);
});
test('price extraction supports clear currencies and preserves ambiguous dollar signs',()=>{
 assert.deepEqual(extractPrice('Retail USD 6,500'),{amount:6500,currency:'USD',raw:'USD 6,500'});assert.equal(extractPrice('INR 1,50,000').amount,150000);assert.equal(extractPrice('CHF 8,500').currency,'CHF');assert.equal(extractPrice('$6,500').currency,null);assert.equal(extractPrice('6,500 EUR').currency,'EUR');
});
test('ranges, monthly payments, discounts, starting prices and multiple amounts are rejected',()=>{
 for(const s of ['USD 5,000 - 6,000','USD 5,000 to 6,000','USD 200 per month','Save USD 500','From USD 5,000','USD 6,500 or USD 7,500','USD 6,500. EUR 6,000','USD 6,90'])assert.equal(extractPrice(s),null,s);
});
test('matching rejects other references, accessories, unsafe links and unidentified snippets',()=>{
 const rejected=[item({snippet:'IWC IW659804 price USD 6,500.'}),item({title:'IWC IW659804 watch',snippet:'IWC IW659804 price USD 6,500.'}),item({title:'Replacement watch strap for IWC IW659803'}),item({link:'javascript:alert(1)'}),item({link:'https://user:pass@retailer.example/watch'}),item({snippet:'Prices USD 6,500.',link:'https://retailer.example/iwc/collection'}),item({title:'IWC IW6598030 watch',snippet:'IWC IW6598030 price USD 6,500.'})];
 assert.equal(choosePrices({organic:rejected},watch,now).length,0);
});
test('a precise product title and URL can identify snippets without repeated references',()=>{const hits=choosePrices({organic:[item({snippet:'Pre-owned IWC watch. USD 6,500.'})]},watch,now);assert.equal(hits.length,1);assert.equal(hits[0].condition,'Pre-owned listing');});
test('mixed retail and used-price wording does not imply a pre-owned offer',()=>{const hits=choosePrices({organic:[item({snippet:'IWC IW659803 MSRP USD 6,500. Real specs, real used prices.'})]},watch,now);assert.equal(hits[0].condition,'Condition / price basis unspecified');});
test('newest dated exact result wins and undated sources do not get a fabricated date',()=>{
 const hits=choosePrices({organic:[item({date:'Sep 1, 2026',link:'https://a.example/watch',position:1}),item({date:undefined,link:'https://b.example/watch',position:2}),item({date:'Oct 3, 2026',link:'https://c.example/watch',position:3})]},watch,now);
 assert.equal(hits[0].source_date,'2026-10-03');assert.equal(hits[2].source_date,null);assert.equal(reportedDate('2 days ago',now),'2026-10-02');assert.equal(reportedDate('Oct 5, 2026',now),null);assert.equal(reportedDate('2026',now),null);
});
test('fresh cache returns without another paid search and keeps currency/provenance',async()=>{
 let calls=0;const s=setup(async(url,options)=>{calls++;assert.equal(url,'https://google.serper.dev/search');assert.ok(JSON.parse(options.body).q.includes('"IW659803"'));return Response.json({organic:[item()]});});
 const first=await (await s.handle(request(),env,s.ctx)).json();await Promise.all(s.pending);const start=performance.now();const second=await (await s.handle(request(),env,s.ctx)).json();assert.equal(calls,1);assert.equal(first.cached,false);assert.equal(second.cached,true);assert.equal(second.prices[0].currency,'USD');assert.ok(performance.now()-start<1000);assert.ok(!JSON.stringify(second).includes('fixture-secret'));
});
test('simultaneous clicks share a single paid search in a worker instance',async()=>{
 let calls=0;const s=setup(async()=>{calls++;await new Promise(resolve=>setTimeout(resolve,20));return Response.json({organic:[item()]});});await Promise.all([s.handle(request(),env,s.ctx),s.handle(request(),env,s.ctx)]);assert.equal(calls,1);
});
test('no-result searches are cached for fifteen minutes',async()=>{
 let calls=0;const s=setup(async()=>{calls++;return Response.json({organic:[]});});const first=await (await s.handle(request(),env,s.ctx)).json();await Promise.all(s.pending);await s.handle(request(),env,s.ctx);assert.equal(first.status,'not_found');assert.equal(Date.parse(first.expires_at)-now,900000);assert.equal(calls,1);
});
test('expired saved prices return immediately while refresh runs in background',async()=>{
 let release;const s=setup(()=>new Promise(resolve=>{release=resolve;}));await s.cache.put('https://prices.example/cached-price/v2/fixture/us',Response.json({status:'found',prices:[item()],expires_at:'2026-10-01T00:00:00Z',checked_at:'2026-09-30T00:00:00Z'}));
 const result=await (await s.handle(request(),env,s.ctx)).json();assert.equal(result.cached,true);assert.equal(result.stale,true);release(Response.json({organic:[item()]}));await Promise.all(s.pending);
});
test('unknown watches and disallowed origins never reach the provider',async()=>{
 let calls=0;const s=setup(async()=>{calls++;return Response.json({organic:[]});});assert.equal((await s.handle(request('id=made-up'),env,s.ctx)).status,400);assert.equal((await s.handle(request('id=fixture',{Origin:'https://bad.example'}),env,s.ctx)).status,403);assert.equal((await s.handle(request('id=fixture&country=zz'),env,s.ctx)).status,400);assert.equal(calls,0);
});
test('missing keys and enforced rate limits return useful errors and a Google fallback',async()=>{
 const s=setup(async()=>{throw new Error('should not run');});const unconfigured=await s.handle(request(),{...env,SERPER_API_KEY:''},s.ctx);assert.equal(unconfigured.status,503);assert.equal((await unconfigured.json()).code,'not_configured');
 const limited=await s.handle(request(),{...env,LOOKUP_LIMITER:{limit:async()=>({success:false})}},s.ctx);assert.equal(limited.status,429);assert.equal(limited.headers.get('Retry-After'),'60');assert.ok((await limited.json()).google_url.startsWith('https://www.google.com/search?'));
});
test('provider errors do not expose credentials or upstream error content',async()=>{
 const s=setup(async()=>new Response('fixture-secret',{status:401}));const response=await s.handle(request(),env,s.ctx);assert.equal(response.status,502);assert.ok(!(await response.text()).includes('fixture-secret'));
});
test('a slow provider is aborted within the configured latency budget',async()=>{
 const s=setup((url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted')))));const start=performance.now();const response=await s.handle(request(),env,s.ctx);assert.equal(response.status,504);assert.ok(performance.now()-start>=7900&&performance.now()-start<9000);assert.equal((await response.json()).code,'timeout');
});
test('CORS preflight allows the website and rejects POST searches',async()=>{
 const s=setup(async()=>Response.json({organic:[]}));const headers={Origin:'https://www.arunabhosom.com'};const response=await s.handle(new Request('https://prices.example/v1/price',{method:'OPTIONS',headers}),env,s.ctx);assert.equal(response.status,204);assert.equal(response.headers.get('Access-Control-Allow-Origin'),headers.Origin);assert.equal((await s.handle(new Request('https://prices.example/v1/price',{method:'POST',headers}),env,s.ctx)).status,405);
});
