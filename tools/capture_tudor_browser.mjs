// Tudor only: five published catalogue pages, then the references in their public JSON.
// One normal browser page, >=3 seconds between requests, cache/resume, no reference guessing.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {robotsAllowed} from './robots_rules.mjs';

const args = Object.fromEntries(process.argv.slice(2).filter((_,i,a)=>i%2===0).map((x,i)=>[x.replace(/^--/,''),process.argv.slice(2)[i*2+1]]));
const folder = args.output || 'scraping_runs/tudor-in-capture';
if (!args.robots) throw Error('--robots must point to the current compiled Tudor robots rules');
const rules = JSON.parse(fs.readFileSync(args.robots,'utf8')).rules;
const delay = Math.max(3000,Number(args.delay || 3)*1000);
const origin = 'https://www.tudorwatch.com';
const catalog = origin+'/en/watches';
const allowed = url => {
  const u = new URL(url);
  return u.origin===origin && !u.search && !u.hash &&
    /^\/en\/(?:watches(?:\/page\/[1-9]\d*|\/[a-z0-9-]+\/m[a-z0-9]+-\d{4})?|watch-family\/daring-watches\/m[a-z0-9]+-\d{4})$/.test(u.pathname) && robotsAllowed(url,rules);
};
fs.mkdirSync(path.join(folder,'snapshots'),{recursive:true});
const cachePath = path.join(folder,'browser_cache.json');
const cache = fs.existsSync(cachePath) ? JSON.parse(fs.readFileSync(cachePath,'utf8')) : {};
const saveCache = () => {fs.writeFileSync(cachePath+'.tmp',JSON.stringify(cache,null,2));fs.renameSync(cachePath+'.tmp',cachePath);};
const require = createRequire(import.meta.url);
const {chromium} = require(args.playwright || 'playwright');
const connected = Boolean(args.cdp);
const browser = connected ? await chromium.connectOverCDP(args.cdp) : await chromium.launch({executablePath:args.chrome,headless:args.headless==='true'});
const context = connected ? browser.contexts()[0] : await browser.newContext();
const page = await context.newPage();
let last = 0;
await page.route('**/*',async route=>{
  const r=route.request();
  if(r.isNavigationRequest() && r.frame()===page.mainFrame() && !allowed(r.url()))return route.abort('blockedbyclient');
  return route.continue();
});

async function get(url,selector) {
  if(!allowed(url))throw Error('Outside Tudor watch/robots scope: '+url);
  if(cache[url] && args.refresh!=='true' && Date.now()-Date.parse(cache[url].fetched_at)<86400000) {
    const body=fs.readFileSync(path.join(folder,'snapshots',cache[url].sha256),'utf8');
    if(crypto.createHash('sha256').update(body).digest('hex')!==cache[url].sha256)throw Error('Cache integrity failure');
    return body;
  }
  const pause=last+delay-Date.now();
  if(pause>0)await new Promise(r=>setTimeout(r,pause));
  last=Date.now();
  const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
  const status=response?.status(), title=await page.title();
  if(status!==200 || /access denied|verify you are human|just a moment/i.test(title))throw Error('Access blocked or unexpected response: '+status+' '+url);
  await page.locator(selector).waitFor({state:'attached',timeout:15000});
  const body=await page.content();
  const sha256=crypto.createHash('sha256').update(body).digest('hex');
  fs.writeFileSync(path.join(folder,'snapshots',sha256),body);
  cache[url]={url:page.url(),requested_url:url,status,sha256,fetched_at:new Date().toISOString(),representation:'rendered_dom',transport:'normal Playwright browser'};
  saveCache();
  console.log(Object.keys(cache).length+' saved pages: '+url);
  return body;
}

function catalogue(body) {
  const match=body.match(/<script[^>]*>(window\[Symbol\.for\("InstantSearchInitialResults"\)\] = [\s\S]*?)<\/script>/);
  if(!match)throw Error('Published Tudor catalogue JSON missing');
  const data=JSON.parse(match[1].slice(match[1].indexOf('=')+1).trim().replace(/;\s*$/,'' )).prd_catalog;
  if(!('allPrices.IN.rawPrice' in data.state.numericRefinements))throw Error('Expected India prices; select India on the normal website before collecting');
  const results=data.results[0];
  const pagers=[...body.matchAll(/href="(\/en\/watches(?:\/page\/[1-9]\d*)?)"/g)].map(m=>origin+m[1]);
  return {results,pagers:[...new Set(pagers)]};
}

try {
  const pending=[catalog],seen=new Set(),items=new Map();
  let expected,nbPages;
  while(pending.length) {
    const url=pending.shift();if(seen.has(url))continue;seen.add(url);
    const {results,pagers}=catalogue(await get(url,'main h1'));
    if(expected===undefined){expected=results.nbHits;nbPages=results.nbPages;}
    if(expected!==results.nbHits || nbPages!==results.nbPages)throw Error('Catalogue changed while collecting');
    for(const h of results.hits){if(items.has(h.cleanRmc))throw Error('Duplicate reference in pagination');items.set(h.cleanRmc,h);}
    pending.push(...pagers.filter(u=>!seen.has(u)));
  }
  if(items.size!==expected || seen.size!==nbPages)throw Error('Incomplete published catalogue');
  for(const h of items.values())await get(origin+'/en/watches/'+h.familySlug+'/'+h.cleanRmc,'#full-specifications');
  console.log('Complete: '+items.size+' Tudor product pages. Run tools/capture_tudor_in.py to export and validate.');
} catch(error) {
  fs.writeFileSync(path.join(folder,'browser_error.json'),JSON.stringify({error:String(error),captured_at:new Date().toISOString()}));
  console.error(error.message);process.exitCode=2;
} finally {
  await page.close();
  await browser.close(); // A CDP connection disconnects; a browser launched here closes.
}
