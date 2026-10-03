// IWC US public catalogue only. Normal browser; sequential navigation and saved DOM.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {robotsAllowed} from './robots_rules.mjs';

const pairs=process.argv.slice(2);
const args=Object.fromEntries(pairs.filter((_,i)=>i%2===0).map((k,i)=>[k.replace(/^--/,''),pairs[2*i+1]]));
const folder=args.output||'scraping_runs/iwc-us-capture';
if(!args.robots)throw Error('--robots must supply reviewed current IWC robots rules');
const rules=JSON.parse(fs.readFileSync(args.robots,'utf8')).rules;
const catalog='https://www.iwc.com/us-en/watches';
const allowed=url=>{const u=new URL(url);return u.origin==='https://www.iwc.com'&&!u.search&&!u.hash&&/^\/us-en\/watches(?:\/[a-z0-9-]+\/iw\d{6}-[a-z0-9-]+)?$/.test(u.pathname)&&robotsAllowed(url,rules);};
const delay=Math.max(3000,Number(args.delay||3)*1000);
fs.mkdirSync(path.join(folder,'snapshots'),{recursive:true});
const cachePath=path.join(folder,'browser_cache.json');
const cache=fs.existsSync(cachePath)?JSON.parse(fs.readFileSync(cachePath,'utf8')):{};
const require=createRequire(import.meta.url);
const {chromium}=require(args.playwright||'playwright');
const browser=args.cdp?await chromium.connectOverCDP(args.cdp):await chromium.launch({executablePath:args.chrome,headless:args.headless==='true'});
const context=args.cdp?browser.contexts()[0]:await browser.newContext();
const page=await context.newPage();
let last=0;
await page.route('**/*',route=>{const req=route.request();if(req.isNavigationRequest()&&req.frame()===page.mainFrame()&&!allowed(req.url()))return route.abort('blockedbyclient');return route.continue();});
async function get(url,selector){
  if(!allowed(url))throw Error('Outside IWC catalogue/robots scope: '+url);
  const saved=cache[url];
  if(saved&&args.refresh!=='true'&&Date.now()-Date.parse(saved.fetched_at)<86400000){
    const body=fs.readFileSync(path.join(folder,'snapshots',saved.sha256),'utf8');
    if(crypto.createHash('sha256').update(body).digest('hex')!==saved.sha256||saved.url!==url)throw Error('Cached source identity/integrity failure');
    return body;
  }
  const pause=last+delay-Date.now();if(pause>0)await new Promise(r=>setTimeout(r,pause));last=Date.now();
  const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
  const status=response?.status();
  if(status!==200||/access denied|verify you are human|just a moment/i.test(await page.title()))throw Error('Blocked or unexpected response: '+status+' '+url);
  await page.locator(selector).waitFor({state:'attached',timeout:15000});
  if(await page.locator('link[rel="canonical"]').getAttribute('href')!==url)throw Error('Canonical identity mismatch');
  const body=await page.content(),sha256=crypto.createHash('sha256').update(body).digest('hex');
  fs.writeFileSync(path.join(folder,'snapshots',sha256),body);
  cache[url]={url:page.url(),requested_url:url,status,sha256,fetched_at:new Date().toISOString(),representation:'rendered_dom',transport:'normal Playwright browser'};
  fs.writeFileSync(cachePath+'.tmp',JSON.stringify(cache,null,2));fs.renameSync(cachePath+'.tmp',cachePath);
  console.log(Object.keys(cache).length+' pages saved: '+url);return body;
}
try{
  const body=await get(catalog,'.phoenix-mixed-grid');
  const urls=[...new Set([...body.matchAll(/href="(https:\/\/www\.iwc\.com\/us-en\/watches\/[a-z0-9-]+\/iw\d{6}-[a-z0-9-]+)"/g)].map(m=>m[1]))];
  if(!urls.length)throw Error('Published catalogue has no product links');
  for(const url of urls.slice(0,args.limit?Number(args.limit):undefined))await get(url,'#tab-overview');
  console.log('Captured published IWC references. Run tools.capture_iwc_us and tools.validate_iwc_us for count reconciliation and exports.');
}catch(error){
  fs.writeFileSync(path.join(folder,'browser_error.json'),JSON.stringify({error:String(error),captured_at:new Date().toISOString()}));console.error(error.message);process.exitCode=2;
}finally{await page.close();await browser.close();}
