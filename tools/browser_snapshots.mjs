// Sequential normal-browser snapshots. No stealth, proxies, CAPTCHA handling or parallel pages.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {createRequire} from 'node:module';import {robotsAllowed} from './robots_rules.mjs';
const args=Object.fromEntries(process.argv.slice(2).reduce((a,x,i,v)=>(x.startsWith('--')&&a.push([x.slice(2),v[i+1]]),a),[]));
const folder=args.output;if(!folder||!args.queue||!args.origin)throw new Error('output, queue and origin required');
const require=createRequire(import.meta.url);const {chromium}=require(args.playwright||'playwright');
fs.mkdirSync(path.join(folder,'snapshots'),{recursive:true});
const metaFile=path.join(folder,'browser_cache.json');const cache=fs.existsSync(metaFile)?JSON.parse(fs.readFileSync(metaFile)):{};
const rules=args.robots?JSON.parse(fs.readFileSync(args.robots)).rules:null;
const queue=JSON.parse(fs.readFileSync(args.queue));const origin=new URL(args.origin).origin;const delay=Math.max(3000,Number(args.delay||3)*1000);
const save=()=>{fs.writeFileSync(metaFile+'.tmp',JSON.stringify(cache,null,2));fs.renameSync(metaFile+'.tmp',metaFile)};
const browser=await chromium.launch({executablePath:args.chrome||undefined,headless:true});const context=await browser.newContext();const page=await context.newPage();
await context.route('**/*',async route=>{const request=route.request();if(request.isNavigationRequest()&&request.frame()===page.mainFrame()){const u=new URL(request.url());if(u.origin!==origin||(rules&&!robotsAllowed(u.href,rules))){return route.abort('blockedbyclient')}}if(['image','media','font'].includes(request.resourceType()))return route.abort();return route.continue()});
let last=0;
try{
 for(const item of queue){
  const url=item.url;const parsed=new URL(url);if(parsed.origin!==origin||parsed.protocol!=='https:')throw new Error('Queue outside official HTTPS origin');
  if(rules&&!robotsAllowed(url,rules))throw new Error('Robots denied: '+url);
  if(!rules&&parsed.pathname!=='/robots.txt')throw new Error('Robots preflight required');
  const existing=cache[url];if(existing&&Date.now()/1000-existing.fetched_epoch<86400){const body=fs.readFileSync(path.join(folder,'snapshots',existing.sha256));if(crypto.createHash('sha256').update(body).digest('hex')!==existing.sha256)throw new Error('Cache integrity failure');console.log('Cached '+url);continue;}
  const pause=last+delay-Date.now();if(pause>0)await new Promise(r=>setTimeout(r,pause));last=Date.now();
  let response;for(let attempt=0;attempt<2;attempt++){try{response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});break}catch(e){if(attempt===1)throw e;await new Promise(r=>setTimeout(r,5000));}}
  const status=response?.status();const title=await page.title();if([401,403,429,451].includes(status)||/access denied|just a moment|verify you are human/i.test(title)){fs.writeFileSync(path.join(folder,'browser_block.json'),JSON.stringify({url,status,title,captured_at:new Date().toISOString()}));throw new Error('Access block; collection stopped: '+status+' '+title)}
  if(status!==200)throw new Error('Unexpected HTTP '+status+' '+url);
  if(item.selector)await page.waitForSelector(item.selector,{state:'attached',timeout:15000});
  const body=parsed.pathname==='/robots.txt'?await page.locator('body').innerText():await page.content();
  const sha256=crypto.createHash('sha256').update(body).digest('hex');fs.writeFileSync(path.join(folder,'snapshots',sha256),body);
  cache[url]={url:page.url(),status,sha256,fetched_at:new Date().toISOString(),fetched_epoch:Date.now()/1000,representation:'rendered_dom'};save();console.log(`${Object.keys(cache).length} snapshots: ${url}`);
 }
}catch(e){fs.writeFileSync(path.join(folder,'browser_error.json'),JSON.stringify({error:String(e),captured_at:new Date().toISOString()}));console.error(e.message);process.exitCode=2;}finally{await browser.close();}
