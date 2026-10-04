(function(root){
'use strict';
const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=u=>{try{const x=new URL(u);return x.protocol==='https:'?x.href:'';}catch{return '';}};
const results=new Map(),pending=new Map();
let country=root.ATLAS_CONFIG?.priceCountry||'us';
const countries=[['us','United States'],['in','India'],['gb','United Kingdom'],['ch','Switzerland'],['de','Germany'],['fr','France'],['jp','Japan'],['ae','UAE'],['sg','Singapore'],['hk','Hong Kong']];
const key=r=>r.id+'|'+country;
const google=r=>'https://www.google.com/search?'+new URLSearchParams({q:`${r.brand} "${r.reference_number}" watch price -replica`,gl:country,hl:'en'});
function apiBase(){const raw=root.ATLAS_CONFIG?.priceApiBase||'';try{const u=new URL(raw);return (u.protocol==='https:'||(u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)))?u.origin:'';}catch{return '';}}
function controls(r){
 if(Number.isFinite(r.price_value))return '';
 const ready=!!apiBase(),eligible=r.reference_number?.length>=3;
 return `<div class="price-lookup" data-price-watch="${escape(r.id)}"><p class="tiny-label">REPORTED WEB PRICE</p>${ready&&eligible?`<button class="button price-fetch" data-price-lookup="${escape(r.id)}">Find latest reported price</button>`:`<a class="button price-fetch" href="${escape(google(r))}" target="_blank" rel="noopener noreferrer">Find reported price on Google ↗</a>`}<div class="price-response" role="status" aria-live="polite">${resultMarkup(r)}</div></div>`;
}
function resultMarkup(r){
 const entry=results.get(key(r));
 if(pending.has(key(r)))return '<p class="price-note">Searching Google for this exact reference…</p>';
 if(!entry)return '<p class="price-note">Internet reports may describe retail, resale or pre-owned prices. Check the source and currency.</p>';
 if(entry.error)return `<p class="price-note">${escape(entry.error)}</p><a href="${escape(google(r))}" target="_blank" rel="noopener noreferrer">Search Google directly ↗</a>`;
 const checked=new Date(entry.checked_at).toLocaleString('en-GB',{dateStyle:'medium',timeStyle:'short'});
 if(!entry.prices?.length)return `<p class="price-note">No unambiguous price for this exact reference was found in the search snippets.</p><a href="${escape(google(r))}" target="_blank" rel="noopener noreferrer">View the Google results ↗</a><p class="price-note">Checked ${escape(checked)}</p>`;
 return `<p class="price-note">${entry.stale?'Previously found result · refreshing in the background. ':entry.cached?'Saved search result. ':''}${escape(entry.basis)}. Source dates may differ from the date a price was set.</p>${entry.prices.map((p,i)=>`<div class="reported-price"><strong>${escape(p.currency?p.currency+' '+Number(p.amount).toLocaleString('en-US'):p.raw)}</strong>${!p.currency?'<small>Currency unspecified by source</small>':''}<span>${escape(p.condition)}</span><a href="${escape(safe(p.source_url))}" target="_blank" rel="noopener noreferrer">${escape(p.source_title||p.source_domain)} ↗</a><small>${p.source_date?'Source dated '+escape(p.source_date):'Source date unavailable'}${i===0&&p.source_date?' · newest dated match':''}</small></div>`).join('')}<p class="price-note">Checked ${escape(checked)} · Search country: ${escape(countries.find(x=>x[0]===entry.country)?.[1]||entry.country)}. Reported amounts are unverified and exclude any unstated tax, delivery or condition differences.</p><a href="${escape(google(r))}" target="_blank" rel="noopener noreferrer">All Google results ↗</a>`;
}
function paint(r){document.querySelectorAll('[data-price-watch]').forEach(el=>{if(el.dataset.priceWatch!==r.id)return;el.querySelector('.price-response').innerHTML=resultMarkup(r);const b=el.querySelector('[data-price-lookup]');if(b){b.disabled=pending.has(key(r));b.textContent=b.disabled?'Searching…':'Find latest reported price';}});}
async function lookup(r){
 const lookupKey=key(r),lookupCountry=country;
 if(pending.has(lookupKey))return pending.get(lookupKey);
 const existing=results.get(lookupKey);if(existing&&!existing.error&&Date.parse(existing.expires_at)>Date.now()){paint(r);return existing;}
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
 const task=(async()=>{
  try{
   const response=await fetch(apiBase()+'/v1/price?'+new URLSearchParams({id:r.id,country:lookupCountry}),{signal:controller.signal,credentials:'omit'});
   const data=await response.json();
   if(!response.ok)throw new Error(data.error||'Price search is unavailable.');
   if(!['found','not_found'].includes(data.status)||!Array.isArray(data.prices))throw new Error('The price service returned an invalid result.');
   results.set(lookupKey,data);return data;
  }catch(e){results.set(lookupKey,{error:e.name==='AbortError'?'The lookup took too long. You can search Google directly.':e.message});}
  finally{clearTimeout(timer);pending.delete(lookupKey);paint(r);}
 })();
 pending.set(lookupKey,task);paint(r);return task;
}
function bind(records){const index=new Map(records.map(r=>[r.id,r]));document.querySelectorAll('[data-price-lookup]').forEach(b=>b.onclick=()=>{const r=index.get(b.dataset.priceLookup);if(r)lookup(r);});}
function countrySelector(elementId='price-country'){return `<label class="price-country">Web price search country <select id="${escape(elementId)}">${countries.map(([id,label])=>`<option value="${id}" ${country===id?'selected':''}>${label}</option>`).join('')}</select></label>`;}
function setCountry(value){if(countries.some(c=>c[0]===value))country=value;}
root.AtlasPrices={controls,bind,countrySelector,setCountry,google,lookup};
})(globalThis);
