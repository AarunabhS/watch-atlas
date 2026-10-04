/* Local integration preview. No search occurs without a server-side Serper key. */
import http from 'node:http';import {readFile} from 'node:fs/promises';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {DatabaseSync} from 'node:sqlite';import {createFinderService,sqliteAdapter} from '../backend/finder-service.mjs';
import catalog from '../backend/catalog.mjs';import {createPriceService} from '../backend/price-service.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../dist'),port=Number(process.env.ATLAS_PREVIEW_PORT||8787),origin=`http://127.0.0.1:${port}`;
function limiter(limit){const counts=new Map();return {async limit({key}){const minute=Math.floor(Date.now()/60000);const counter=counts.get(key);const n=counter?.minute===minute?counter.count+1:1;counts.set(key,{minute,count:n});for(const [k,c]of counts)if(c.minute<minute)counts.delete(k);return {success:n<=limit};}};}
const entries=new Map(),cache={async match(key){const e=entries.get(typeof key==='string'?key:key.url);if(e&&e.until>Date.now())return e.response.clone();},async put(key,response){const seconds=Number(/max-age=(\d+)/.exec(response.headers.get('Cache-Control'))?.[1]||0);entries.set(typeof key==='string'?key:key.url,{response:response.clone(),until:Date.now()+seconds*1000});}};
const env={SERPER_API_KEY:process.env.SERPER_API_KEY,ALLOWED_ORIGINS:origin,LOOKUP_LIMITER:limiter(6),SEARCH_BUDGET:limiter(30)},handle=createPriceService({catalog,cache});
const finderDb=new DatabaseSync(path.resolve(root,'../.finder/catalog.sqlite'),{readOnly:true}),finderHandle=createFinderService({database:sqliteAdapter(finderDb)});
const types={'.html':'text/html','.js':'text/javascript','.json':'application/json','.css':'text/css'};
const server=http.createServer(async(req,res)=>{
 try{
  const url=new URL(req.url,origin);
  if(url.pathname.startsWith('/v1/')){
   const request=new Request(url,{method:req.method,headers:{...req.headers,Origin:req.headers.origin||origin,'CF-Connecting-IP':req.socket.remoteAddress||'local'}});
   const result=await (url.pathname.startsWith('/v1/finder/')?finderHandle:handle)(request,env,{waitUntil:p=>p.catch(()=>{})});res.writeHead(result.status,Object.fromEntries(result.headers));res.end(await result.text());return;
  }
  if(req.method!=='GET'){res.writeHead(405);res.end();return;}
  if(url.pathname==='/config.js'){res.writeHead(200,{'Content-Type':'text/javascript','Cache-Control':'no-store'});res.end(`window.ATLAS_CONFIG=Object.freeze({finderApiBase:${JSON.stringify(origin)},priceApiBase:${JSON.stringify(origin)},priceCountry:'us'});`);return;}
  const file=path.resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));
  if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
  const body=await readFile(file);res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(body);
 }catch{res.writeHead(404);res.end('Not found');}
});
server.listen(port,'127.0.0.1',()=>console.log(`Watch Atlas + indexed Finder + price API preview: ${origin}/#finder\nSerper: ${env.SERPER_API_KEY?'connected':'not configured; lookups return a Google fallback'}`));
