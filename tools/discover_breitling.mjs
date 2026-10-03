// Browser discovery only: follow the site's pagination and save rendered DOM.
// The Python collector checks robots before invoking this script.
import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {robotsAllowed} from './robots_rules.mjs';

const options = Object.fromEntries(process.argv.slice(2).reduce((a,x,i,args) => i%2===0 ? [...a,[x.slice(2),args[i+1]]] : a,[]));
const require = createRequire(import.meta.url);
const {chromium} = require(options.playwright || 'playwright');
const folder = path.resolve(options.output,'rendered_pages');
await fs.mkdir(folder,{recursive:true});
const origin = 'https://www.breitling.com';
const finder = origin + '/us-en/watches/all/';
const delay = Math.max(3000,Number(options.delay || 3)*1000);
const userAgent = 'WatchAtlasCatalogBot/1.0 (+https://github.com/AarunabhS/watch-atlas)';
// Rules are compiled by the shared Python robots parser before browser launch.
const robotsRules=JSON.parse(await fs.readFile(options.robots || path.join(folder,'robots_rules.json'),'utf8')).rules;
const launch = {headless:true,chromiumSandbox:true};
if(options.chrome) launch.executablePath = options.chrome;
const browser = await chromium.launch(launch);
const context = await browser.newContext({userAgent,locale:'en-US',viewport:{width:1440,height:1000}});
// Watch images are linked in the data, not downloaded for discovery.
await context.route('**/*',route => ['image','media','font'].includes(route.request().resourceType()) ? route.abort() : route.continue());
const page = await context.newPage();
let denied = null;
let robotsDenied = null;
page.on('response',response => {
  const request=response.request();
  if(['document','xhr','fetch'].includes(request.resourceType()) && [401,403,429,451].includes(response.status())) {
    const host=new URL(response.url()).hostname;
    if(host==='www.breitling.com' || host.includes('algolia')) denied={url:response.url().split('?')[0],status:response.status()};
  }
});
const pages=[];
const references=new Set();
try {
  if(!robotsAllowed(finder,robotsRules)) {
    robotsDenied=finder;
    throw new Error('Catalog disallowed by robots');
  }
  const response=await page.goto(finder,{waitUntil:'domcontentloaded',timeout:45000});
  if(response.status()!==200) throw new Error('Catalog document HTTP '+response.status());
  await page.waitForFunction(() => Array.from(document.querySelectorAll('[data-test-id="ListingHitsWatchesGrid"] button')).some(x=>x.textContent.trim().toUpperCase()==='ADD TO BAG'&&!x.disabled),null,{timeout:30000});
  const cookieReject=page.getByRole('button',{name:/^Reject All(?: Cookies)?$/i});
  if(await cookieReject.count() && await cookieReject.first().isVisible()) await cookieReject.first().click();
  const info=await page.evaluate(() => {
    const p=JSON.parse(document.querySelector('#__NEXT_DATA__').textContent).props.pageProps;
    const r=Object.values(p.serverState.initialResults)[0].results[0];
    return {expected:r.nbHits,declared_page_count:r.nbPages,hitsPerPage:r.hitsPerPage};
  });
  let lastAction=Date.now();
  for(let number=1;number<=info.declared_page_count;number++) {
    if(denied) throw new Error('Access block: '+JSON.stringify(denied));
    const dom=await page.evaluate(() => {
      const grid=document.querySelector('[data-test-id="ListingHitsWatchesGrid"]');
      return {html:document.documentElement.outerHTML,
              references:Array.from(grid.querySelectorAll('[data-test-id="Sku"]')).map(x=>x.textContent.trim())};
    });
    const expectedHere=Math.min(info.hitsPerPage,info.expected-(number-1)*info.hitsPerPage);
    if(dom.references.length!==expectedHere || new Set(dom.references).size!==expectedHere) throw new Error('Wrong card count on page '+number);
    for(const ref of dom.references) {
      if(references.has(ref)) throw new Error('Repeated reference across pages: '+ref);
      references.add(ref);
    }
    const file=number+'.html';
    await fs.writeFile(path.join(folder,file),dom.html,'utf8');
    pages.push({page:number-1,url:page.url(),file,sha256:crypto.createHash('sha256').update(dom.html).digest('hex'),
                captured_at:new Date().toISOString(),kind:'rendered_dom',references:dom.references});
    console.log('Browser listing '+number+'/'+info.declared_page_count+': '+references.size+'/'+info.expected+' references');
    if(number<info.declared_page_count) {
      const next=page.getByRole('link',{name:'Go to page '+(number+1),exact:true}).first();
      const href=await next.getAttribute('href');
      const u=new URL(href,origin);
      if(u.origin!==origin || u.pathname!=='/us-en/watches/all/' || u.searchParams.get('page')!==String(number+1)) throw new Error('Unexpected pagination target');
      if(!robotsAllowed(u.href,robotsRules)) {
        robotsDenied=u.href;
        throw new Error('Pagination disallowed by robots');
      }
      const remaining=delay-(Date.now()-lastAction);
      if(remaining>0) await page.waitForTimeout(remaining);
      const previous=dom.references[0];
      await next.click();
      lastAction=Date.now();
      await page.waitForFunction(({previous,number}) => {
        const first=document.querySelector('[data-test-id="ListingHitsWatchesGrid"] [data-test-id="Sku"]');
        return first&&first.textContent.trim()!==previous&&new URL(location.href).searchParams.get('page')===String(number);
      },{previous,number:number+1},{timeout:30000});
    }
  }
  if(references.size!==info.expected) throw new Error('Catalog reference count mismatch');
  const manifest={...info,complete:true,captured_epoch:Date.now()/1000,pages,document_status:response.status(),
                  method:'headless browser, public catalog pagination, rendered DOM'};
  await fs.writeFile(path.join(folder,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
} catch(error) {
  await fs.writeFile(path.join(folder,'discovery_error.json'),JSON.stringify({error:error.message,denied,robots_denied:robotsDenied,pages},null,2)+'\n');
  console.error(error.message);
  process.exitCode=2;
} finally {
  await context.close();
  await browser.close();
}
